"""Neon-backed merchant intake and moderated community endpoints."""
from __future__ import annotations
import datetime as dt
import hashlib
import json
import os
import re
import secrets
from functools import lru_cache
from http.cookies import SimpleCookie
from urllib.parse import parse_qs, urlsplit

from .database import connect
from .pgcompat import use_postgres

KINDS = {'notice', 'season', 'story', 'question'}
TABLES = {'applications': 'merchant_applications', 'posts': 'community_posts', 'comments': 'community_comments'}
MAX_BODY = 12000

class APIError(Exception):
    def __init__(self, status, message):
        self.status, self.message = status, message

def respond(data, status=200):
    return status, {'Content-Type':'application/json; charset=utf-8','Cache-Control':'no-store','X-Content-Type-Options':'nosniff'}, json.dumps(data, ensure_ascii=False, default=str).encode('utf-8')

def required(data, key, limit, minimum=1):
    value = data.get(key)
    if not isinstance(value, str):
        raise APIError(400, key + ' 입력이 필요합니다.')
    value = value.strip()
    if not minimum <= len(value) <= limit or any(ord(ch)<32 and ch not in '\n\r\t' for ch in value):
        raise APIError(400, key + ' 길이 또는 형식이 올바르지 않습니다.')
    return value

def payload(body, headers):
    if headers.get('content-type','').split(';')[0].lower().strip() != 'application/json':
        raise APIError(415, 'JSON 요청만 허용됩니다.')
    if not 2 <= len(body) <= MAX_BODY:
        raise APIError(413, '요청 본문 크기를 확인하세요.')
    try:
        result = json.loads(body)
    except (ValueError, UnicodeError):
        raise APIError(400, 'JSON 구문이 잘못되었습니다.') from None
    if not isinstance(result, dict):
        raise APIError(400, 'JSON 객체가 필요합니다.')
    return result

def origin_check(headers, required_origin=False):
    origin, host = headers.get('origin',''), headers.get('host','')
    if not origin:
        if required_origin:
            raise APIError(403, '요청 출처 확인이 필요합니다.')
        return
    parsed = urlsplit(origin)
    if parsed.netloc.lower() != host.lower() or (parsed.scheme != 'https' and not host.startswith(('localhost:', '127.0.0.1:'))):
        raise APIError(403, '요청 출처가 일치하지 않습니다.')

@lru_cache(maxsize=2)
def jwks_client(url):
    import jwt
    return jwt.PyJWKClient(url, cache_jwk_set=True, lifespan=300, timeout=5)

def member(headers):
    import jwt
    value = headers.get('authorization','')
    if not value.startswith('Bearer ') or len(value)>6000:
        raise APIError(401, '회원 로그인 후 이용하세요.')
    base = os.environ.get('NEON_AUTH_BASE_URL','').strip().rstrip('/')
    if not base.startswith('https://') or '.neon.tech' not in urlsplit(base).hostname:
        raise APIError(503, '회원 인증 설정이 없습니다.')
    try:
        token = value[7:]
        key = jwks_client(base+'/.well-known/jwks.json').get_signing_key_from_jwt(token)
        claims = jwt.decode(token, key.key, algorithms=['EdDSA','RS256'], issuer=urlsplit(base).scheme+'://'+urlsplit(base).netloc,
                            options={'require':['exp','sub','iss'],'verify_aud':False}, leeway=30)
        uid = claims['sub']
        if not isinstance(uid,str) or not 1<=len(uid)<=128:
            raise ValueError('subject')
        return {'id':uid,'label':str(claims.get('name') or '회원')[:60]}
    except Exception:
        raise APIError(401, '인증 토큰이 유효하지 않습니다. 다시 로그인해 주세요.') from None

def admin(headers, write=False):
    jar = SimpleCookie()
    try: jar.load(headers.get('cookie',''))
    except Exception: raise APIError(401, '관리자 로그인이 필요합니다.') from None
    raw = jar.get('garak_admin_session')
    if raw is None or len(raw.value)>512: raise APIError(401, '관리자 로그인이 필요합니다.')
    session_id = hashlib.sha256(raw.value.encode()).hexdigest()
    with connect() as db:
        row = db.execute('SELECT u.id,u.role,u.active,s.csrf,s.expires_at FROM sessions s JOIN users u ON s.user_id=u.id WHERE s.id_hash=?',(session_id,)).fetchone()
    if not row or not row['active'] or row['role'] not in ('superadmin','ops','content') or row['expires_at'] <= dt.datetime.now(dt.timezone.utc).isoformat(timespec='seconds'):
        raise APIError(403, '운영자 승인 권한이 없습니다.')
    if write:
        origin_check(headers, True)
        csrf = headers.get('x-garak-csrf','')
        if not csrf or not secrets.compare_digest(csrf, row['csrf']):
            raise APIError(403, 'CSRF 검사 실패')
    return row['id']

