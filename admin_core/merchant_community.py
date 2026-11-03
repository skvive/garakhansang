"""Persistent merchant intake and moderated member community for Garak Hansang."""
from __future__ import annotations
import datetime as dt
import hashlib
import json
import os
import re
import secrets
from http.cookies import SimpleCookie
from urllib.parse import parse_qs, urlsplit
from functools import lru_cache
from .database import connect
from .pgcompat import use_postgres

CATS = {"notice", "season", "story", "question"}
ADMIN_ROLES = {"superadmin", "ops", "content"}

class Err(Exception):
    def __init__(self, code, message):
        self.code, self.message = code, message

def reply(obj, code=200):
    return code, {"Content-Type":"application/json; charset=utf-8","Cache-Control":"no-store","X-Content-Type-Options":"nosniff"}, json.dumps(obj,ensure_ascii=False,default=str).encode("utf-8")

def field(data, key, maximum, minimum=1):
    s=data.get(key,"")
    if not isinstance(s,str): raise Err(400,key+" 형식 오류")
    s=s.strip()
    if not minimum<=len(s)<=maximum or any(ord(c)<32 and c not in "\n\r\t" for c in s):
        raise Err(400,key+" 길이 또는 형식을 확인하세요.")
    return s

def payload(raw, headers):
    if headers.get("content-type","").split(";")[0].strip().lower()!="application/json":
        raise Err(415,"JSON 형식으로 전송해야 합니다.")
    if not 2<=len(raw)<=12000: raise Err(413,"요청 본문 크기를 확인하세요.")
    try: data=json.loads(raw)
    except (ValueError,UnicodeError): raise Err(400,"JSON 형식 오류") from None
    if not isinstance(data,dict): raise Err(400,"JSON 객체가 필요합니다.")
    return data

def check_origin(headers):
    origin=headers.get("origin")
    if origin:
        o=urlsplit(origin)
        host=headers.get("host","")
        if o.netloc.lower()!=host.lower() or o.scheme not in ("https","http"):
            raise Err(403,"요청 출처가 일치하지 않습니다.")
        if o.scheme=="http" and not host.startswith(("localhost:","127.0.0.1:")):
            raise Err(403,"HTTPS 연결이 필요합니다.")

@lru_cache(maxsize=2)
def jwks(url):
    import jwt
    return jwt.PyJWKClient(url, cache_jwk_set=True, lifespan=300, timeout=5)

def member(headers):
    import jwt
    auth=headers.get("authorization","")
    if not auth.startswith("Bearer ") or len(auth)>6000:
        raise Err(401,"회원 로그인이 필요합니다.")
    base=os.getenv("NEON_AUTH_BASE_URL","").rstrip("/")
    if not base.startswith("https://"):raise Err(503,"Neon Auth 설정이 없습니다.")
    origin=urlsplit(base)
    issuer=origin.scheme+"://"+origin.netloc
    try:
        token=auth[7:]
        key=jwks(base+"/.well-known/jwks.json").get_signing_key_from_jwt(token)
        claims=jwt.decode(token,key.key,algorithms=["EdDSA","RS256"],issuer=issuer,
                          options={"require":["sub","exp","iss"],"verify_aud":False},leeway=30)
        user_id=claims["sub"]
        if not isinstance(user_id,str) or not 1<=len(user_id)<=128:raise ValueError("sub")
        return {"id":user_id,"name":str(claims.get("name") or claims.get("email") or "회원")[:60]}
    except Exception:
        raise Err(401,"로그인 토큰이 만료되었거나 유효하지 않습니다.") from None

def admin(headers,write=False):
    cookies=SimpleCookie()
    try:cookies.load(headers.get("cookie",""))
    except Exception:raise Err(401,"관리자 로그인이 필요합니다.")
    value=cookies.get("garak_admin_session")
    if not value or len(value.value)>512:raise Err(401,"관리자 로그인이 필요합니다.")
    ident=hashlib.sha256(value.value.encode()).hexdigest()
    with connect() as db:
        r=db.execute("SELECT u.role,u.active,s.csrf,s.expires_at FROM sessions s JOIN users u ON u.id=s.user_id WHERE s.id_hash=?",(ident,)).fetchone()
    now=dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")
    if not r or not r["active"] or r["role"] not in ADMIN_ROLES or r["expires_at"]<=now:
        raise Err(403,"관리자 검수 권한이 없습니다.")
    if write and not secrets.compare_digest(headers.get("x-garak-csrf",""),r["csrf"]):
        raise Err(403,"CSRF 검증에 실패했습니다.")

