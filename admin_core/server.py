"""Garak Hansang V6 local beta API + storefront static server.

Security boundary: loopback only unless explicitly opted into private staging network.
This is not a production auth/payment service; demo fixtures are not actual sales.
"""
from __future__ import annotations
import argparse,datetime as dt,hashlib,json,mimetypes,os,re,secrets,sqlite3,threading,time,urllib.parse
from http.server import SimpleHTTPRequestHandler,ThreadingHTTPServer
from pathlib import Path
from .database import connect,init_db,now,password_hash,password_valid,HERE,DEFAULT_DB,backend_name
from .mobile_commerce import public_product,quote_cart,verified_merchants,list_verified_products
from .product_options import approved_options,draft_options,create_revision,approve_revision
from .order_intents import create_or_replay,read_intent,list_intents,abandon_intent,IntentConflict

SITE=HERE/'storefront'
ROLE_RULES={
 'superadmin':{'*'},
 'ops':{'overview','products','inventory','inventory_moves','orders','shipments','merchants','recipes','posts','creators','tickets','integrations','reports','customers'},
 'content':{'overview','recipes','posts','creators','campaigns','products','reports'},
 'finance':{'overview','orders','settlements','reports','merchants','campaigns'},
 'support':{'overview','orders','shipments','tickets','customers','reports'},
}
FIELDS={
 'merchants':{'name','kind','contact','commission_bps','verified','status'},
 'products':{'name','price','stock','status','origin','image'},
 'recipes':{'title','minutes','status','reviewed','image','content'},
 'creators':{'name','platform','url','verified','status'},
 'posts':{'title','body','is_ad','verified','status'},
 'campaigns':{'name','placement','budget','spent','status','sponsored','start_date','end_date'},
 'integrations':{'enabled','status','description'},
 'tickets':{'subject','status'},
 'shipments':{'carrier','tracking','status'},
 'settlements':{'status'},
 'users':{'role','active'},
 'customers':{'name','consent'},
}
TABLES=FIELDS.keys()|{'orders','order_items','inventory_moves','audit_logs','page_events','ad_events'}
PRIVATE_FIELDS={'password_hash','id_hash','csrf','session_anonymous'}
STATUS={
 'products':{'draft','published','hidden'},'merchants':{'pending','active','rejected','suspended'},'recipes':{'draft','published','hidden'},
 'posts':{'pending','approved','rejected','archived'},'creators':{'pending','active','suspended'},
 'campaigns':{'draft','active','paused','completed'},'tickets':{'open','working','resolved'},
 'shipments':{'pending','ready','shipped','delivered'},'settlements':{'draft','approved','paid'}
}
ORDER_TRANSITIONS={'new':{'paid_test','canceled'},'paid_test':{'processing','canceled'},'processing':{'shipped','canceled'},'shipped':{'delivered'},'delivered':set(),'canceled':set()}
SETTLEMENT_TRANSITIONS={'draft':{'approved'},'approved':{'paid'},'paid':set()}
SESSION_SECONDS=8*3600
AUTH_ATTEMPTS={};AUTH_LOCK=threading.RLock(); EVENT_ATTEMPTS={}

def to_dict(row):return dict(row) if row is not None else None

def redact_audit(value):
 """Keep change provenance, never persist credentials or direct contact data in audit JSON."""
 if isinstance(value,dict):
  return {k:('[REDACTED]' if any(tag in k.lower() for tag in (
    'password','secret','token','csrf','hash','cookie','email','phone','contact','address','credential','api_key'))
    else redact_audit(v)) for k,v in value.items()}
 if isinstance(value,list):return [redact_audit(x) for x in value]
 return value

def record(con,who,action,table,rowid,old=None,new=None):
 old=redact_audit(old);new=redact_audit(new)
 con.execute('INSERT INTO audit_logs(actor_id,action,target,target_id,old_json,new_json,at) VALUES(?,?,?,?,?,?,?)',
   (who,action,table,rowid,json.dumps(old,ensure_ascii=False,default=str) if old is not None else None,json.dumps(new,ensure_ascii=False,default=str) if new is not None else None,now()))

def permitted(role,module,method):
 if role=='superadmin':return True
 if module not in ROLE_RULES.get(role,set()):return False
 if method=='GET':return True
 if role=='support' and module not in {'tickets','shipments'}:return False
 if role=='finance' and module in {'campaigns','merchants'}:return False
 if role=='content' and module=='products':return False
 if role=='ops' and module=='integrations':return False
 return True

def dbpath(server):
    return getattr(server,'dbpath',None) or os.environ.get('GARAK_ADMIN_DB',str(DEFAULT_DB))

