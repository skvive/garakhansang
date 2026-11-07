"""Isolated order/Stripe sandbox for Garak Hansang Order (NOT a production API).

Reuses admin_core.delivery_flow transitions. Caller must supply an authenticated,
verified principal and a server-generated quote from mobile_commerce.quote_cart.
No live Stripe key, charge, refund, delivery dispatch or FCM is executed.
Do NOT connect this SQLite fixture to a production/Neon database.
"""
from __future__ import annotations

import hashlib
import hmac
import json
import re
import secrets
import sqlite3
import time
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from .delivery_flow import DeliveryOrder, OrderFlowError, transition as domain_transition

KEY = re.compile(r"^[a-zA-Z0-9_-]{12,128}$")
ID = re.compile(r"^[a-zA-Z0-9_-]{1,128}$")
VALID_ROLES = frozenset({"customer", "merchant", "rider", "ops", "payment_service"})
EVENT_PAYMENT = frozenset({"checkout.session.completed", "checkout.session.async_payment_succeeded"})


class SandboxError(ValueError):
    """A payment, authorization, or state integrity condition failed."""


def _principal(p, role=None):
    if not isinstance(p, dict) or p.get("role") not in VALID_ROLES:
        raise SandboxError("verified principal required")
    if not isinstance(p.get("sub"), str) or not ID.fullmatch(p["sub"]):
        raise SandboxError("verified principal subject required")
    if role and p["role"] != role:
        raise SandboxError("role not permitted")
    return p


def setup(con: sqlite3.Connection):
    """Opt-in schema for a dedicated, disposable SQLite testing database only."""
    con.executescript("""
    PRAGMA foreign_keys=ON;
    CREATE TABLE IF NOT EXISTS p2_sandbox_orders(
      id TEXT PRIMARY KEY, customer_id TEXT NOT NULL, merchant_id TEXT NOT NULL,
      idempotency_key TEXT NOT NULL, subtotal_krw INTEGER NOT NULL CHECK(subtotal_krw>0),
      delivery_fee_krw INTEGER NOT NULL DEFAULT 0, total_krw INTEGER NOT NULL CHECK(total_krw>0),
      currency TEXT NOT NULL DEFAULT 'krw' CHECK(currency='krw'),
      state TEXT NOT NULL DEFAULT 'payment_pending', rider_id TEXT, version INTEGER NOT NULL DEFAULT 0,
      checkout_session_id TEXT UNIQUE, created_at INTEGER NOT NULL,
      UNIQUE(customer_id,idempotency_key)
    );
    CREATE TABLE IF NOT EXISTS p2_sandbox_events(
      provider_event_id TEXT PRIMARY KEY, order_id TEXT NOT NULL REFERENCES p2_sandbox_orders(id),
      event_type TEXT NOT NULL, created_at INTEGER NOT NULL
    );
    CREATE TABLE IF NOT EXISTS p2_sandbox_outbox(
      id INTEGER PRIMARY KEY, order_id TEXT NOT NULL REFERENCES p2_sandbox_orders(id),
      recipient_role TEXT NOT NULL, recipient_id TEXT NOT NULL,
      event TEXT NOT NULL, delivered INTEGER NOT NULL DEFAULT 0,
      created_at INTEGER NOT NULL
    );
    CREATE INDEX IF NOT EXISTS idx_p2_outbox_recipient
      ON p2_sandbox_outbox(recipient_role,recipient_id,delivered);
    """)