def limit(db, table, uid, count, hours=24):
    if table not in TABLES.values(): raise APIError(500,'내부 설정 오류')
    since=dt.datetime.now(dt.timezone.utc)-dt.timedelta(hours=hours)
    row=db.execute('SELECT COUNT(*) AS n FROM '+table+' WHERE author_id=? AND created_at >= ?', (uid,since)).fetchone()
    if row['n']>=count: raise APIError(429,'요청 횟수 한도를 초과했습니다. 나중에 다시 시도하세요.')

def application_submit(uid, data):
    shop=required(data,'shopName',80)
    name=required(data,'contactName',50)
    phone=required(data,'phone',30)
    email=required(data,'email',120)
    category=required(data,'category',60)
    location=required(data,'location',120,0)
    description=required(data,'description',1500,15)
    if data.get('consent') is not True: raise APIError(400,'개인정보 이용에 동의해 주세요.')
    if not re.fullmatch(r'\+?[0-9][0-9\s()\-]{6,28}',phone): raise APIError(400,'전화번호 형식 오류')
    if not re.fullmatch(r'[^\s@]+@[^\s@]+\.[^\s@]+',email): raise APIError(400,'이메일 형식 오류')
    with connect() as db:
        limit(db,'merchant_applications',uid,3)
        recent=db.execute("SELECT id FROM merchant_applications WHERE author_id=? AND shop_name=? AND status='pending' ORDER BY id DESC LIMIT 1",(uid,shop)).fetchone()
        if recent: raise APIError(409,'이 상호의 검토 대기 신청이 이미 있습니다.')
        row=db.execute('INSERT INTO merchant_applications (author_id,shop_name,contact_name,phone,email,category,shop_location,description,consent_at) VALUES (?,?,?,?,?,?,?,?,CURRENT_TIMESTAMP) RETURNING id',
                       (uid,shop,name,phone,email,category,location,description)).fetchone()
    return respond({'ok':True,'id':row['id'],'status':'pending','message':'입점 신청이 접수됐습니다. 담당자 확인 전 정식 입점은 아닙니다.'},201)

def list_applications(uid):
    with connect() as db:
        rows=db.execute('SELECT id,shop_name,category,status,created_at FROM merchant_applications WHERE author_id=? ORDER BY id DESC LIMIT 30',(uid,)).fetchall()
    return respond({'items':[dict(r) for r in rows]})

def submit_post(uid,label,data):
    kind=required(data,'category',16)
    if kind not in KINDS: raise APIError(400,'게시글 분류 오류')
    title=required(data,'title',120,3)
    body=required(data,'content',3500,10)
    with connect() as db:
        limit(db,'community_posts',uid,5)
        row=db.execute('INSERT INTO community_posts(author_id,author_label,category,title,body) VALUES (?,?,?,?,?) RETURNING id',(uid,label,kind,title,body)).fetchone()
    return respond({'ok':True,'id':row['id'],'status':'pending','message':'게시글이 검토 대기로 접수됐습니다.'},201)

def list_posts(query,uid=None):
    kind=query.get('category',['all'])[0]
    mine=query.get('mine',['0'])[0]=='1'
    if kind!='all' and kind not in KINDS: raise APIError(400,'게시글 분류 오류')
    if mine and not uid: raise APIError(401,'회원 로그인이 필요합니다.')
    sql='SELECT id,category,title,body,author_label,status,created_at FROM community_posts WHERE '+('author_id=?' if mine else "status='approved'")
    params=[uid] if mine else []
    if kind!='all': sql+=' AND category=?'; params.append(kind)
    with connect() as db:
        rows=db.execute(sql+' ORDER BY id DESC LIMIT 50',tuple(params)).fetchall()
    return respond({'items':[dict(r) for r in rows],'mine':mine})