class Handler(SimpleHTTPRequestHandler):
 server_version='GarakBetaAdmin/8.0'
 def __init__(self,*args,**kw):super().__init__(*args,directory=str(SITE),**kw)
 def log_message(self,fmt,*args):
  # Never include credentials or query secrets in logs.
  msg=str(fmt%args)
  if '/api/auth/login' in msg:msg='auth attempt'
  print('['+now()+'] '+msg[:300])
 def end_headers(self):
  self.send_header('X-Content-Type-Options','nosniff')
  self.send_header('X-Frame-Options','DENY')
  self.send_header('Referrer-Policy','strict-origin-when-cross-origin')
  self.send_header('Cross-Origin-Resource-Policy','same-origin')
  self.send_header('Cache-Control','no-store' if self.path.startswith('/api/') or self.path.startswith('/admin/') else 'public, max-age=90')
  super().end_headers()
 def respond(self,body=None,status=200,extra=None):
  content=json.dumps(body if body is not None else {},ensure_ascii=False,default=str).encode('utf-8')
  self.send_response(status);self.send_header('Content-Type','application/json; charset=utf-8')
  self.send_header('Content-Length',str(len(content)))
  for k,v in (extra or {}).items():self.send_header(k,v)
  self.end_headers();self.wfile.write(content)
 def error_json(self,status,message):self.respond({'error':message},status)
 def parse_body(self):
  if self.headers.get('Content-Type','').split(';')[0].strip()!='application/json':raise ValueError('application/json 형식이 필요합니다.')
  size=int(self.headers.get('Content-Length','0'))
  if not (2<=size<=96_000):raise ValueError('요청 본문은 최대 96KB입니다.')
  data=json.loads(self.rfile.read(size))
  if not isinstance(data,dict):raise ValueError('JSON 객체가 필요합니다.')
  return data
 def request_origin_ok(self):
  origin=self.headers.get('Origin','')
  host=self.headers.get('Host','')
  return not origin or urllib.parse.urlsplit(origin).netloc==host
 def session(self):
  raw=''
  for cookie in self.headers.get('Cookie','').split(';'):
   name,_,value=cookie.strip().partition('=')
   if name=='garak_admin_session':raw=value
  if not raw:return None
  sid=hashlib.sha256(raw.encode()).hexdigest()
  with connect(dbpath(self.server)) as con:
   r=con.execute('''SELECT u.id,u.username,u.role,u.active,s.csrf,s.expires_at FROM sessions s JOIN users u ON u.id=s.user_id WHERE s.id_hash=?''',(sid,)).fetchone()
  if not r or not r['active'] or r['expires_at']<=now():return None
  return dict(r)
 def require(self,module,method):
  s=self.session()
  if not s:self.error_json(401,'로그인 후 이용하세요.');return None
  if not permitted(s['role'],module,method):self.error_json(403,'이 역할에는 접근 권한이 없습니다.');return None
  if method!='GET':
   if not self.request_origin_ok():self.error_json(403,'요청 출처를 확인할 수 없습니다.');return None
   if not secrets.compare_digest(self.headers.get('X-Garak-CSRF',''),s['csrf']):self.error_json(403,'CSRF 검증 실패');return None
  return s
 def do_GET(self):
  path=urllib.parse.urlsplit(self.path).path
  if path=='/api/health':return self.respond({'ok':True,'mode':'LOCAL_BETA','backend':backend_name(),'payments':'simulation_only','external_integrations':'not_connected'})
  if path=='/api/auth/me':
   s=self.session()
   return self.respond({'authenticated':bool(s),'user':{'id':s['id'],'username':s['username'],'role':s['role']} if s else None,'csrf':s['csrf'] if s else None,'demo':True})
  if path=='/api/v1/mobile/markets':
   with connect(dbpath(self.server)) as con: merchants=verified_merchants(con)
   return self.respond({'data':{'items':[{'id':'garak','name':'가락한상 제휴 매장'}] if merchants else []},
                        'mode':'LOCAL_BETA','serviceability_verified':False})
  if path=='/api/v1/mobile/merchants':
   query=urllib.parse.parse_qs(urllib.parse.urlsplit(self.path).query)
   if query.get('market_id',[''])[0]!='garak':return self.error_json(404,'시장 정보 없음')
   with connect(dbpath(self.server)) as con: merchants=verified_merchants(con)
   return self.respond({'data':{'items':merchants},'mode':'LOCAL_BETA',
                        'serviceability_verified':False})
  if path=='/api/v1/mobile/products':
   query=urllib.parse.parse_qs(urllib.parse.urlsplit(self.path).query)
   if query and query.get('market_id',[''])[0]!='garak':return self.error_json(404,'시장 정보 없음')
   merchant=query.get('merchant_name',[None])[0]
   if merchant is not None and 'market_id' not in query:
    return self.error_json(400,'매장 필터에는 시장 식별자가 필요합니다.')
   try:
    with connect(dbpath(self.server)) as con: products=list_verified_products(con,merchant)
   except ValueError as e:return self.error_json(400,str(e))
   return self.respond({'data':{'items':products},'mode':'LOCAL_BETA','checkout_enabled':False})
  if path.startswith('/api/v1/mobile/products/'):
   slug=path.rsplit('/',1)[-1]
   try:
    with connect(dbpath(self.server)) as con: product=public_product(con,slug)
   except (LookupError,ValueError):return self.error_json(404,'승인된 상품을 찾을 수 없습니다.')
   return self.respond({'data':product,'mode':'LOCAL_BETA','checkout_enabled':False})
  if path.startswith('/api/public/'):
   con=connect(dbpath(self.server))
   try:
    if path=='/api/public/products':
     rows=con.execute('''SELECT p.slug,p.name,p.price,p.stock,p.status,p.image,p.category
       FROM products p LEFT JOIN merchants m ON m.id=p.merchant_id
       WHERE p.status='published' AND (m.status IS NULL OR m.status NOT IN ('suspended','rejected'))
       ORDER BY p.id LIMIT 100''').fetchall()
     return self.respond({'items':[dict(r) for r in rows],'mode':'LOCAL_BETA','price_warning':'샘플 가격이며 실제 판매가격이 아닙니다.'})
    if path.startswith('/api/public/product/'):
     slug=path.split('/')[-1]
     r=con.execute("""SELECT p.slug,p.name,p.price,p.stock,p.status,p.image FROM products p LEFT JOIN merchants m ON m.id=p.merchant_id WHERE p.slug=? AND p.status='published' AND (m.status IS NULL OR m.status NOT IN ('suspended','rejected'))""",(slug,)).fetchone()
     if not r:return self.error_json(404,'판매 중인 상품 없음')
     return self.respond({'product':dict(r),'mode':'LOCAL_BETA'})
    if path=='/api/public/posts':
     rows=con.execute("SELECT id,category,organization,title,body,is_ad FROM posts WHERE status='approved' AND verified=1 ORDER BY id DESC LIMIT 50").fetchall()
     return self.respond({'items':[dict(r) for r in rows]})
    if path=='/api/public/recipes':
     rows=con.execute("SELECT source_id,title,category,main_ingredient,product_slug,image,minutes FROM recipes WHERE status='published' AND reviewed=1 ORDER BY id LIMIT 132").fetchall()
     return self.respond({'items':[dict(r) for r in rows]})
   finally:con.close()
   return self.error_json(404,'공개 API가 없습니다.')
  if path=='/api/admin/order-intents' or path.startswith('/api/admin/order-intents/'):
   # This is an administrator-only NON-PAYABLE simulation ledger.
   session=self.require('orders','GET')
   if not session:return
   if backend_name()!='sqlite' or os.environ.get('GARAK_ORDER_SANDBOX')!='1':
    return self.error_json(503,'주문 시뮬레이션 API는 독립 로컬 테스트에서만 사용합니다.')
   parts=path.strip('/').split('/')
   if len(parts) not in (3,4):return self.error_json(404,'주문 시뮬레이션 조회 API 없음')
   actor=None if session['role']=='superadmin' else session['id']
   try:
    with connect(dbpath(self.server)) as con:
     if len(parts)==3:result={'items':list_intents(con,actor_id=actor)}
     else:result=read_intent(con,reference=parts[3],actor_id=actor)
   except LookupError:return self.error_json(404,'시뮬레이션 주문 정보 없음')
   return self.respond({'data':result,'mode':'LOCAL_BETA',
                        'checkout_enabled':False,'merchant_notified':False})
  if path.startswith('/api/admin/product-options/'):
   parts=path.strip('/').split('/')
   if len(parts)!=4:return self.error_json(404,'관리자 옵션 조회 API 없음')
   session=self.require('products','GET')
   if not session:return
   slug=parts[3]
   with connect(dbpath(self.server)) as con:
    product=con.execute('SELECT id,name FROM products WHERE slug=?',(slug,)).fetchone()
    if product is None:return self.error_json(404,'상품 없음')
    ver,groups=approved_options(con,product['id'])
    draft=draft_options(con,product['id'])
   return self.respond({'product':{'slug':slug,'name':product['name']},
                        'approved':{'version':ver,'groups':groups},'latest_draft':draft,
                        'mode':'LOCAL_BETA','checkout_enabled':False})
  if path.startswith('/api/admin/'):
   parts=path.strip('/').split('/');module=parts[2] if len(parts)>2 else ''
   if module not in TABLES|{'overview','reports','orders','settlements'}:return self.error_json(404,'모듈을 찾을 수 없습니다.')
   s=self.require(module,'GET')
   if not s:return
   with connect(dbpath(self.server)) as con:
    if module=='overview':return self.respond(overview(con))
    if module=='reports':return self.respond(reports(con))
    if module in TABLES:
     query=urllib.parse.parse_qs(urllib.parse.urlsplit(self.path).query)
     if module=='orders' and len(parts)==5 and parts[3].isdigit() and parts[4]=='details':
      oid=int(parts[3]); order=con.execute('SELECT * FROM orders WHERE id=?',(oid,)).fetchone()
      if not order:return self.error_json(404,'주문 없음')
      items=con.execute('SELECT oi.qty,oi.unit_price,oi.product_id,p.name,m.name merchant FROM order_items oi JOIN products p ON p.id=oi.product_id LEFT JOIN merchants m ON m.id=oi.merchant_id WHERE oi.order_id=?',(oid,)).fetchall()
      ship=con.execute('SELECT carrier,tracking,status FROM shipments WHERE order_id=?',(oid,)).fetchone()
      return self.respond({'order':dict(order),'items':[dict(x) for x in items],'shipment':dict(ship) if ship else None})
     if len(parts)>3 and parts[3].isdigit():
      row=con.execute(f'SELECT * FROM {module} WHERE id=?',(int(parts[3]),)).fetchone()
      if not row:return self.error_json(404,'데이터 없음')
      clean={k:v for k,v in dict(row).items() if k not in PRIVATE_FIELDS}
      return self.respond({'item':clean})
     term=(query.get('q',[''])[0] or '')[:100]
     cols=con.execute(f'PRAGMA table_info({module})').fetchall(); searchable=[v['name'] for v in cols if v['type'].upper().startswith('TEXT') and v['name'] not in PRIVATE_FIELDS]
     where=' OR '.join([f'{col} LIKE ?' for col in searchable])
     where=(' WHERE '+where) if term and searchable else ''
     params=['%'+term+'%']*len(searchable) if where else []
     rows=con.execute(f'SELECT * FROM {module}'+where+' ORDER BY id DESC LIMIT 300',params).fetchall()
     items=[{k:v for k,v in dict(r).items() if k not in PRIVATE_FIELDS} for r in rows]
     return self.respond({'items':items,'count':len(items),'module':module,'demo':True,'editable':sorted(FIELDS.get(module,[]))})
  # Keep login shell and public assets readable, protect legacy media operator tool.
  if path=='/admin/menu-options.html' and not self.session():
   return self.error_json(401,'상품 옵션 관리 기능은 관리자 로그인 후 이용하세요.')
  if path=='/admin/recipe-media.html' and not self.session():
   return self.error_json(401,'레시피 이미지 관리 도구는 관리자 로그인 후 이용하세요.')
  if path=='/':self.path='/index.html'
  elif path=='/admin' or path=='/admin/':self.path='/admin/index.html'
  return super().do_GET()
 def do_POST(self):
  path=urllib.parse.urlsplit(self.path).path
  if path=='/api/v1/mobile/cart/quote':
   if not self.request_origin_ok():return self.error_json(403,'요청 출처 오류')
   try:
    body=self.parse_body()
    with connect(dbpath(self.server)) as con: quote=quote_cart(con,body)
   except (ValueError,TypeError,json.JSONDecodeError) as e:return self.error_json(400,str(e))
   return self.respond({'data':quote,'mode':'LOCAL_BETA','checkout_enabled':False})
  if path=='/api/admin/order-intents' or path.startswith('/api/admin/order-intents/'):
   session=self.require('orders','POST')
   if not session:return
   if backend_name()!='sqlite' or os.environ.get('GARAK_ORDER_SANDBOX')!='1':
    return self.error_json(503,'주문 시뮬레이션은 명시적으로 허용된 로컬 테스트 DB에서만 진행합니다.')
   parts=path.strip('/').split('/')
   if len(parts) not in (3,5) or (len(parts)==5 and parts[4]!='abandon'):
    return self.error_json(404,'시뮬레이션 주문 변경 API 없음')
   try:
    body=self.parse_body()
    with connect(dbpath(self.server)) as con:
     con.execute('BEGIN IMMEDIATE')
     if len(parts)==3:
      key=self.headers.get('Idempotency-Key','')
      result,created=create_or_replay(
       con,payload=body,actor_id=session['id'],key=key,timestamp=now())
      if created:
       record(con,session['id'],'checkout_intent_created','checkout_intents',None,
              None,{'reference':result['reference'],'merchant_id':result['merchant_id'],
                    'subtotal_krw':result['subtotal_krw'],'payment_status':'not_initiated'})
      status=201 if created else 200
     else:
      result=abandon_intent(
       con,reference=parts[3],actor_id=session['id'],
       expected_version=body.get('expected_version'),timestamp=now())
      record(con,session['id'],'checkout_intent_abandoned','checkout_intents',None,
             None,{'reference':result['reference'],'status':result['status']})
      status=200
    # Commit must finish before success; no payment or merchant notification is emitted.
    return self.respond({'data':result,'mode':'LOCAL_BETA',
                         'checkout_enabled':False,'merchant_notified':False},status)
   except IntentConflict as e:return self.error_json(409,str(e))
   except LookupError:return self.error_json(404,'시뮬레이션 주문 정보 없음')
   except (ValueError,TypeError,sqlite3.IntegrityError,json.JSONDecodeError) as e:
    return self.error_json(400,str(e))
  if path.startswith('/api/admin/product-options/'):
   parts=path.strip('/').split('/')
   if len(parts) not in (5,7) or parts[:3]!=['api','admin','product-options'] or parts[4]!='revisions':
    return self.error_json(404,'옵션 변경 API 없음')
   session=self.require('products','POST')
   if not session:return
   if backend_name()!='sqlite':return self.error_json(503,'옵션 편집은 독립 테스트 DB에서만 허용합니다.')
   if len(parts)==7 and (parts[6]!='approve' or not parts[5].isdigit()):
    return self.error_json(404,'옵션 승인 API 없음')
   if len(parts)==7 and session['role']!='superadmin':
    return self.error_json(403,'최종 옵션 승인은 최고관리자만 가능합니다.')
   try:
    slug=parts[3]
    body=self.parse_body()
    status=200
    with connect(dbpath(self.server)) as con:
     con.execute('BEGIN IMMEDIATE')
     if len(parts)==5:
      result=create_revision(con,slug,body.get('groups'),session['id'],now())
      record(con,session['id'],'product_options_revision_created','products',None,None,
             {'slug':slug,'version':result['version'],'count':len(result['groups'])})
      status=201
     else:
      result=approve_revision(con,slug,int(parts[5]),now())
      record(con,session['id'],'product_options_revision_approved','products',None,None,result)
    # The DB connection must commit before any HTTP success can reach the client.
    # Otherwise an immediate customer GET may still observe unapproved options.
    return self.respond({'data':result,'checkout_enabled':False},status)
   except LookupError:return self.error_json(404,'상품 없음')
   except (ValueError,TypeError,sqlite3.IntegrityError) as e:
    return self.error_json(400,str(e))
  if path=='/api/public/events':
   if not self.request_origin_ok():return self.error_json(403,'출처 오류')
   try:
    d=self.parse_body();event=str(d.get('event',''));page=str(d.get('path','')).split('?')[0]
    if event not in {'page_view','view_product','view_recipe','add_to_cart_demo','view_post'} or not page.startswith('/') or len(page)>180:return self.error_json(400,'이벤트 형식 오류')
    with AUTH_LOCK:
     ip=self.client_address[0];ticks=[t for t in EVENT_ATTEMPTS.get(ip,[]) if time.monotonic()-t<60]
     if len(ticks)>=100:return self.error_json(429,'이벤트 제한')
     ticks.append(time.monotonic());EVENT_ATTEMPTS[ip]=ticks
    with connect(dbpath(self.server)) as con:con.execute('INSERT INTO page_events(event_name,path,created_at) VALUES(?,?,?)',(event,page,now()))
    return self.respond({'ok':True},202)
   except (ValueError,json.JSONDecodeError):return self.error_json(400,'형식 오류')
  if path=='/api/auth/login':
   if not self.request_origin_ok():return self.error_json(403,'인증 출처 오류')
   try:body=self.parse_body()
   except (ValueError,json.JSONDecodeError):return self.error_json(400,'로그인 입력 형식 오류')
   user=str(body.get('username',''))[:60];password=str(body.get('password',''))
   with AUTH_LOCK:
    attempts=[x for x in AUTH_ATTEMPTS.get(self.client_address[0],[]) if time.monotonic()-x<300]
    if len(attempts)>=8:return self.error_json(429,'로그인 시도가 많습니다. 5분 후 재시도하세요.')
    AUTH_ATTEMPTS[self.client_address[0]]=attempts
   with connect(dbpath(self.server)) as con:
    row=con.execute('SELECT * FROM users WHERE username=? AND active=1',(user,)).fetchone()
    valid=password_valid(password,row['password_hash']) if row else False
    if not valid:
     with AUTH_LOCK:AUTH_ATTEMPTS[self.client_address[0]].append(time.monotonic())
     return self.error_json(401,'아이디 또는 비밀번호가 올바르지 않습니다.')
    sid=secrets.token_urlsafe(36);csrf=secrets.token_urlsafe(30)
    expires=(dt.datetime.now(dt.timezone.utc)+dt.timedelta(seconds=SESSION_SECONDS)).isoformat(timespec='seconds')
    con.execute('INSERT INTO sessions(id_hash,user_id,csrf,expires_at) VALUES(?,?,?,?)',(hashlib.sha256(sid.encode()).hexdigest(),row['id'],csrf,expires))
    record(con,row['id'],'login','users',row['id'])
    cookie=f'garak_admin_session={sid}; HttpOnly; SameSite=Strict; Path=/; Max-Age={SESSION_SECONDS}'
    if self.headers.get('X-Forwarded-Proto','')=='https':cookie+='; Secure'
    return self.respond({'ok':True,'role':row['role'],'csrf':csrf},200,{'Set-Cookie':cookie})
  if path=='/api/auth/logout':
   s=self.require('overview','POST')
   if not s:return
   for chunk in self.headers.get('Cookie','').split(';'):
    k,_,v=chunk.strip().partition('=')
    if k=='garak_admin_session':
     with connect(dbpath(self.server)) as con:con.execute('DELETE FROM sessions WHERE id_hash=?',(hashlib.sha256(v.encode()).hexdigest(),))
   return self.respond({'ok':True},200,{'Set-Cookie':'garak_admin_session=; Path=/; HttpOnly; SameSite=Strict; Max-Age=0'})
  if path=='/api/auth/password':
   s=self.require('overview','POST')
   if not s:return
   try:d=self.parse_body()
   except (ValueError,json.JSONDecodeError):return self.error_json(400,'잘못된 요청')
   old=str(d.get('current_password',''));new=str(d.get('new_password',''))
   if len(new)<14 or len(new)>200:return self.error_json(400,'새 비밀번호는 14~200자로 설정하세요.')
   with connect(dbpath(self.server)) as con:
    row=con.execute('SELECT password_hash FROM users WHERE id=?',(s['id'],)).fetchone()
    if not password_valid(old,row['password_hash']):return self.error_json(403,'현재 비밀번호 불일치')
    con.execute('UPDATE users SET password_hash=? WHERE id=?',(password_hash(new),s['id']))
    # Credential rotation invalidates every outstanding session, including the current session.
    con.execute('DELETE FROM sessions WHERE user_id=?',(s['id'],))
    record(con,s['id'],'password_change_and_revoke_sessions','users',s['id'])
   (Path(dbpath(self.server)).parent/'FIRST_LOGIN_LOCAL_ONLY.txt').unlink(missing_ok=True)
   return self.respond({'ok':True})
  parts=path.strip('/').split('/')
  if len(parts)<3 or parts[:2]!=['api','admin']:return self.error_json(404,'API 없음')
  module=parts[2]
  s=self.require(module,'POST')
  if not s:return
  try:d=self.parse_body()
  except (ValueError,json.JSONDecodeError) as e:return self.error_json(400,str(e))
  try:
   if path=='/api/admin/inventory/adjust':return self.adjust_inventory(s,d)
   if path=='/api/admin/users/create':return self.user_create(s,d)
   if path=='/api/admin/products':return self.product_create(s,d)
   if path=='/api/admin/recipes':return self.recipe_create(s,d)
   if path=='/api/admin/orders/create':return self.order_create(s,d)
   if len(parts)==5 and parts[2]=='orders' and parts[4]=='transition':return self.order_transition(s,int(parts[3]),d)
   if path=='/api/admin/settlements/generate':return self.generate_settlements(s)
   if path=='/api/admin/reports/export':return self.respond({'error':'개인정보 보호를 위해 대량 다운로드를 별도로 승인해야 합니다.'},403)
   if module in {'posts','campaigns','creators','tickets','merchants'} and len(parts)==3:return self.create_record(s,module,d)
   return self.error_json(404,'알 수 없는 작업')
  except (ValueError,TypeError,KeyError,sqlite3.IntegrityError) as e:return self.error_json(400,str(e))
 def do_PATCH(self):
  parts=urllib.parse.urlsplit(self.path).path.strip('/').split('/')
  if len(parts)!=4 or parts[:2]!=['api','admin'] or parts[2] not in FIELDS or not parts[3].isdigit():return self.error_json(404,'수정 API 없음')
  module=parts[2];rid=int(parts[3]);s=self.require(module,'PATCH')
  if not s:return
  try:d=self.parse_body();return self.update_record(s,module,rid,d)
  except (ValueError,TypeError,KeyError,sqlite3.IntegrityError) as e:return self.error_json(400,str(e))
 def update_record(self,s,module,rid,d):
  allowed=FIELDS[module];setdata={k:v for k,v in d.items() if k in allowed}
  if not setdata:return self.error_json(400,'수정 가능한 필드가 없습니다.')
  if 'status' in setdata and module in STATUS and setdata['status'] not in STATUS[module]:raise ValueError('유효하지 않은 상태')
  if module=='products' and 'stock' in setdata:raise ValueError('재고는 별도 조정 API로 변경하세요.')
  for k,v in setdata.items():
   if k in {'price','budget','spent','commission_bps','minutes','reviewed','verified','active','sponsored','enabled','is_ad','consent'}:
    if isinstance(v,bool):v=int(v)
    if not isinstance(v,int) or v<0:raise ValueError(k+'는 0 이상의 정수여야 합니다.')
    if k=='commission_bps' and v>4000:raise ValueError('수수료 40% 초과 불가')
    if k in {'verified','reviewed','active','sponsored','enabled','is_ad','consent'} and v not in (0,1):raise ValueError('불리언 값 오류')
    setdata[k]=v
   elif not isinstance(v,str) or not 0<=len(v)<=5000:raise ValueError(k+' 문자열 길이 오류')
  with connect(dbpath(self.server)) as con:
   con.execute('BEGIN IMMEDIATE')
   old=to_dict(con.execute(f'SELECT * FROM {module} WHERE id=?',(rid,)).fetchone())
   if not old:return self.error_json(404,'원본 없음')
   new_status=setdata.get('status')
   if module=='merchants' and setdata.get('status',old['status'])=='active' and not setdata.get('verified',old['verified']):raise ValueError('사업자 확인이 취소되면 활성 점포 상태를 유지할 수 없습니다.')
   # Once a seller is suspended or rejected, published products must stop selling immediately.
   # Reactivation never silently republishes products; a separate approval is required.
   if module=='merchants' and setdata.get('status',old['status']) in {'suspended','rejected'}:
    ids=[r['id'] for r in con.execute("SELECT id FROM products WHERE merchant_id=? AND status='published'",(rid,)).fetchall()]
    if ids:
     con.execute("UPDATE products SET status='hidden',updated_at=? WHERE merchant_id=? AND status='published'",(now(),rid))
     record(con,s['id'],'seller_suspended_products_hidden','merchants',rid,None,{'hidden_count':len(ids)})
   if module=='products' and new_status=='published' and old['status']!='published':
    owner=con.execute('SELECT verified,status FROM merchants WHERE id=?',(old['merchant_id'],)).fetchone()
    if not owner or not owner['verified'] or owner['status']!='active':raise ValueError('인증된 활성 상인의 상품만 신규 공개할 수 있습니다.')
   if module=='posts' and new_status=='approved' and not setdata.get('verified',old['verified']):raise ValueError('사업자/작성자 확인 없는 게시물 공개 불가')
   if module=='recipes' and new_status=='published' and not setdata.get('reviewed',old['reviewed']):raise ValueError('레시피 검수 후 공개 가능')
   if module=='settlements' and new_status and new_status!=old['status'] and new_status not in SETTLEMENT_TRANSITIONS[old['status']]:raise ValueError('정산 상태 전환 오류')
   if module=='shipments' and new_status in {'shipped','delivered'}:
    raise ValueError('실제 배송 상태 변경은 주문 상태 전환 API에서만 가능합니다.')
   if module=='integrations' and setdata.get('status')=='connected':raise ValueError('실제 OAuth/API 검증 없이 connected 표기 불가')
   if module=='users' and rid==s['id'] and ('role' in setdata or setdata.get('active')==0):raise ValueError('본인 권한/상태 변경 불가')
   if module=='users' and setdata.get('role') and setdata['role'] not in ROLE_RULES:raise ValueError('역할 이름 오류')
   if module=='products' and 'price' in setdata and setdata['price']>1_000_000_000:raise ValueError('가격 범위 오류')
   cols=', '.join(f'{k}=?' for k in setdata)
   con.execute(f'UPDATE {module} SET {cols} WHERE id=?',[*setdata.values(),rid])
   new=to_dict(con.execute(f'SELECT * FROM {module} WHERE id=?',(rid,)).fetchone())
   record(con,s['id'],'update',module,rid,old,new)
   con.commit()
  return self.respond({'ok':True,'item':{k:v for k,v in new.items() if k not in PRIVATE_FIELDS}})
 def product_create(self,s,d):
  slug=str(d.get('slug','')).strip();name=str(d.get('name','')).strip();kind=str(d.get('category',''))
  price=d.get('price',0);stock=d.get('stock',0);merchant_id=int(d.get('merchant_id',0))
  if not re.fullmatch(r'[a-z0-9-]{4,90}',slug):raise ValueError('상품 코드 형식 오류')
  if not 3<=len(name)<=200:raise ValueError('상품명 3~200자')
  if kind not in {'seafood','meat','produce','sets','extras'}:raise ValueError('상품 카테고리 오류')
  if type(price)!=int or not 0<=price<=1_000_000_000 or type(stock)!=int or not 0<=stock<=100000:raise ValueError('가격/재고 입력 오류')
  with connect(dbpath(self.server)) as con:
   merchant=con.execute('SELECT id FROM merchants WHERE id=?',(merchant_id,)).fetchone()
   if not merchant:raise ValueError('등록된 상인이 없습니다')
   cur=con.execute('INSERT INTO products(slug,name,category,merchant_id,price,stock,status,image,origin,updated_at) VALUES(?,?,?,?,?,?,?,?,?,?)',
    (slug,name,kind,merchant_id,price,stock,'draft',str(d.get('image',''))[:255],str(d.get('origin',''))[:120],now()))
   if stock:con.execute('INSERT INTO inventory_moves(product_id,delta,reason,actor_id,created_at) VALUES(?,?,?,?,?)',(cur.lastrowid,stock,'initial_beta_stock',s['id'],now()))
   record(con,s['id'],'create','products',cur.lastrowid,None,{'slug':slug,'price':price,'stock':stock,'status':'draft'})
  return self.respond({'ok':True,'id':cur.lastrowid,'status':'draft'},201)
 def recipe_create(self,s,d):
  title=str(d.get('title','')).strip();category=str(d.get('category','')).strip();slug=str(d.get('product_slug','')).strip();minutes=d.get('minutes',20)
  if not 3<=len(title)<=200:raise ValueError('요리명 3~200자')
  if category not in {'수산','축산','농산'}:raise ValueError('레시피 카테고리 오류')
  if type(minutes)!=int or minutes<1 or minutes>480:raise ValueError('조리 시간 오류')
  if slug and not re.fullmatch(r'[a-z0-9-]{2,90}',slug):raise ValueError('상품 코드 오류')
  with connect(dbpath(self.server)) as con:
   if slug and not con.execute('SELECT id FROM products WHERE slug=?',(slug,)).fetchone():raise ValueError('연결 상품이 없음')
   rid='custom-'+secrets.token_hex(6)
   cur=con.execute('INSERT INTO recipes(source_id,title,category,main_ingredient,product_slug,image,minutes,content,status,reviewed,updated_at) VALUES(?,?,?,?,?,?,?,?,?,?,?)',
    (rid,title,category,str(d.get('main_ingredient',''))[:120],slug,str(d.get('image',''))[:255],minutes,'{}','draft',0,now()))
   record(con,s['id'],'create','recipes',cur.lastrowid,None,{'source_id':rid,'title':title,'status':'draft'})
  return self.respond({'ok':True,'id':cur.lastrowid,'source_id':rid,'status':'draft'},201)
 def user_create(self,s,d):
  if s['role']!='superadmin':return self.error_json(403,'최고 관리자만 계정을 생성합니다.')
  username=str(d.get('username','')).strip();role=str(d.get('role','support'))
  if not re.fullmatch(r'[A-Za-z0-9_.-]{3,40}',username):raise ValueError('아이디는 영문·숫자·기호 3~40자')
  if role not in ROLE_RULES:raise ValueError('역할 오류')
  pw=secrets.token_urlsafe(20)
  with connect(dbpath(self.server)) as con:
   cur=con.execute('INSERT INTO users(username,password_hash,role,created_at) VALUES(?,?,?,?)',(username,password_hash(pw),role,now()))
   record(con,s['id'],'create_user','users',cur.lastrowid,None,{'username':username,'role':role})
  return self.respond({'id':cur.lastrowid,'username':username,'role':role,'one_time_password':pw,'notice':'전달 후 최초 비밀번호 변경 필수'},201)
 def adjust_inventory(self,s,d):
  pid=d.get('product_id');delta=d.get('delta');reason=d.get('reason','')
  if type(pid)!=int or pid<=0 or type(delta)!=int or delta==0 or abs(delta)>100000 or not isinstance(reason,str) or not 3<=len(reason.strip())<=200:
   raise ValueError('재고 변경 ID/수량/사유가 올바르지 않습니다. 정수 수량만 사용할 수 있습니다.')
  reason=reason.strip()
  with connect(dbpath(self.server)) as con:
   con.execute('BEGIN IMMEDIATE')
   p=con.execute('SELECT id,stock FROM products WHERE id=?',(pid,)).fetchone()
   if not p:raise ValueError('상품 없음')
   if p['stock']+delta<0:raise ValueError('재고 부족')
   con.execute('UPDATE products SET stock=?,updated_at=? WHERE id=?',(p['stock']+delta,now(),pid))
   con.execute('INSERT INTO inventory_moves(product_id,delta,reason,created_at,actor_id) VALUES(?,?,?,?,?)',(pid,delta,reason,now(),s['id']))
   record(con,s['id'],'stock_adjust','products',pid,{'stock':p['stock']},{'stock':p['stock']+delta,'reason':reason});con.commit()
  return self.respond({'ok':True,'stock':p['stock']+delta})
 def order_create(self,s,d):
  entries=d.get('items')
  if not isinstance(entries,list) or not (1<=len(entries)<=20):raise ValueError('상품 1~20개를 지정하세요')
  # Aggregate duplicate SKUs before a stock read. The DB CHECK(stock>=0) is a final
  # defense, not a substitute for an explicit and understandable stock error.
  quantities={}
  for entry in entries:
   if not isinstance(entry,dict):raise ValueError('상품 입력 형식 오류')
   slug=entry.get('slug','');qty=entry.get('qty',0)
   if not isinstance(slug,str) or not re.fullmatch(r'[a-z0-9-]{2,90}',slug):raise ValueError('상품 코드 형식 오류')
   if type(qty)!=int or qty<1 or qty>50:raise ValueError('수량 1~50개')
   quantities[slug]=quantities.get(slug,0)+qty
   if quantities[slug]>50:raise ValueError(slug+': 상품별 주문 상한은 50개입니다.')
  rows=[];subtotal=0
  with connect(dbpath(self.server)) as con:
   con.execute('BEGIN IMMEDIATE')
   for slug,qty in quantities.items():
    product=con.execute('''SELECT p.*,m.status AS seller_status FROM products p
       LEFT JOIN merchants m ON m.id=p.merchant_id WHERE p.slug=? AND p.status=?''',(slug,'published')).fetchone()
    if not product or product['stock']<qty:raise ValueError(slug+': 합산 수량이 재고를 초과하거나 상품이 비공개 상태입니다.')
    if product['seller_status'] in ('suspended','rejected'):
     raise ValueError(slug+': 판매 중지 또는 승인 거절된 상인의 상품은 주문할 수 없습니다.')
    rows.append((product,qty));subtotal+=product['price']*qty
   customer_id=d.get('customer_id')
   if customer_id is not None and not con.execute('SELECT id FROM customers WHERE id=?',(int(customer_id),)).fetchone():raise ValueError('고객 ID 없음')
   ref='BETA-'+secrets.token_hex(5).upper()
   cur=con.execute('INSERT INTO orders(customer_id,reference,status,payment_mode,subtotal,created_at,updated_at) VALUES(?,?,?,?,?,?,?)',(customer_id,ref,'new','simulation',subtotal,now(),now()))
   order_id=cur.lastrowid
   for product,qty in rows:
    reserved=con.execute('UPDATE products SET stock=stock-?,updated_at=? WHERE id=? AND status=? AND stock>=?',(qty,now(),product['id'],'published',qty))
    if reserved.rowcount!=1:raise ValueError(product['slug']+': 주문 처리 중 재고가 변경되었습니다.')
    con.execute('INSERT INTO order_items(order_id,product_id,merchant_id,qty,unit_price) VALUES(?,?,?,?,?)',(order_id,product['id'],product['merchant_id'],qty,product['price']))
    con.execute('INSERT INTO inventory_moves(product_id,delta,reason,reference,created_at,actor_id) VALUES(?,?,?,?,?,?)',(product['id'],-qty,'beta_order_reservation',ref,now(),s['id']))
   con.execute('INSERT INTO shipments(order_id,updated_at) VALUES(?,?)',(order_id,now()))
   record(con,s['id'],'order_created_test','orders',order_id,None,{'subtotal':subtotal,'reference':ref,'mode':'simulation'})
   con.commit()
  return self.respond({'ok':True,'order_id':order_id,'reference':ref,'subtotal':subtotal,'payment_mode':'simulation'},201)
 def order_transition(self,s,order_id,d):
  status=str(d.get('status',''))
  with connect(dbpath(self.server)) as con:
   con.execute('BEGIN IMMEDIATE')
   old=con.execute('SELECT * FROM orders WHERE id=?',(order_id,)).fetchone()
   if not old:raise ValueError('주문 없음')
   if status not in ORDER_TRANSITIONS[old['status']]:raise ValueError('허용되지 않는 상태 전환')
   if status=='shipped':
    sh=con.execute('SELECT * FROM shipments WHERE order_id=?',(order_id,)).fetchone()
    if not sh or not sh['carrier'] or not sh['tracking']:raise ValueError('배송사·운송장 등록 전 발송 불가')
    con.execute('UPDATE shipments SET status=?,updated_at=? WHERE order_id=?',('shipped',now(),order_id))
   if status=='delivered':con.execute('UPDATE shipments SET status=?,updated_at=? WHERE order_id=?',('delivered',now(),order_id))
   if status=='canceled':
    items=con.execute('SELECT * FROM order_items WHERE order_id=?',(order_id,)).fetchall()
    for it in items:
     con.execute('UPDATE products SET stock=stock+?,updated_at=? WHERE id=?',(it['qty'],now(),it['product_id']))
     con.execute('INSERT INTO inventory_moves(product_id,delta,reason,reference,created_at,actor_id) VALUES(?,?,?,?,?,?)',(it['product_id'],it['qty'],'beta_cancel_restock',old['reference'],now(),s['id']))
   con.execute('UPDATE orders SET status=?,updated_at=? WHERE id=?',(status,now(),order_id))
   record(con,s['id'],'order_transition','orders',order_id,{'status':old['status']},{'status':status});con.commit()
  return self.respond({'ok':True,'order_id':order_id,'status':status})
 def generate_settlements(self,s):
  created=0
  with connect(dbpath(self.server)) as con:
   con.execute('BEGIN IMMEDIATE')
   sales=con.execute('''SELECT oi.order_id,oi.merchant_id,SUM(oi.qty*oi.unit_price) gross,COALESCE(m.commission_bps,800) fee_bps FROM order_items oi JOIN orders o ON o.id=oi.order_id LEFT JOIN merchants m ON m.id=oi.merchant_id WHERE o.status='delivered' AND oi.merchant_id IS NOT NULL GROUP BY oi.order_id,oi.merchant_id''').fetchall()
   for r in sales:
    gross=r['gross'];fee=(gross*r['fee_bps']+5000)//10000
    cur=con.execute('INSERT OR IGNORE INTO settlements(order_id,merchant_id,gross,fee,payout,status,created_at) VALUES(?,?,?,?,?,?,?)',(r['order_id'],r['merchant_id'],gross,fee,gross-fee,'draft',now()))
    created+=cur.rowcount
   record(con,s['id'],'generate','settlements',None,None,{'created':created,'mode':'simulation'})
   con.commit()
  return self.respond({'ok':True,'new_settlements':created,'mode':'simulation'})
 def create_record(self,s,module,d):
  allowed=FIELDS[module]-{'verified','status','spent','sponsored','enabled','active'}
  data={k:d[k] for k in allowed if k in d}
  required={'posts':['category','organization','title','body'],'merchants':['name','kind'],'campaigns':['name'],'creators':['name'],'tickets':['subject']}[module]
  if module=='posts':data.update({k:d.get(k,'') for k in required})
  if module=='merchants':data.update({k:d.get(k,'') for k in required})
  for k in required:
   if not isinstance(data.get(k),str) or len(data[k].strip())<2:raise ValueError(k+'는 필수입니다.')
  if module=='posts' and data['category'] not in {'merchants','distributors','associations','collaboration','chef'}:raise ValueError('게시판 유형 오류')
  if module=='merchants' and data['kind'] not in {'seafood','meat','produce','other'}:raise ValueError('업종 오류')
  if 'budget' in data:
   if not isinstance(data['budget'],int) or data['budget']<0:raise ValueError('예산 오류')
  data['created_at']=now()
  columns=','.join(data.keys());placeholders=','.join('?'*len(data))
  with connect(dbpath(self.server)) as con:
   cur=con.execute(f'INSERT INTO {module}({columns}) VALUES({placeholders})',list(data.values()))
   record(con,s['id'],'create',module,cur.lastrowid,None,data)
  return self.respond({'ok':True,'id':cur.lastrowid,'status':'pending' if module in ('posts','merchants','creators') else 'draft'},201)