def draft(con, principal, trusted_quote, idempotency_key, *, delivery_fee_krw=0):
    """Create *simulated* order from a trusted quote, without reserving any stock."""
    p = _principal(principal, "customer")
    if not isinstance(idempotency_key, str) or not KEY.fullmatch(idempotency_key):
        raise SandboxError("invalid idempotency key")
    if not isinstance(trusted_quote, dict) or trusted_quote.get("source") != "server_catalog":
        raise SandboxError("only a server catalog quote is accepted")
    subtotal = trusted_quote.get("subtotal_krw")
    merchant = trusted_quote.get("merchant_id")
    if type(subtotal) is not int or not 1 <= subtotal <= 100_000_000:
        raise SandboxError("invalid trusted subtotal")
    if type(delivery_fee_krw) is not int or not 0 <= delivery_fee_krw <= 100_000:
        raise SandboxError("invalid demo delivery fee")
    if merchant is None or not ID.fullmatch(str(merchant)):
        raise SandboxError("approved merchant required")
    if type(trusted_quote.get("checkout_enabled")) is not bool or trusted_quote["checkout_enabled"]:
        raise SandboxError("sandbox expects checkout-disabled quote")
    oid = "go_" + secrets.token_hex(12)
    try:
        con.execute("BEGIN IMMEDIATE")
        cur = con.execute("""INSERT INTO p2_sandbox_orders
          (id,customer_id,merchant_id,idempotency_key,subtotal_krw,delivery_fee_krw,total_krw,created_at)
          VALUES(?,?,?,?,?,?,?,?) ON CONFLICT(customer_id,idempotency_key) DO NOTHING""",
          (oid,p["sub"],str(merchant),idempotency_key,subtotal,delivery_fee_krw,
           subtotal+delivery_fee_krw,int(time.time())))
        if cur.rowcount == 0:
            row = con.execute("""SELECT * FROM p2_sandbox_orders
              WHERE customer_id=? AND idempotency_key=?""",(p["sub"],idempotency_key)).fetchone()
            if row["subtotal_krw"] != subtotal or row["merchant_id"] != str(merchant) or row["delivery_fee_krw"] != delivery_fee_krw:
                raise SandboxError("idempotency key reused with different cart")
            oid = row["id"]
        con.commit()
    except Exception:
        con.rollback()
        raise
    return get_order(con,{"role":"customer","sub":p["sub"]},oid)


def get_order(con, principal, order_id):
    p = _principal(principal)
    row = con.execute("SELECT * FROM p2_sandbox_orders WHERE id=?",(order_id,)).fetchone()
    if row is None:
        raise SandboxError("order not found")
    allowed = (p["role"] == "ops"
               or p["role"] == "customer" and p["sub"] == row["customer_id"]
               or p["role"] == "merchant" and p["sub"] == row["merchant_id"]
               or p["role"] == "rider" and p["sub"] == row["rider_id"])
    if not allowed:
        raise SandboxError("order not found")
    return {k:row[k] for k in ("id","merchant_id","subtotal_krw","delivery_fee_krw",
            "total_krw","currency","state","rider_id","version")}


def attach_test_checkout(con, principal, order_id, *, api_key, success_url, cancel_url, create_session=None):
    """Prepare test Stripe Checkout. Never creates a live mode session.

    Inject create_session for tests. Production identity/RLS is intentionally
    NOT implemented and this adapter MUST NOT be exposed as a public endpoint.
    """
    p = _principal(principal, "customer")
    if not isinstance(api_key,str) or not api_key.startswith("sk_test_"):
        raise SandboxError("only Stripe test secret keys are accepted")
    for url in (success_url,cancel_url):
        if not isinstance(url,str) or not url.startswith("https://"):
            raise SandboxError("only HTTPS return URLs are allowed")
    row = con.execute("SELECT * FROM p2_sandbox_orders WHERE id=?",(order_id,)).fetchone()
    if row is None or row["customer_id"] != p["sub"]:
        raise SandboxError("order not found")
    if row["state"] != "payment_pending":
        raise SandboxError("order not payable")
    if row["checkout_session_id"]:
        raise SandboxError("checkout already prepared")
    params = {
      "mode":"payment","client_reference_id":row["customer_id"],
      "success_url":success_url,"cancel_url":cancel_url,
      "metadata[order_id]":row["id"],"metadata[merchant_id]":row["merchant_id"],
      "line_items[0][quantity]":"1",
      "line_items[0][price_data][currency]":"krw",
      "line_items[0][price_data][unit_amount]":str(row["total_krw"]),
      "line_items[0][price_data][product_data][name]":"Garak Hansang sandbox order"
    }
    if create_session is None:
        def create_session(body):
            req = Request("https://api.stripe.com/v1/checkout/sessions",
                data=urlencode(body).encode("utf-8"),
                headers={"Authorization":"Bearer "+api_key,
                         "Content-Type":"application/x-www-form-urlencoded",
                         "Idempotency-Key":"garak-test-"+order_id},method="POST")
            with urlopen(req, timeout=10) as response:
                return json.loads(response.read(65536))
    session = create_session(params)
    if not isinstance(session,dict) or session.get("livemode") is not False:
        raise SandboxError("refuse unverified or live Stripe session")
    sid, url = session.get("id"),session.get("url")
    if not isinstance(sid,str) or not sid.startswith("cs_test_"):
        raise SandboxError("Stripe test session id required")
    if not isinstance(url,str) or not url.startswith("https://checkout.stripe.com/"):
        raise SandboxError("Stripe Checkout HTTPS URL required")
    try:
        con.execute("BEGIN IMMEDIATE")
        updated = con.execute("""UPDATE p2_sandbox_orders SET checkout_session_id=?
           WHERE id=? AND customer_id=? AND state='payment_pending'
             AND checkout_session_id IS NULL""",(sid,order_id,p["sub"]))
        if updated.rowcount != 1:
            raise SandboxError("checkout already prepared")
        con.commit()
    except Exception:
        con.rollback()
        raise
    return {"checkout_url":url,"session_id":sid,"sandbox_only":True}


