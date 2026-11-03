"""Authenticated merchant applications and moderated community for Garak Hansang.
All mutations require a verified Neon Auth JWT or legacy admin session.
"""
from __future__ import annotations
import datetime as dt
import json
import os
import re
import secrets
from functools import lru_cache
from urllib.parse import parse_qs, urlsplit
from .database import connect
from .pgcompat import use_postgres

CATEGORIES = {'notice','season','story','question'}
ADMIN_ROLES = {'superadmin','ops','content'}
TABLES = {'applications':'merchant_applications','posts':'community_posts','comments':'community_comments'}

class RequestError(Exception):
    def __init__(self, status, message):
        self.status, self.message = status, message

def response(data, status=200):
    return status, {'Content-Type':'application/json; charset=utf-8','Cache-Control':'no-store','X-Content-Type-Options':'nosniff'}, json.dumps(data,ensure_ascii=False,default=str).encode('utf-8')

def field(data,key,maximum,minimum=1):
    value=data.get(key,'')
    if not isinstance(value,str): raise RequestError(400,'입력 형식 오류: '+key)
    value=value.strip()
    if not minimum<=len(value)<=maximum or any(ord(c)<32 and c not in '\r\n\t' for c in value):
        raise RequestError(400,'입력 길이 또는 형식 오류: '+key)
    return value

def body_json(raw,headers):
    if headers.get('content-type','').split(';')[0].strip().lower()!='application/json':
        raise RequestError(415,'JSON 형식의 요청만 허용합니다.')
    if not 2<=len(raw)<=12000: raise RequestError(413,'요청 본문 크기 초과')
    try: value=json.loads(raw)
    except (ValueError,UnicodeError): raise RequestError(400,'잘못된 JSON') from None
    if not isinstance(value,dict): raise RequestError(400,'JSON 객체가 필요합니다.')
    return value

def check_origin(headers):
    origin=headers.get('origin','')
    if origin:
        url=urlsplit(origin)
        host=headers.get('host','')
        if url.netloc.lower()!=host.lower() or url.scheme not in ({'https','http'} if host.startswith(('localhost:','127.0.0.1:')) else {'https'}):
            raise RequestError(403,'요청 출처를 확인할 수 없습니다.')

@lru_cache(maxsize=4)
def jwks_client(url):
    import jwt
    return jwt.PyJWKClient(url,cache_jwk_set=True,lifespan=300,timeout=6)

def member(headers):
    import jwt
    value=headers.get('authorization','')
    if not value.startswith('Bearer ') or len(value)>8000: raise RequestError(401,'회원 로그인이 필요합니다.')
    base=os.environ.get('NEON_AUTH_BASE_URL','').strip().rstrip('/')
    if not base.startswith('https://'): raise RequestError(503,'회원 인증 서버가 설정되지 않았습니다.')
    issuer=urlsplit(base).scheme+'://'+urlsplit(base).netloc
    try:
        token=value[7:]
        key=jwks_client(base+'/.well-known/jwks.json').get_signing_key_from_jwt(token)
        claims=jwt.decode(token,key.key,algorithms=['EdDSA','RS256'],issuer=issuer,options={'require':['sub','exp','iss'],'verify_aud':False},leeway=30)
        uid=claims['sub']
        if not isinstance(uid,str) or not 1<=len(uid)<=128: raise ValueError('bad subject')
        name=claims.get('name') if isinstance(claims.get('name'),str) else '회원'
        return uid,name.strip()[:50] or '회원'
    except Exception:
        raise RequestError(401,'인증이 만료되었거나 유효하지 않습니다. 다시 로그인하세요.') from None

def admin(headers):
    import hashlib
    raw=''
    for pair in headers.get('cookie','').split(';'):
        key,_,val=pair.strip().partition('=')
        if key=='garak_admin_session': raw=val;break
    if not raw or len(raw)>512: raise RequestError(401,'관리자 로그인이 필요합니다.')
    with connect() as con:
        row=con.execute('''SELECT u.id,u.role,u.active,s.csrf,s.expires_at FROM sessions s
        JOIN users u ON u.id=s.user_id WHERE s.id_hash=?''',(hashlib.sha256(raw.encode()).hexdigest(),)).fetchone()
    if not row or not row['active'] or row['role'] not in ADMIN_ROLES or str(row['expires_at'])<=dt.datetime.now(dt.timezone.utc).isoformat(timespec='seconds'):
        raise RequestError(403,'관리자 검수 권한이 없습니다.')
    return row