def overview(con):
 def num(s):return con.execute(s).fetchone()[0]
 return {'mode':'LOCAL_BETA','synthetic':True,'kpis':{
 'products':num("SELECT COUNT(*) FROM products"),'published_products':num("SELECT COUNT(*) FROM products WHERE status='published'"),
 'stock_units':num('SELECT COALESCE(SUM(stock),0) FROM products'), 'recipes':num('SELECT COUNT(*) FROM recipes'),
 'pending_posts':num("SELECT COUNT(*) FROM posts WHERE status='pending'"),'pending_merchants':num("SELECT COUNT(*) FROM merchants WHERE status='pending'"),
 'orders':num('SELECT COUNT(*) FROM orders'),'gross_order_value_test':num("SELECT COALESCE(SUM(subtotal),0) FROM orders WHERE status NOT IN ('canceled')"),
 'delivered_test':num("SELECT COUNT(*) FROM orders WHERE status='delivered'"),
 'unresolved_tickets':num("SELECT COUNT(*) FROM tickets WHERE status!='resolved'"),
 'unconnected_integrations':num("SELECT COUNT(*) FROM integrations WHERE status!='connected'"),
 'settlements_due_test':num("SELECT COALESCE(SUM(payout),0) FROM settlements WHERE status!='paid'")},
 'recent_orders':[dict(x) for x in con.execute('SELECT id,reference,status,subtotal,created_at FROM orders ORDER BY id DESC LIMIT 8')],
 'inventory_low':[dict(x) for x in con.execute('SELECT id,slug,name,stock FROM products WHERE stock<=5 ORDER BY stock ASC LIMIT 10')]}