def verify_stripe_test_signature(payload: bytes, signature: str, secret: str, *, now=None):
    if not isinstance(secret,str) or not secret.startswith("whsec_"):
        raise SandboxError("Stripe test webhook signing secret required")
    if not isinstance(payload,bytes) or len(payload)>65536:
        raise SandboxError("invalid webhook payload")
    fields = [x.strip().split("=",1) for x in (signature or "").split(",") if "=" in x]
    timestamps = [v for k,v in fields if k=="t"]
    signatures = [v for k,v in fields if k=="v1"]
    if len(timestamps)!=1 or not timestamps[0].isdigit() or not signatures:
        raise SandboxError("invalid Stripe-Signature")
    stamp=int(timestamps[0]);now=int(time.time()) if now is None else now
    if abs(now-stamp)>300:
        raise SandboxError("stale Stripe webhook")
    expected=hmac.new(secret.encode(),str(stamp).encode()+b"."+payload,hashlib.sha256).hexdigest()
    if not any(hmac.compare_digest(v,expected) for v in signatures):
        raise SandboxError("invalid Stripe webhook signature")
    try:
        event=json.loads(payload)
    except (UnicodeError,ValueError) as exc:
        raise SandboxError("malformed Stripe event") from exc
    if not isinstance(event,dict) or event.get("livemode") is not False:
        raise SandboxError("live events forbidden")
    return event


def _notify(con, order, label):
    role,_,event=label.partition(":")
    if role not in {"customer","merchant","rider_pool","ops"} or not event:
        raise SandboxError("unknown notification route")
    dest={"customer":order["customer_id"],"merchant":order["merchant_id"],
          "ops":"ops_all","rider_pool":"eligible_rider_pool"}[role]
    con.execute("""INSERT INTO p2_sandbox_outbox
      (order_id,recipient_role,recipient_id,event,created_at)
      VALUES(?,?,?,?,?)""",(order["id"],role,dest,event,int(time.time())))


def paid_webhook(con, raw_payload, stripe_signature, *, signing_secret, now=None):
    """Only trusted signed test webhook can mark a sandbox order paid."""
    event=verify_stripe_test_signature(raw_payload,stripe_signature,signing_secret,now=now)
    if event.get("type") not in EVENT_PAYMENT:
        return {"processed":False,"reason":"not a payment completion"}
    sid=event.get("data",{}).get("object",{})
    if not isinstance(sid,dict):
        raise SandboxError("missing Checkout Session")
    eid=event.get("id")
    if not isinstance(eid,str) or not eid.startswith("evt_"):
        raise SandboxError("event id required")
    ref=sid.get("metadata") or {}
    oid=ref.get("order_id")
    if not isinstance(oid,str):
        raise SandboxError("order metadata missing")
    try:
        con.execute("BEGIN IMMEDIATE")
        row=con.execute("SELECT * FROM p2_sandbox_orders WHERE id=?",(oid,)).fetchone()
        if row is None:
            raise SandboxError("unknown order")
        if (sid.get("livemode") is not False or sid.get("mode") != "payment"
            or sid.get("payment_status") != "paid"
            or sid.get("status") != "complete"
            or sid.get("currency") != "krw"
            or type(sid.get("amount_total")) is not int
            or sid["amount_total"] != row["total_krw"]
            or sid.get("id") != row["checkout_session_id"]
            or sid.get("client_reference_id") != row["customer_id"]
            or str(ref.get("merchant_id")) != row["merchant_id"]):
            raise SandboxError("payment/session/order integrity mismatch")
        if con.execute("SELECT 1 FROM p2_sandbox_events WHERE provider_event_id=?",(eid,)).fetchone():
            con.commit()
            return {"processed":False,"duplicate":True,"state":row["state"]}
        if row["state"]!="payment_pending":
            # Repeated legitimate success messages can arrive after fulfillment starts.
            # Record the provider event but never re-notify or reset the order.
            if row["state"] in {"paid","merchant_accepted","preparing","ready_for_pickup",
                "dispatch_requested","rider_assigned","picked_up","in_transit","delivered",
                "refund_pending","refunded"}:
                con.execute("""INSERT INTO p2_sandbox_events
                  (provider_event_id,order_id,event_type,created_at) VALUES(?,?,?,?)""",
                  (eid,oid,event["type"],int(time.time())))
                con.commit()
                return {"processed":False,"duplicate_payment":True,"state":row["state"]}
            raise SandboxError("payment completion in invalid state")
        outcome=domain_transition(DeliveryOrder(order_id=oid,merchant_id=row["merchant_id"],
                                  state=row["state"],rider_id=row["rider_id"],version=row["version"]),
                                  "payment_verified","payment_service","stripe",row["version"],
                                  verified_provider_event=True)
        updated=con.execute("""UPDATE p2_sandbox_orders SET state=?,version=?
             WHERE id=? AND version=?""",(outcome.order.state,outcome.order.version,oid,row["version"]))
        if updated.rowcount!=1:raise SandboxError("concurrent order update")
        con.execute("""INSERT INTO p2_sandbox_events(provider_event_id,order_id,event_type,created_at)
                        VALUES(?,?,?,?)""",(eid,oid,event["type"],int(time.time())))
        for label in outcome.notifications:_notify(con,row,label)
        con.commit()
        return {"processed":True,"state":outcome.order.state}
    except Exception:
        con.rollback()
        raise