def rate(con,table,user,limit):
    if table not in TABLES.values(): raise RequestError(500,'알 수 없는 테이블')
    cutoff=dt.datetime.now(dt.timezone.utc)-dt.timedelta(hours=24)
    n=con.execute(f'SELECT COUNT(*) n FROM {table} WHERE author_id=? AND created_at>=?',(user,cutoff)).fetchone()['n']
    if n>=limit: raise RequestError(429,'24시간 작성 제한을 초과했습니다.')

def list_applications(uid):
    with connect() as con:
        rows=con.execute('''SELECT id,shop_name,category,status,created_at FROM merchant_applications
        WHERE author_id=? ORDER BY id DESC LIMIT 30''',(uid,)).fetchall()
    return response({'items':[dict(row) for row in rows]})

def create_application(uid,d):
    fields={key:field(d,key,length,minlen) for key,length,minlen in
        [('shopName',80,1),('contactName',50,1),('phone',30,7),('email',120,5),
         ('category',60,1),('location',120,0),('description',1500,15)]}
    if d.get('consent') is not True: raise RequestError(400,'개인정보 수집·이용 동의가 필요합니다.')
    if not re.fullmatch(r'\+?[0-9][0-9\s()\-]{6,28}',fields['phone']): raise RequestError(400,'전화번호 형식 오류')
    if not re.fullmatch(r'[^\s@]+@[^\s@]+\.[^\s@]+',fields['email']): raise RequestError(400,'이메일 형식 오류')
    with connect() as con:
        rate(con,'merchant_applications',uid,3)
        cur=con.execute('''INSERT INTO merchant_applications
        (author_id,shop_name,contact_name,phone,email,category,shop_location,description,consent_at)
        VALUES (?,?,?,?,?,?,?,?,CURRENT_TIMESTAMP) RETURNING id''',
        (uid,fields['shopName'],fields['contactName'],fields['phone'],fields['email'],
         fields['category'],fields['location'],fields['description']))
        rid=cur.fetchone()['id']
    return response({'ok':True,'id':rid,'status':'pending','message':'입점 신청 접수 완료 · 검토 대기'},201)

def list_posts(query,auth_headers):
    category=query.get('category',['all'])[0]
    mine=query.get('mine',['0'])[0]=='1'
    if category!='all' and category not in CATEGORIES: raise RequestError(400,'잘못된 분류')
    params=[]
    if mine:
        uid,_=member(auth_headers)
        where='WHERE author_id=?';params.append(uid)
    else:
        where="WHERE status='approved'"
    if category!='all': where+=' AND category=?';params.append(category)
    with connect() as con:
        rows=con.execute('SELECT id,category,title,body,author_label,status,created_at FROM community_posts '+where+
          ' ORDER BY id DESC LIMIT 50',tuple(params)).fetchall()
    return response({'items':[dict(x) for x in rows],'mine':mine})

def create_post(uid,name,d):
    category=field(d,'category',16)
    if category not in CATEGORIES: raise RequestError(400,'게시판 분류 오류')
    title=field(d,'title',120,3);body=field(d,'content',3500,10)
    with connect() as con:
        rate(con,'community_posts',uid,5)
        row=con.execute('''INSERT INTO community_posts(author_id,author_label,category,title,body)
         VALUES (?,?,?,?,?) RETURNING id''',(uid,name,category,title,body)).fetchone()
    return response({'ok':True,'id':row['id'],'status':'pending','message':'게시글 접수 완료 · 운영자 승인 대기'},201)

def list_comments(query):
    try: post_id=int(query.get('postId',['0'])[0])
    except (TypeError,ValueError): raise RequestError(400,'게시글 번호 오류') from None
    if post_id<=0: raise RequestError(400,'게시글 번호 오류')
    with connect() as con:
        rows=con.execute('''SELECT c.id,c.author_label,c.body,c.created_at FROM community_comments c
         JOIN community_posts p ON p.id=c.post_id WHERE c.post_id=?
         AND c.status='approved' AND p.status='approved' ORDER BY c.id ASC LIMIT 100''',(post_id,)).fetchall()
    return response({'items':[dict(x) for x in rows]})