def reports(con):
 def rows(sql):return [dict(r) for r in con.execute(sql).fetchall()]
 return {'mode':'LOCAL_BETA','synthetic':True,
 'daily_sales':rows("SELECT substr(created_at,1,10) day,COUNT(*) orders,COALESCE(SUM(CASE WHEN status!='canceled' THEN subtotal ELSE 0 END),0) gross FROM orders GROUP BY substr(created_at,1,10) ORDER BY day DESC LIMIT 30"),
 'order_status':rows('SELECT status,COUNT(*) count FROM orders GROUP BY status ORDER BY status'),
 'sales_by_category':rows("SELECT p.category,SUM(oi.qty) units,SUM(oi.qty*oi.unit_price) gross FROM order_items oi JOIN products p ON p.id=oi.product_id JOIN orders o ON o.id=oi.order_id WHERE o.status!='canceled' GROUP BY p.category ORDER BY gross DESC"),
 'top_products':rows("SELECT p.name,SUM(oi.qty) units,SUM(oi.qty*oi.unit_price) gross FROM order_items oi JOIN products p ON p.id=oi.product_id JOIN orders o ON o.id=oi.order_id WHERE o.status!='canceled' GROUP BY oi.product_id ORDER BY units DESC LIMIT 10"),
 'traffic':rows('SELECT event_name,COUNT(*) events FROM page_events GROUP BY event_name'),
 'ad_funnel':rows("SELECT c.name,COUNT(CASE WHEN e.event_type='impression' THEN 1 END) impressions,COUNT(CASE WHEN e.event_type='click' THEN 1 END) clicks,COUNT(CASE WHEN e.event_type='conversion' THEN 1 END) conversions FROM campaigns c LEFT JOIN ad_events e ON e.campaign_id=c.id GROUP BY c.id")}