def limit(db, table, user_id, maximum):
    if table not in {"merchant_applications","community_posts","community_comments"}:raise Err(500,"내부 설정 오류")
    since=dt.datetime.now(dt.timezone.utc)-dt.timedelta(hours=24)
    n=db.execute("SELECT COUNT(*) n FROM "+table+" WHERE author_id=? AND created_at>=?",(user_id,since)).fetchone()["n"]
    if n>=maximum:raise Err(429,"일일 신청·작성 제한을 초과했습니다.")

def apply_create(user,d):
    shop=field(d,"shopName",80)
    name=field(d,"contactName",50)
    phone=field(d,"phone",30)
    email=field(d,"email",120)
    category=field(d,"category",60)
    location=field(d,"location",120,0)
    about=field(d,"description",1500,15)
    if d.get("consent") is not True:raise Err(400,"개인정보 동의가 필요합니다.")
    if not re.fullmatch(r"\+?[0-9][0-9\s\-()]{6,28}",phone):raise Err(400,"전화번호 형식을 확인하세요.")
    if not re.fullmatch(r"[^\s@]+@[^\s@]+\.[^\s@]+",email):raise Err(400,"이메일 형식을 확인하세요.")
    with connect() as db:
        limit(db,"merchant_applications",user["id"],3)
        r=db.execute("""INSERT INTO merchant_applications(author_id,shop_name,contact_name,phone,email,category,shop_location,description,consent_at)
             VALUES(?,?,?,?,?,?,?,?,CURRENT_TIMESTAMP) RETURNING id""",(user["id"],shop,name,phone,email,category,location,about)).fetchone()
    return reply({"ok":True,"id":r["id"],"status":"pending"},201)

def apply_list(user):
    with connect() as db:
        rows=db.execute("SELECT id,shop_name,category,status,created_at FROM merchant_applications WHERE author_id=? ORDER BY id DESC LIMIT 30",(user["id"],)).fetchall()
    return reply({"items":[dict(x) for x in rows]})

def post_create(user,d):
    category=field(d,"category",16)
    if category not in CATS:raise Err(400,"게시판 분류 오류")
    title=field(d,"title",120,3)
    body=field(d,"content",3500,10)
    with connect() as db:
        limit(db,"community_posts",user["id"],5)
        r=db.execute("INSERT INTO community_posts(author_id,author_label,category,title,body) VALUES(?,?,?,?,?) RETURNING id",
                     (user["id"],user["name"],category,title,body)).fetchone()
    return reply({"ok":True,"id":r["id"],"status":"pending"},201)

def post_list(query,user):
    category=query.get("category",["all"])[0]
    mine=query.get("mine",["0"])[0]=="1"
    if category!="all" and category not in CATS:raise Err(400,"게시판 분류 오류")
    if mine and not user:raise Err(401,"회원 로그인이 필요합니다.")
    sql="SELECT id,category,title,body,author_label,status,created_at FROM community_posts WHERE "
    params=[]
    if mine:sql+="author_id=?";params.append(user["id"])
    else:sql+="status='approved'"
    if category!="all":sql+=" AND category=?";params.append(category)
    sql+=" ORDER BY id DESC LIMIT 50"
    with connect() as db:rows=db.execute(sql,tuple(params)).fetchall()
    return reply({"items":[dict(x) for x in rows],"mine":mine})