def act(con, principal, order_id, event, expected_version, *, approved_riders=()):
    """Role-scoped simulated transition. Calling API must validate auth first."""
    p=_principal(principal)
    if p["role"]=="payment_service":
        raise SandboxError("provider state changes require signed webhook")
    try:
        con.execute("BEGIN IMMEDIATE")
        row=con.execute("SELECT * FROM p2_sandbox_orders WHERE id=?",(order_id,)).fetchone()
        if row is None:raise SandboxError("order not found")
        if p["role"]=="customer" and p["sub"]!=row["customer_id"]:
            raise SandboxError("customer does not own order")
        if p["role"]=="merchant" and p["sub"]!=row["merchant_id"]:
            raise SandboxError("merchant does not own order")
        if p["role"]=="rider" and event=="rider_accept" and p["sub"] not in approved_riders:
            raise SandboxError("rider is not approved for this dispatch")
        if p["role"]=="rider" and event!="rider_accept" and row["rider_id"]!=p["sub"]:
            raise SandboxError("rider is not assigned")
        try:
            outcome=domain_transition(DeliveryOrder(order_id=order_id,merchant_id=row["merchant_id"],
                 state=row["state"],rider_id=row["rider_id"],version=row["version"]),event,p["role"],
                 p["sub"],expected_version)
        except OrderFlowError as exc:
            raise SandboxError(str(exc)) from exc
        updated=con.execute("""UPDATE p2_sandbox_orders SET state=?,rider_id=?,version=?
             WHERE id=? AND version=?""",(outcome.order.state,outcome.order.rider_id,
                                        outcome.order.version,order_id,expected_version))
        if updated.rowcount != 1:raise SandboxError("concurrent update")
        for label in outcome.notifications:_notify(con,row,label)
        con.commit()
        return {"state":outcome.order.state,"version":outcome.order.version}
    except Exception:
        con.rollback()
        raise


def inbox(con, principal):
    p=_principal(principal)
    if p["role"]=="payment_service":raise SandboxError("no operator inbox")
    role=p["role"];dest=p["sub"]
    if role=="ops":dest="ops_all"
    rows=con.execute("""SELECT order_id,event,created_at FROM p2_sandbox_outbox
           WHERE recipient_role=? AND recipient_id=? ORDER BY id DESC LIMIT 100""",(role,dest)).fetchall()
    return [dict(row) for row in rows]


def dashboard(con, principal):
    """Only own merchant/customer/assigned rider orders. Ops sees all sandbox orders."""
    p=_principal(principal)
    if p["role"]=="ops":
        rows=con.execute("SELECT id FROM p2_sandbox_orders ORDER BY created_at DESC LIMIT 100").fetchall()
    elif p["role"]=="customer":
        rows=con.execute("SELECT id FROM p2_sandbox_orders WHERE customer_id=? ORDER BY created_at DESC LIMIT 100",(p["sub"],)).fetchall()
    elif p["role"]=="merchant":
        rows=con.execute("SELECT id FROM p2_sandbox_orders WHERE merchant_id=? ORDER BY created_at DESC LIMIT 100",(p["sub"],)).fetchall()
    elif p["role"]=="rider":
        rows=con.execute("SELECT id FROM p2_sandbox_orders WHERE rider_id=? ORDER BY created_at DESC LIMIT 100",(p["sub"],)).fetchall()
    else:
        raise SandboxError("role not permitted")
    return [get_order(con,p,row["id"]) for row in rows]