def setup(db=None, seed=True):
 """Initialize schema/seed for local SQLite or Neon Postgres (DATABASE_URL)."""
 path=db or os.environ.get('GARAK_ADMIN_DB',str(DEFAULT_DB))
 con=init_db(path,seed=seed);con.close();return path

class Server(ThreadingHTTPServer):
 daemon_threads=True
 def __init__(self,address,dbpath):
  self.dbpath=Path(dbpath);super().__init__(address,Handler)

def main():
 parser=argparse.ArgumentParser(description='Garak admin core local beta')
 parser.add_argument('--port',type=int,default=int(os.environ.get('GARAK_PORT','8099')))
 parser.add_argument('--host',default='127.0.0.1')
 parser.add_argument('--db',default=os.environ.get('GARAK_ADMIN_DB',str(DEFAULT_DB)))
 parser.add_argument('--no-seed',action='store_true')
 a=parser.parse_args()
 if a.host not in {'127.0.0.1','localhost','::1'} and os.environ.get('GARAK_PRIVATE_STAGING_ACK')!='YES':
  parser.error('Public listening is disabled. Set GARAK_PRIVATE_STAGING_ACK=YES for secured private staging only.')
 con=init_db(a.db,seed=not a.no_seed);con.close()
 server=Server((a.host,a.port),a.db)
 print(f'가락한상 관리자 로컬 베타: http://{a.host}:{a.port}/admin/ (실결제 비활성)')
 print(f'최초 로그인 정보는 {Path(a.db).parent / "FIRST_LOGIN_LOCAL_ONLY.txt"}에서 확인하세요.')
 try:server.serve_forever()
 except KeyboardInterrupt:pass
 finally:server.server_close()

if __name__=='__main__':main()