def comment_create(user,d):
    try:post_id=int(d.get("postId",0))
    except (ValueError,TypeError):raise Err(400,"게시글 번호 오류") from None
    if post_id<1:raise Err(400,"게시글 번호 오류")
    body=field(d,"content",800,2)
    with connect() as db:
        r=db.execute("SELECT id FROM community_posts WHERE id=? AND status='approved'",(post_id,)).fetchone()
        if not r:raise Err(404,"공개된 게시글이 아닙니다.")
        limit(db,"community_comments",user["id"],20)
        r=db.execute("INSERT INTO community_comments(post_id,author_id,author_label,body) VALUES(?,?,?,?) RETURNING id",
                     (post_id,user["id"],user["name"],body)).fetchone()
    return reply({"ok":True,"id":r["id"],"status":"pending"},201)

def comment_list(query):
    try:post_id=int(query.get("postId",["0"])[0])
    except (ValueError,TypeError):raise Err(400,"게시글 번호 오류") from None
    if post_id<1:raise Err(400,"게시글 번호 오류")
    with connect() as db:
        rows=db.execute("""SELECT c.id,c.author_label,c.body,c.created_at FROM community_comments c
           JOIN community_posts p ON p.id=c.post_id WHERE c.post_id=? AND c.status='approved' AND p.status='approved'
           ORDER BY c.id LIMIT 100""",(post_id,)).fetchall()
    return reply({"items":[dict(x) for x in rows]})

def moderation_list():
    with connect() as db:
        a=db.execute("SELECT id,shop_name,contact_name,phone,email,category,shop_location,description,status FROM merchant_applications WHERE status='pending' ORDER BY id LIMIT 50").fetchall()
        p=db.execute("SELECT id,category,title,body,author_label,status FROM community_posts WHERE status='pending' ORDER BY id LIMIT 50").fetchall()
        c=db.execute("SELECT id,post_id,body,author_label,status FROM community_comments WHERE status='pending' ORDER BY id LIMIT 50").fetchall()
    return reply({"applications":[dict(x) for x in a],"posts":[dict(x) for x in p],"comments":[dict(x) for x in c]})

def moderation_update(d):
    kind=field(d,"kind",20)
    status=field(d,"status",20)
    tables={"applications":"merchant_applications","posts":"community_posts","comments":"community_comments"}
    if kind not in tables or status not in {"approved","rejected"}:raise Err(400,"검수 항목 오류")
    try:item_id=int(d.get("id",0))
    except (ValueError,TypeError):raise Err(400,"항목 번호 오류") from None
    if item_id<1:raise Err(400,"항목 번호 오류")
    # Review of an application is not formal seller admission.
    if kind=="applications" and status=="approved":status="reviewed"
    with connect() as db:
        r=db.execute("UPDATE "+tables[kind]+" SET status=?,reviewed_at=CURRENT_TIMESTAMP WHERE id=? AND status='pending' RETURNING id",(status,item_id)).fetchone()
    if not r:raise Err(404,"검수 대기 항목이 없습니다.")
    return reply({"ok":True,"id":item_id,"status":status})

def handle(method,raw_path,original_headers,body):
    h={str(k).lower():str(v) for k,v in original_headers.items()}
    parts=urlsplit(raw_path)
    path=parts.path.rstrip("/")
    q=parse_qs(parts.query)
    try:
        if method not in ("GET","POST"):raise Err(405,"허용되지 않은 메서드")
        if not use_postgres():raise Err(503,"Neon DB 연결이 설정되지 않았습니다.")
        if method=="POST":check_origin(h)
        if path=="/api/merchant-applications":
            u=member(h)
            return apply_list(u) if method=="GET" else apply_create(u,payload(body,h))
        if path=="/api/community/posts":
            u=member(h) if method=="POST" or "authorization" in h or q.get("mine")==["1"] else None
            return post_list(q,u) if method=="GET" else post_create(u,payload(body,h))
        if path=="/api/community/comments":
            return comment_list(q) if method=="GET" else comment_create(member(h),payload(body,h))
        if path=="/api/community/moderation":
            admin(h,method=="POST")
            return moderation_list() if method=="GET" else moderation_update(payload(body,h))
        raise Err(404,"API 경로를 찾을 수 없습니다.")
    except Err as e:return reply({"error":e.message},e.code)
    except Exception:return reply({"error":"서버 오류가 발생했습니다. 운영자에게 문의하세요."},500)