def submit_comment(uid,label,data):
    try: post=int(data.get('postId',0))
    except (ValueError,TypeError): raise APIError(400,'게시글 번호 오류') from None
    if post<1:raise APIError(400,'게시글 번호 오류')
    body=required(data,'content',800,2)
    with connect() as db:
        if not db.execute("SELECT id FROM community_posts WHERE id=? AND status='approved'",(post,)).fetchone():
            raise APIError(404,'공개된 게시글이 없습니다.')
        limit(db,'community_comments',uid,20)
        row=db.execute('INSERT INTO community_comments(post_id,author_id,author_label,body) VALUES (?,?,?,?) RETURNING id',(post,uid,label,body)).fetchone()
    return respond({'ok':True,'id':row['id'],'status':'pending','message':'댓글이 등록됐습니다. 승인 후 공개됩니다.'},201)

def list_comments(query):
    try: post=int(query.get('postId',['0'])[0])
    except (ValueError,TypeError): raise APIError(400,'게시글 번호 오류') from None
    if post<1: raise APIError(400,'게시글 번호 오류')
    with connect() as db:
        rows=db.execute("""SELECT c.id,c.author_label,c.body,c.created_at FROM community_comments c
                   JOIN community_posts p ON p.id=c.post_id
                   WHERE c.post_id=? AND c.status='approved' AND p.status='approved'
                   ORDER BY c.id ASC LIMIT 100""",(post,)).fetchall()
    return respond({'items':[dict(r) for r in rows]})

def list_moderation():
    with connect() as db:
        apps=db.execute("SELECT id,shop_name,contact_name,phone,email,category,shop_location,description,created_at FROM merchant_applications WHERE status='pending' ORDER BY id LIMIT 50").fetchall()
        posts=db.execute("SELECT id,category,title,body,author_label,created_at FROM community_posts WHERE status='pending' ORDER BY id LIMIT 50").fetchall()
        comments=db.execute("SELECT id,post_id,body,author_label,created_at FROM community_comments WHERE status='pending' ORDER BY id LIMIT 50").fetchall()
    return respond({'applications':[dict(r) for r in apps],'posts':[dict(r) for r in posts],'comments':[dict(r) for r in comments]})

def decide(data, actor):
    kind=required(data,'kind',20)
    state=required(data,'status',20)
    if kind not in TABLES or state not in ('approved','rejected'): raise APIError(400,'검토 항목 오류')
    try: item_id=int(data.get('id',0))
    except (ValueError,TypeError): raise APIError(400,'번호 오류') from None
    if item_id<=0:raise APIError(400,'번호 오류')
    table=TABLES[kind]
    # Application review does not establish a contract or a live shop.
    new_state = 'reviewed' if kind=='applications' and state=='approved' else state
    with connect() as db:
        changed=db.execute('UPDATE '+table+" SET status=?,reviewed_at=CURRENT_TIMESTAMP WHERE id=? AND status='pending' RETURNING id",(new_state,item_id)).fetchone()
        if changed:
            db.execute('INSERT INTO audit_logs(actor_id,action,target,target_id,at) VALUES (?,?,?,?,CURRENT_TIMESTAMP)',(actor,'moderation_'+new_state,table,item_id))
    if not changed: raise APIError(404,'이미 처리되었거나 존재하지 않는 항목입니다.')
    return respond({'ok':True,'id':item_id,'status':new_state})

def handle(method,url,request_headers,body):
    headers={str(k).lower():str(v) for k,v in request_headers.items()}
    parsed=urlsplit(url)
    path=parsed.path.rstrip('/')
    query=parse_qs(parsed.query)
    try:
        if method not in ('GET','POST'): raise APIError(405,'지원하지 않는 요청 방식입니다.')
        if not use_postgres(): raise APIError(503,'Neon DB 연결이 구성되지 않았습니다.')
        if method=='POST':origin_check(headers,False)
        if path=='/api/merchant-applications':
            user=member(headers)
            return list_applications(user['id']) if method=='GET' else application_submit(user['id'],payload(body,headers))
        if path=='/api/community/posts':
            user=member(headers) if ('authorization' in headers or query.get('mine')==['1'] or method=='POST') else None
            return list_posts(query,user['id'] if user else None) if method=='GET' else submit_post(user['id'],user['label'],payload(body,headers))
        if path=='/api/community/comments':
            return list_comments(query) if method=='GET' else submit_comment(*((lambda u:(u['id'],u['label']))(member(headers))),payload(body,headers))
        if path=='/api/community/moderation':
            actor=admin(headers,method=='POST')
            return list_moderation() if method=='GET' else decide(payload(body,headers),actor)
        raise APIError(404,'API 경로가 없습니다.')
    except APIError as exc:
        return respond({'error':exc.message},exc.status)
    except Exception:
        return respond({'error':'서버 내부 오류입니다. 운영자에게 문의해 주세요.'},500)