def create_comment(uid,name,d):
    try: post_id=int(d.get('postId',0))
    except (TypeError,ValueError): raise RequestError(400,'게시글 번호 오류') from None
    if post_id<=0: raise RequestError(400,'게시글 번호 오류')
    body=field(d,'content',800,2)
    with connect() as con:
        row=con.execute("SELECT id FROM community_posts WHERE id=? AND status='approved'",(post_id,)).fetchone()
        if not row: raise RequestError(404,'공개된 게시글이 없습니다.')
        rate(con,'community_comments',uid,20)
        row=con.execute('''INSERT INTO community_comments(post_id,author_id,author_label,body)
        VALUES (?,?,?,?) RETURNING id''',(post_id,uid,name,body)).fetchone()
    return response({'ok':True,'id':row['id'],'status':'pending','message':'댓글 접수 완료 · 승인 대기'},201)

def pending():
    with connect() as con:
        apps=con.execute('''SELECT id,shop_name,contact_name,phone,email,category,shop_location,description,created_at
        FROM merchant_applications WHERE status='pending' ORDER BY id LIMIT 50''').fetchall()
        posts=con.execute('''SELECT id,category,title,body,author_label,created_at
        FROM community_posts WHERE status='pending' ORDER BY id LIMIT 50''').fetchall()
        comments=con.execute('''SELECT id,post_id,author_label,body,created_at
        FROM community_comments WHERE status='pending' ORDER BY id LIMIT 50''').fetchall()
    return response({'applications':[dict(x) for x in apps],'posts':[dict(x) for x in posts],'comments':[dict(x) for x in comments]})

def moderate(d):
    kind=field(d,'kind',20);status=field(d,'status',20)
    if kind not in TABLES or status not in {'approved','rejected'}: raise RequestError(400,'처리 항목 오류')
    try: rid=int(d.get('id',0))
    except (TypeError,ValueError): raise RequestError(400,'번호 오류') from None
    if rid<=0: raise RequestError(400,'번호 오류')
    if kind=='applications' and status=='approved':status='reviewed'
    table=TABLES[kind]
    with connect() as con:
        row=con.execute(f'''UPDATE {table} SET status=?,reviewed_at=CURRENT_TIMESTAMP
        WHERE id=? AND status='pending' RETURNING id''',(status,rid)).fetchone()
    if not row: raise RequestError(404,'처리 가능한 검수 항목이 없습니다.')
    return response({'ok':True,'id':rid,'status':status})

def handle(method,path_and_query,raw_headers,raw_body):
    headers={str(k).lower():str(v) for k,v in raw_headers.items()}
    path=urlsplit(path_and_query).path.rstrip('/')
    query=parse_qs(urlsplit(path_and_query).query)
    try:
        if method not in ('GET','POST'): raise RequestError(405,'허용되지 않은 요청 방식')
        if not use_postgres():raise RequestError(503,'Neon 데이터베이스 연결이 설정되지 않았습니다.')
        if method=='POST':check_origin(headers)
        if path=='/api/merchant-applications':
            uid,_=member(headers)
            return list_applications(uid) if method=='GET' else create_application(uid,body_json(raw_body,headers))
        if path=='/api/community/posts':
            if method=='GET':return list_posts(query,headers)
            uid,name=member(headers)
            return create_post(uid,name,body_json(raw_body,headers))
        if path=='/api/community/comments':
            if method=='GET':return list_comments(query)
            uid,name=member(headers)
            return create_comment(uid,name,body_json(raw_body,headers))
        if path=='/api/community/moderation':
            user=admin(headers)
            if method=='GET':return pending()
            if not secrets.compare_digest(headers.get('x-garak-csrf',''),str(user['csrf'])):
                raise RequestError(403,'CSRF 검증 실패')
            return moderate(body_json(raw_body,headers))
        raise RequestError(404,'API 경로를 찾을 수 없습니다.')
    except RequestError as exc:
        return response({'error':exc.message},exc.status)
    except Exception:
        return response({'error':'서버 오류입니다. 잠시 후 다시 시도해 주세요.'},500)
