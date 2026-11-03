"""Real Neon-backed applications and moderated community API. Existing shop demos are separate."""
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

CATEGORIES = {"notice", "season", "story", "question"}
ADMIN_ROLES = {"superadmin", "ops", "content"}
TABLES = {"applications":"merchant_applications", "posts":"community_posts", "comments":"community_comments"}


class RequestError(Exception):
    def __init__(self, status, message):
        self.status, self.message = status, message


def response(payload, status=200):
    return status, {"Content-Type":"application/json; charset=utf-8",
                    "Cache-Control":"no-store", "X-Content-Type-Options":"nosniff"}, (
        json.dumps(payload, ensure_ascii=False, default=str).encode("utf-8"))


def field(data, name, minimum, maximum):
    value = data.get(name)
    if not isinstance(value, str):
        raise RequestError(400, "필수 항목 형식 오류: " + name)
    value = value.strip()
    if not minimum <= len(value) <= maximum:
        raise RequestError(400, name + " 길이 오류")
    if any(ord(ch) < 32 and ch not in "\n\r\t" for ch in value):
        raise RequestError(400, name + " 형식 오류")
    return value


def payload(body, headers):
    if headers.get("content-type","").split(";")[0].strip().lower() != "application/json":
        raise RequestError(415, "JSON 요청만 허용합니다.")
    if not 2 <= len(body) <= 12000:
        raise RequestError(413, "요청 본문 크기 오류")
    try:
        value = json.loads(body)
    except (ValueError, UnicodeError):
        raise RequestError(400, "JSON 형식 오류") from None
    if not isinstance(value, dict):
        raise RequestError(400, "JSON 객체가 필요합니다.")
    return value


def check_origin(headers):
    origin, host = headers.get("origin",""), headers.get("host","")
    if not origin:
        return
    u = urlsplit(origin)
    if u.netloc.lower() != host.lower() or u.scheme not in ("https","http"):
        raise RequestError(403, "허용되지 않은 요청 출처")
    if u.scheme != "https" and not host.startswith(("localhost:","127.0.0.1:")):
        raise RequestError(403, "보안 연결이 필요합니다.")


@lru_cache(maxsize=1)
def jwks(url):
    import jwt
    return jwt.PyJWKClient(url, cache_jwk_set=True, lifespan=300, timeout=5)


def member(headers):
    import jwt
    authorization = headers.get("authorization","")
    if not authorization.startswith("Bearer ") or len(authorization) > 6000:
        raise RequestError(401, "회원 로그인이 필요합니다.")
    base = os.environ.get("NEON_AUTH_BASE_URL","").rstrip("/")
    if not base.startswith("https://"):
        raise RequestError(503, "회원 인증 설정이 필요합니다.")
    try:
        token = authorization[7:]
        key = jwks(base + "/.well-known/jwks.json").get_signing_key_from_jwt(token)
        issuer = urlsplit(base).scheme + "://" + urlsplit(base).netloc
        claims = jwt.decode(token, key.key, algorithms=["EdDSA","RS256"],
                            issuer=issuer, leeway=30,
                            options={"require":["exp","sub","iss"],"verify_aud":False})
        uid = claims.get("sub")
        if not isinstance(uid,str) or not 1 <= len(uid) <= 128:
            raise ValueError("invalid identity")
        return {"id":uid,"name":str(claims.get("name") or "회원")[:60]}
    except Exception:
        raise RequestError(401,"인증이 만료되었거나 유효하지 않습니다. 다시 로그인하세요.") from None


def admin(headers, csrf=False):
    jar = SimpleCookie()
    try:
        jar.load(headers.get("cookie",""))
    except Exception:
        raise RequestError(401,"관리자 로그인이 필요합니다.") from None
    sid = jar.get("garak_admin_session")
    if not sid or len(sid.value) > 512:
        raise RequestError(401,"관리자 로그인이 필요합니다.")
    digest = hashlib.sha256(sid.value.encode()).hexdigest()
    with connect() as con:
        row = con.execute("SELECT u.role,u.active,s.csrf,s.expires_at FROM sessions s "
                          "JOIN users u ON u.id=s.user_id WHERE s.id_hash=?",(digest,)).fetchone()
    now = dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")
    if not row or not row["active"] or row["role"] not in ADMIN_ROLES or row["expires_at"] <= now:
        raise RequestError(403,"관리자 권한이 필요합니다.")
    if csrf and not secrets.compare_digest(headers.get("x-garak-csrf",""),row["csrf"]):
        raise RequestError(403,"CSRF 검증 실패")


