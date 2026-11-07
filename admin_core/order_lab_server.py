"""Loopback-only functional order/merchant/rider/admin integration laboratory.

All customers, merchants, riders and payments are synthetic. The standalone server
cannot bind a public address and is never imported by the Vercel production handler.
No production auth, real payouts, FCM or live Stripe keys are used.
"""
from __future__ import annotations

import argparse
import hashlib
import hmac
import json
import os
import re
import secrets
import sqlite3
import threading
import time
from http import cookies
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit

from .database import connect, init_db, HERE
from .delivery_flow import DeliveryOrder, transition as domain_transition
from .mobile_commerce import list_verified_products, quote_cart, verified_merchants
from .order_p2_sandbox import (
    SandboxError, setup as setup_orders, attach_test_checkout, draft,
    dashboard, get_order, act, inbox, paid_webhook, _notify,
)

SITE = HERE / "storefront"
COOKIE = "garak_lab_session"
SESSION_MAX = 3600
ACCOUNT_NAME = re.compile(r"^[a-z][a-z0-9_-]{2,31}$")
JSON_CAP = 32_768


def sha_token(value):
    return hashlib.sha256(value.encode()).hexdigest()


def secret_hash(value, salt=None):
    salt = salt or secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac("sha256", value.encode(), salt, 200_000)
    return salt.hex() + ":" + digest.hex()


def check_secret(value, encoded):
    try:
        salt, expected = encoded.split(":")
        result = secret_hash(value, bytes.fromhex(salt)).split(":")[1]
        return hmac.compare_digest(result, expected)
    except (ValueError, TypeError):
        return False


def init_lab(path, accounts):
    """Initialize only a fresh disposable local SQLite path; keep existing rows."""
    if not str(Path(path).resolve()).startswith(str((HERE / "runtime").resolve())):
        # Tests can pass a separate TemporaryDirectory; CLI enforces runtime path.
        pass
    with init_db(path, seed=True, bootstrap=False) as db:
        setup_orders(db)
        db.executescript("""
        CREATE TABLE IF NOT EXISTS p3_lab_accounts(
          username TEXT PRIMARY KEY, subject TEXT NOT NULL, role TEXT NOT NULL,
          password_hash TEXT NOT NULL, enabled INTEGER NOT NULL DEFAULT 1
        );
        CREATE TABLE IF NOT EXISTS p3_lab_sessions(
          token_hash TEXT PRIMARY KEY, username TEXT NOT NULL REFERENCES p3_lab_accounts(username),
          csrf TEXT NOT NULL, expires INTEGER NOT NULL
        );
        CREATE TABLE IF NOT EXISTS p3_lab_rider_status(
          subject TEXT PRIMARY KEY, approved INTEGER NOT NULL DEFAULT 0,
          on_duty INTEGER NOT NULL DEFAULT 0
        );
        """)
        m = db.execute("SELECT id FROM merchants ORDER BY id LIMIT 1").fetchone()
        if m is None:
            raise RuntimeError("expected synthetic merchant fixture")
        mid = str(m["id"])
        # Synthetic merchant only; these seed products are never real stock.
        db.execute("UPDATE merchants SET verified=1,status='active' WHERE id=?", (m["id"],))
        defs = {
            "customer": ("c_demo", "customer"),
            "merchant": (mid, "merchant"),
            "rider": ("r_demo", "rider"),
            "ops": ("ops_demo", "ops"),
        }
        for username, (subject, role) in defs.items():
            password = accounts[username]
            if not isinstance(password, str) or len(password) < 14:
                raise ValueError("lab passwords must be >= 14 characters")
            db.execute("""INSERT INTO p3_lab_accounts
                  (username,subject,role,password_hash) VALUES(?,?,?,?)
                  ON CONFLICT(username) DO UPDATE SET password_hash=excluded.password_hash""",
                       (username, subject, role, secret_hash(password)))
        db.execute("""INSERT OR IGNORE INTO p3_lab_rider_status(subject,approved,on_duty)
                      VALUES('r_demo',1,1)""")
    return mid


class LabServer(ThreadingHTTPServer):
    daemon_threads = True
    allow_reuse_address = True

    def __init__(self, address, path):
        if address[0] not in ("127.0.0.1", "localhost", "::1"):
            raise RuntimeError("order laboratory cannot bind a non-loopback address")
        self.lab_db = str(path)
        self.lab_signing_secret = secrets.token_hex(24)
        self.auth_lock = threading.RLock()
        self.failed_logins = {}
        super().__init__(address, LabHandler)


class LabHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(SITE), **kwargs)

    def log_message(self, fmt, *args):
        # Never log passwords, tokens or submitted JSON.
        print("[order-lab] " + fmt % args)

    def end_headers(self):
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("X-Frame-Options", "DENY")
        self.send_header("Referrer-Policy", "no-referrer")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Security-Policy",
                         "default-src 'self'; style-src 'self'; script-src 'self';"
                         " img-src 'self' data:; connect-src 'self'; base-uri 'none'; frame-ancestors 'none'")
        super().end_headers()

    def json(self, body, status=200, extra=None):
        raw = json.dumps(body, ensure_ascii=False).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(raw)))
        for k, v in (extra or {}).items():
            self.send_header(k, v)
        self.end_headers()
        self.wfile.write(raw)

    def error(self, status, code):
        self.json({"error": code, "sandbox_only": True}, status)

    def body(self):
        if self.headers.get("Content-Type", "").split(";")[0].strip() != "application/json":
            raise SandboxError("json content-type required")
        length = int(self.headers.get("Content-Length", "0"))
        if not 1 <= length <= JSON_CAP:
            raise SandboxError("request body exceeds size limit")
        data = json.loads(self.rfile.read(length))
        if not isinstance(data, dict):
            raise SandboxError("json object required")
        return data

    def principal(self, require_csrf=False):
        cookie = cookies.SimpleCookie()
        try:
            cookie.load(self.headers.get("Cookie", ""))
        except cookies.CookieError:
            return None
        token = cookie.get(COOKIE)
        if token is None:
            return None
        with connect(self.server.lab_db) as db:
            row = db.execute("""SELECT a.subject,a.role,s.csrf,s.expires
              FROM p3_lab_sessions s JOIN p3_lab_accounts a ON a.username=s.username
              WHERE s.token_hash=? AND a.enabled=1""", (sha_token(token.value),)).fetchone()
        if row is None or row["expires"] <= int(time.time()):
            return None
        if require_csrf and not secrets.compare_digest(
                self.headers.get("X-Lab-CSRF", ""), row["csrf"]):
            return None
        return {"sub": row["subject"], "role": row["role"], "csrf": row["csrf"]}

    def origin_ok(self):
        origin = self.headers.get("Origin")
        return not origin or urlsplit(origin).netloc == self.headers.get("Host", "")

    def dispatch(self, method):
        path = urlsplit(self.path).path
        if path == "/lab/api/health" and method == "GET":
            return self.json({"ok": True, "mode": "LOOPBACK_SYNTHETIC",
                "real_payments": False, "live_delivery": False})
        if path == "/lab/api/login" and method == "POST":
            if not self.origin_ok(): return self.error(403, "bad_origin")
            data = self.body()
            username, password = data.get("username"), data.get("password")
            if not isinstance(username, str) or not ACCOUNT_NAME.fullmatch(username):
                return self.error(401, "login_failed")
            if not isinstance(password, str) or len(password) > 256:
                return self.error(401, "login_failed")
            with self.server.auth_lock:
                attempts = self.server.failed_logins.get(username, [])
                attempts = [v for v in attempts if v > time.time() - 300]
                if len(attempts) >= 6:
                    return self.error(429, "try_again_later")
                with connect(self.server.lab_db) as db:
                    account = db.execute("SELECT * FROM p3_lab_accounts WHERE username=? AND enabled=1",
                                         (username,)).fetchone()
                    if not account or not check_secret(password, account["password_hash"]):
                        self.server.failed_logins[username] = attempts + [time.time()]
                        return self.error(401, "login_failed")
                    token = secrets.token_urlsafe(32)
                    csrf = secrets.token_urlsafe(24)
                    db.execute("""INSERT INTO p3_lab_sessions(token_hash,username,csrf,expires)
                        VALUES(?,?,?,?)""", (sha_token(token), username, csrf, int(time.time()) + SESSION_MAX))
                    self.server.failed_logins.pop(username, None)
            return self.json({"role": account["role"], "csrf": csrf, "sandbox_only": True}, extra={
                "Set-Cookie": f"{COOKIE}={token}; HttpOnly; SameSite=Strict; Path=/lab; Max-Age={SESSION_MAX}"
            })
        if path == "/lab/api/me" and method == "GET":
            p = self.principal()
            return self.json({"authenticated": bool(p), "principal": p})
        if not path.startswith("/lab/api/"):
            if method != "GET": return self.error(405, "method_not_allowed")
            if path == "/" or path == "/order-lab":
                self.path = "/order-lab/index.html"
            elif path.startswith("/order-lab/") or path.startswith("/assets/"):
                self.path = path
            else:
                return self.error(404, "not_found")
            return super().do_GET()
        if method == "POST" and not self.origin_ok():
            return self.error(403, "bad_origin")
        p = self.principal(require_csrf=method == "POST")
        if p is None:
            return self.error(401, "login_required_or_csrf_invalid")
        role = p["role"]
        if path == "/lab/api/logout" and method == "POST":
            cookie = cookies.SimpleCookie()
            cookie.load(self.headers.get("Cookie", ""))
            if cookie.get(COOKIE):
                with connect(self.server.lab_db) as db:
                    db.execute("DELETE FROM p3_lab_sessions WHERE token_hash=?",
                                (sha_token(cookie[COOKIE].value),))
            return self.json({"ok": True}, extra={
                "Set-Cookie": f"{COOKIE}=; HttpOnly; SameSite=Strict; Path=/lab; Max-Age=0"
            })
        if method == "GET" and path == "/lab/api/products":
            with connect(self.server.lab_db) as db:
                items = list_verified_products(db)
                if role == "merchant":
                    items = [x for x in items if str(x.get("merchant", "")) in {
                        row["name"] for row in db.execute("SELECT name FROM merchants WHERE id=?",(p["sub"],))
                    }]
                return self.json({"items": items, "currency": "KRW", "demo": True})
        if method == "GET" and path == "/lab/api/orders":
            with connect(self.server.lab_db) as db:
                return self.json({"items": dashboard(db, p), "demo": True})
        if method == "GET" and path == "/lab/api/inbox":
            with connect(self.server.lab_db) as db:
                result = inbox(db, p)
                if role == "rider" and self.approved_rider(db, p):
                    rows = db.execute("""SELECT order_id,event,created_at
                        FROM p2_sandbox_outbox WHERE recipient_role='rider_pool'
                        AND event='job_available' ORDER BY id DESC LIMIT 100""").fetchall()
                    result += [dict(x) for x in rows]
                return self.json({"items": result, "demo": True})
        if method == "GET" and path == "/lab/api/dispatch":
            if role != "rider": return self.error(403, "rider_role_required")
            with connect(self.server.lab_db) as db:
                if not self.approved_rider(db, p):
                    return self.json({"items": []})
                rows = db.execute("""SELECT id,merchant_id,subtotal_krw,delivery_fee_krw,
                        state,version FROM p2_sandbox_orders
                        WHERE state='dispatch_requested' AND rider_id IS NULL LIMIT 50""").fetchall()
                return self.json({"items": [dict(x) for x in rows], "demo": True})
        if method == "GET" and path == "/lab/api/merchants":
            if role != "ops": return self.error(403, "operator_role_required")
            with connect(self.server.lab_db) as db:
                return self.json({"items": [dict(x) for x in db.execute(
                    "SELECT id,name,verified,status FROM merchants ORDER BY id LIMIT 100")]})
        if method == "GET" and path == "/lab/api/riders":
            if role != "ops": return self.error(403, "operator_role_required")
            with connect(self.server.lab_db) as db:
                return self.json({"items": [dict(x) for x in db.execute(
                    "SELECT subject,approved,on_duty FROM p3_lab_rider_status ORDER BY subject")]})
        if method == "GET" and path == "/lab/api/settlements":
            if role not in ("ops", "merchant"): return self.error(403, "role_not_permitted")
            with connect(self.server.lab_db) as db:
                clause = "" if role == "ops" else " AND merchant_id=?"
                params = () if role == "ops" else (p["sub"],)
                rows = db.execute("""SELECT id,merchant_id,total_krw,delivery_fee_krw,
                      (total_krw-delivery_fee_krw) AS merchandise_krw
                      FROM p2_sandbox_orders WHERE state='delivered'""" + clause, params).fetchall()
                results = []
                for row in rows:
                    merchant = db.execute("SELECT commission_bps FROM merchants WHERE id=?",
                                          (row["merchant_id"],)).fetchone()
                    bps = merchant["commission_bps"] if merchant else 0
                    fee = (row["merchandise_krw"] * bps) // 10000
                    results.append({"order_id": row["id"], "merchant_id": row["merchant_id"],
                                    "gross_krw": row["merchandise_krw"], "commission_krw": fee,
                                    "merchant_due_krw": row["merchandise_krw"] - fee,
                                    "payout_executed": False})
                return self.json({"items": results, "demo": True})
        if method == "POST" and path == "/lab/api/order/draft":
            if role != "customer": return self.error(403, "customer_role_required")
            data = self.body()
            with connect(self.server.lab_db) as db:
                quote = quote_cart(db, {"items": data.get("items"), "delivery_type": "delivery"})
                order = draft(db, p, quote, data.get("idempotency_key"),
                              delivery_fee_krw=2000)  # fixed synthetic fee, not sellable!
                return self.json({"order": order, "checkout_status": "SANDBOX_ONLY"}, 201)
        if method == "POST" and path == "/lab/api/merchants/approve":
            if role != "ops": return self.error(403, "operator_role_required")
            data = self.body()
            merchant_id = data.get("id")
            if type(merchant_id) is not int:
                return self.error(400, "merchant_id_required")
            with connect(self.server.lab_db) as db:
                cur = db.execute("""UPDATE merchants SET status='active',verified=1
                                WHERE id=? AND status IN ('pending','active')""",(merchant_id,))
                if cur.rowcount != 1:return self.error(404, "merchant_not_found")
                return self.json({"ok": True, "demo": True})
        if method == "POST" and path == "/lab/api/products/stock":
            if role not in ("ops","merchant"):return self.error(403, "role_not_permitted")
            data = self.body()
            slug, stock = data.get("slug"), data.get("stock")
            if not isinstance(slug, str) or type(stock) is not int or not 0 <= stock <= 10000:
                return self.error(400, "invalid_stock")
            with connect(self.server.lab_db) as db:
                if role == "ops":
                    cur = db.execute("UPDATE products SET stock=? WHERE slug=?",(stock,slug))
                else:
                    cur = db.execute("""UPDATE products SET stock=? WHERE slug=? AND merchant_id=?""",
                                     (stock,slug,p["sub"]))
                if cur.rowcount != 1:return self.error(404,"not_own_product")
                return self.json({"ok":True,"demo":True})
        if method == "POST" and path == "/lab/api/riders/approve":
            if role != "ops":return self.error(403, "operator_role_required")
            data = self.body()
            sub, approved = data.get("sub"), data.get("approved")
            if not isinstance(sub,str) or type(approved) is not bool:
                return self.error(400,"invalid_rider")
            with connect(self.server.lab_db) as db:
                cur = db.execute("""UPDATE p3_lab_rider_status
                     SET approved=?,on_duty=CASE WHEN ?=0 THEN 0 ELSE on_duty END
                     WHERE subject=?""",(int(approved),int(approved),sub))
                if cur.rowcount!=1:return self.error(404,"unknown_rider")
                return self.json({"ok":True,"demo":True})
        if method == "POST" and path == "/lab/api/rider/duty":
            if role != "rider":return self.error(403, "rider_role_required")
            data=self.body()
            if type(data.get("on_duty")) is not bool:return self.error(400,"invalid_duty")
            with connect(self.server.lab_db) as db:
                db.execute("""UPDATE p3_lab_rider_status SET on_duty=?
                    WHERE subject=? AND approved=1""",(int(data["on_duty"]),p["sub"]))
            return self.json({"ok":True})
        match = re.fullmatch(r"/lab/api/order/(go_[a-f0-9]{24})/(transition|simulate-paid|simulate-refund|checkout)",path)
        if match and method == "POST":
            order_id, action = match.groups()
            with connect(self.server.lab_db) as db:
                if action == "transition":
                    data=self.body()
                    approved = [r["subject"] for r in db.execute(
                        "SELECT subject FROM p3_lab_rider_status WHERE approved=1 AND on_duty=1")]
                    result=act(db,p,order_id,data.get("event"),data.get("version"),
                               approved_riders=tuple(approved))
                    return self.json({"order":result,"demo":True})
                if action == "checkout":
                    if role != "customer":return self.error(403,"customer_role_required")
                    if os.environ.get("GARAK_LAB_ENABLE_STRIPE_TEST")!="1":
                        return self.error(409,"test_stripe_disabled")
                    key=os.environ.get("GARAK_LAB_STRIPE_TEST_KEY","")
                    base=os.environ.get("GARAK_LAB_PUBLIC_HTTPS_ORIGIN","")
                    if not base.startswith("https://"):
                        return self.error(503,"return_url_not_configured")
                    result=attach_test_checkout(db,p,order_id,api_key=key,
                        success_url=base+"/order/success",
                        cancel_url=base+"/order/cancel")
                    return self.json(result)
                if role != "ops":return self.error(403,"operator_role_required")
                row=db.execute("SELECT * FROM p2_sandbox_orders WHERE id=?",(order_id,)).fetchone()
                if row is None:return self.error(404,"order_not_found")
                if action == "simulate-paid":
                    if row["state"]!="payment_pending":
                        return self.error(409,"order_not_pending")
                    if row["checkout_session_id"] is None:
                        mock_id="cs_test_lab_"+secrets.token_hex(8)
                        attach_test_checkout(db,{"role":"customer","sub":row["customer_id"]},order_id,
                             api_key="sk_test_offline_only",
                             success_url="https://example.invalid/ok",
                             cancel_url="https://example.invalid/cancel",
                             create_session=lambda _:{
                                "id":mock_id,"livemode":False,
                                "url":"https://checkout.stripe.com/c/pay/offline-only"})
                        row=db.execute("SELECT * FROM p2_sandbox_orders WHERE id=?",(order_id,)).fetchone()
                    secret="whsec_"+self.server.lab_signing_secret
                    event={"id":"evt_lab_"+secrets.token_hex(12),"livemode":False,
                       "type":"checkout.session.completed","data":{"object":{
                         "id":row["checkout_session_id"],"mode":"payment",
                         "livemode":False,"status":"complete","payment_status":"paid",
                         "currency":"krw","amount_total":row["total_krw"],
                         "client_reference_id":row["customer_id"],
                         "metadata":{"order_id":order_id,"merchant_id":row["merchant_id"]}}}}
                    payload=json.dumps(event,separators=(",",":")).encode()
                    stamp=int(time.time())
                    sig=hmac.new(secret.encode(),str(stamp).encode()+b"."+payload,
                                  hashlib.sha256).hexdigest()
                    result=paid_webhook(db,payload,f"t={stamp},v1={sig}",signing_secret=secret)
                    return self.json({"result":result,"synthetic_event":True})
                if action == "simulate-refund":
                    if row["state"] != "refund_pending":
                        return self.error(409,"refund_not_pending")
                    outcome=domain_transition(
                        DeliveryOrder(order_id=order_id,merchant_id=row["merchant_id"],
                                      state=row["state"],rider_id=row["rider_id"],
                                      version=row["version"]),
                        "refund_verified","payment_service","synthetic_provider",
                        row["version"],verified_provider_event=True)
                    db.execute("BEGIN IMMEDIATE")
                    try:
                        changed=db.execute("""UPDATE p2_sandbox_orders SET state=?,version=?
                          WHERE id=? AND version=?""",
                          (outcome.order.state,outcome.order.version,order_id,row["version"]))
                        if changed.rowcount!=1:raise SandboxError("stale refund transition")
                        for label in outcome.notifications:_notify(db,row,label)
                        db.commit()
                    except Exception:
                        db.rollback()
                        raise
                    return self.json({"state":"refunded","synthetic_refund":True})
        return self.error(404, "unknown_lab_route")

    def approved_rider(self, db, principal):
        row=db.execute("""SELECT approved,on_duty FROM p3_lab_rider_status
                           WHERE subject=?""",(principal["sub"],)).fetchone()
        return bool(row and row["approved"] and row["on_duty"])

    def do_GET(self):
        try:
            self.dispatch("GET")
        except (SandboxError, ValueError, TypeError, sqlite3.Error) as exc:
            self.error(400, str(exc))

    def do_POST(self):
        try:
            self.dispatch("POST")
        except (SandboxError, ValueError, TypeError, sqlite3.Error, json.JSONDecodeError) as exc:
            self.error(400, str(exc))


def main():
    parser=argparse.ArgumentParser(description="Synthetic local order integration lab (never production)")
    parser.add_argument("--port",type=int,default=8118)
    parser.add_argument("--db",type=str,default=str(HERE/"runtime"/"order-lab.sqlite3"))
    args=parser.parse_args()
    path=Path(args.db).resolve()
    if not path.is_relative_to((HERE/"runtime").resolve()):
        raise RuntimeError("local lab data MUST reside under runtime/")
    if os.environ.get("VERCEL") or os.environ.get("GARAK_ORDER_LIVE")=="1":
        raise RuntimeError("never launch lab in a live deployment")
    accounts={k:secrets.token_urlsafe(20) for k in ("customer","merchant","rider","ops")}
    init_lab(path,accounts)
    server=LabServer(("127.0.0.1",args.port),path)
    server.lab_signing_secret=secrets.token_hex(24)
    print("LOCAL/SYNTHETIC ONLY http://127.0.0.1:%d/" % args.port)
    print("One-time local login credentials (do not share):")
    for k,v in accounts.items():print(k,v)
    try:server.serve_forever()
    finally:server.server_close()


if __name__=="__main__":
    main()