def rate(con, table, user_id, cap):
    if table not in TABLES.values():
        raise RequestError(500,"서버 설정 오류")
    t = dt.datetime.now(dt.timezone.utc) - dt.timedelta(hours=24)
    count = con.execute("SELECT COUNT(*) AS n FROM " + table +
                        " WHERE author_id=? AND created_at>=?",(user_id,t)).fetchone()["n"]
    if count >= cap:
        raise RequestError(429,"접수 횟수를 초과했습니다. 하루 뒤 다시 시도해 주세요.")


def create_application(user, d):
    shop = field(d,"shopName",1,80)
    contact = field(d,"contactName",1,50)
    phone = field(d,"phone",7,30)
    email = field(d,"email",5,120)
    category = field(d,"category",1,60)
    location = field(d,"location",0,120)
    detail = field(d,"description",15,1500)
    if d.get("consent") is not True:
        raise RequestError(400,"개인정보 수집 및 이용 동의가 필요합니다.")
    if not re.fullmatch(r"\+?[0-9][0-9\s()\-]{6,28}",phone) or not re.fullmatch(r"[^\s@]+@[^\s@]+\.[^\s@]+",email):
        raise RequestError(400,"이메일 또는 전화번호 형식 오류")
    with connect() as con:
        rate(con,"merchant_applications",user["id"],3)
        pending=con.execute("SELECT id FROM merchant_applications WHERE author_id=? AND shop_name=? AND status='pending' ORDER BY id DESC LIMIT 1",(user["id"],shop)).fetchone()
        if pending:
            raise RequestError(409,"동일 상호의 입점 신청이 검토 대기 중입니다.")
        row=con.execute("INSERT INTO merchant_applications "
                        "(author_id,shop_name,contact_name,phone,email,category,shop_location,description,consent_at) "
                        "VALUES(?,?,?,?,?,?,?,?,CURRENT_TIMESTAMP) RETURNING id",
                        (user["id"],shop,contact,phone,email,category,location,detail)).fetchone()
    return response({"ok":True,"id":row["id"],"status":"pending","message":"입점 신청 접수 완료 · 검토 대기"},201)


def my_applications(user):
    with connect() as con:
        rows=con.execute("SELECT id,shop_name,category,status,created_at FROM merchant_applications "
                         "WHERE author_id=? ORDER BY id DESC LIMIT 30",(user["id"],)).fetchall()
    return response({"items":[dict(r) for r in rows]})


def create_post(user,d):
    category=field(d,"category",1,16)
    if category not in CATEGORIES:
        raise RequestError(400,"게시판 분류 오류")
    title=field(d,"title",3,120)
    body=field(d,"content",10,3500)
    with connect() as con:
        rate(con,"community_posts",user["id"],5)
        row=con.execute("INSERT INTO community_posts(author_id,author_label,category,title,body) "
                        "VALUES(?,?,?,?,?) RETURNING id",
                        (user["id"],user["name"],category,title,body)).fetchone()
    return response({"ok":True,"id":row["id"],"status":"pending","message":"게시글 접수 완료 · 승인 대기"},201)


def posts(query,user):
    cat=query.get("category",["all"])[0]
    mine=query.get("mine",["0"])[0]=="1"
    if cat!="all" and cat not in CATEGORIES:
        raise RequestError(400,"게시판 분류 오류")
    if mine and user is None:
        raise RequestError(401,"회원 로그인이 필요합니다.")
    if mine:
        sql="SELECT id,category,title,body,author_label,status,created_at FROM community_posts WHERE author_id=?"
        params=[user["id"]]
    else:
        sql="SELECT id,category,title,body,author_label,status,created_at FROM community_posts WHERE status='approved'"
        params=[]
    if cat!="all":
        sql+=" AND category=?"
        params.append(cat)
    with connect() as con:
        rows=con.execute(sql+" ORDER BY id DESC LIMIT 50",tuple(params)).fetchall()
    return response({"items":[dict(r) for r in rows],"mine":mine})


def create_comment(user,d):
    try:
        post_id=int(d.get("postId",0))
    except (ValueError,TypeError):
        raise RequestError(400,"게시글 번호 오류") from None
    if post_id<1:
        raise RequestError(400,"게시글 번호 오류")
    body=field(d,"content",2,800)
    with connect() as con:
        post=con.execute("SELECT id FROM community_posts WHERE id=? AND status='approved'",(post_id,)).fetchone()
        if not post:
            raise RequestError(404,"공개된 게시글이 없습니다.")
        rate(con,"community_comments",user["id"],20)
        row=con.execute("INSERT INTO community_comments(post_id,author_id,author_label,body) "
                        "VALUES(?,?,?,?) RETURNING id",(post_id,user["id"],user["name"],body)).fetchone()
    return response({"ok":True,"id":row["id"],"status":"pending","message":"댓글 접수 완료 · 승인 대기"},201)


def comments(query):
    try:
        post_id=int(query.get("postId",["0"])[0])
    except (ValueError,TypeError):
        raise RequestError(400,"게시글 번호 오류") from None
    if post_id<1:
        raise RequestError(400,"게시글 번호 오류")
    with connect() as con:
        rows=con.execute("SELECT c.id,c.author_label,c.body,c.created_at FROM community_comments c "
                         "JOIN community_posts p ON p.id=c.post_id WHERE c.post_id=? "
                         "AND c.status='approved' AND p.status='approved' "
                         "ORDER BY c.id LIMIT 100",(post_id,)).fetchall()
    return response({"items":[dict(r) for r in rows]})


def moderation():
    with connect() as con:
        applications=con.execute("SELECT id,shop_name,contact_name,phone,email,category,shop_location,description "
                                 "FROM merchant_applications WHERE status='pending' ORDER BY id LIMIT 50").fetchall()
        published=con.execute("SELECT id,category,title,body,author_label FROM community_posts "
                              "WHERE status='pending' ORDER BY id LIMIT 50").fetchall()
        replies=con.execute("SELECT id,post_id,body,author_label FROM community_comments "
                            "WHERE status='pending' ORDER BY id LIMIT 50").fetchall()
    return response({"applications":[dict(r) for r in applications],
                     "posts":[dict(r) for r in published],
                     "comments":[dict(r) for r in replies]})


def review(d):
    kind=field(d,"kind",1,20)
    status=field(d,"status",1,20)
    if kind not in TABLES or status not in ("approved","rejected"):
        raise RequestError(400,"검수 상태 오류")
    try:
        item_id=int(d.get("id",0))
    except (TypeError,ValueError):
        raise RequestError(400,"번호 오류") from None
    if item_id<1:
        raise RequestError(400,"번호 오류")
    table=TABLES[kind]
    if kind=="applications" and status=="approved":
        status="reviewed"  # Not formal merchant admission.
    with connect() as con:
        row=con.execute("UPDATE "+table+" SET status=?, reviewed_at=CURRENT_TIMESTAMP "
                        "WHERE id=? AND status='pending' RETURNING id",
                        (status,item_id)).fetchone()
    if row is None:
        raise RequestError(404,"검토 대기 항목이 없습니다.")
    return response({"ok":True,"id":item_id,"status":status})


def handle(method,path,raw_headers,body):
    headers={str(k).lower():str(v) for k,v in raw_headers.items()}
    u=urlsplit(path)
    path=u.path.rstrip("/")
    query=parse_qs(u.query)
    try:
        if method not in ("GET","POST"):
            raise RequestError(405,"허용되지 않은 방식")
        if not use_postgres():
            raise RequestError(503,"Neon 데이터베이스가 연결되지 않았습니다.")
        if method=="POST":
            check_origin(headers)
        if path=="/api/merchant-applications":
            user=member(headers)
            return my_applications(user) if method=="GET" else create_application(user,payload(body,headers))
        if path=="/api/community/posts":
            user=member(headers) if ("authorization" in headers or query.get("mine")==["1"] or method=="POST") else None
            return posts(query,user) if method=="GET" else create_post(user,payload(body,headers))
        if path=="/api/community/comments":
            return comments(query) if method=="GET" else create_comment(member(headers),payload(body,headers))
        if path=="/api/community/moderation":
            admin(headers,csrf=method=="POST")
            return moderation() if method=="GET" else review(payload(body,headers))
        raise RequestError(404,"요청 경로가 없습니다.")
    except RequestError as e:
        return response({"error":e.message},e.status)
    except Exception as e:
        # No SQL, phone numbers, addresses, tokens or user text in logs.
        print("merchant_api_error="+type(e).__name__)
        return response({"error":"서버 오류입니다. 운영자에게 문의해 주세요."},500)
