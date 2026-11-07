"""Garak Order V2 staging-only Stripe Checkout. Not a public HTTP endpoint.

The calling BFF MUST verify Neon Auth and use an isolated staging-only
database connection (psycopg 3 dict_row, parameter marker %s).
No live Stripe keys, live charges or refund calls.
Reuses the strict P2 Stripe webhook signature verifier.
"""
from __future__ import annotations
import json
import os
from urllib.parse import urlsplit, urlencode
from urllib.request import Request, urlopen
from .order_p2_sandbox import SandboxError, verify_stripe_test_signature

EVENTS = {"checkout.session.completed", "checkout.session.async_payment_succeeded"}


def _trusted_test_inputs(key, success_url, cancel_url):
    if not isinstance(key, str) or not key.startswith("sk_test_"):
        raise SandboxError("Stripe TEST key required; live keys prohibited")
    origin = urlsplit(os.environ.get("GARAK_ORDER_V2_CHECKOUT_ORIGIN", ""))
    if origin.scheme != "https" or not origin.netloc:
        raise SandboxError("Approved staging callback origin is not configured")
    for url in (success_url, cancel_url):
        p = urlsplit(url)
        if (p.scheme != "https" or p.netloc != origin.netloc
                or p.username or p.password or p.fragment):
            raise SandboxError("Unapproved checkout return URL")


def validate_paid_session(event, order, attempt):
    """Compare signed test Stripe session with the immutable database order."""
    if not isinstance(event, dict) or event.get("livemode") is not False or event.get("type") not in EVENTS:
        raise SandboxError("Live or unsupported Stripe event")
    session = event.get("data", {}).get("object")
    if not isinstance(session, dict):
        raise SandboxError("Missing checkout session")
    metadata = session.get("metadata") or {}
    if (session.get("livemode") is not False
            or session.get("mode") != "payment"
            or session.get("status") != "complete"
            or session.get("payment_status") != "paid"
            or session.get("currency") != "krw"
            or type(session.get("amount_total")) is not int
            or session["amount_total"] != order["total_krw"]
            or attempt["amount_krw"] != order["total_krw"]
            or attempt["currency"] != "KRW"
            or attempt["livemode"] is not False
            or session.get("id") != attempt["provider_checkout_id"]
            or session.get("client_reference_id") != order["customer_auth_sub"]
            or metadata.get("order_id") != str(order["id"])
            or metadata.get("merchant_id") != str(order["merchant_id"])):
        raise SandboxError("Payment/account/order/amount verification failed")
    if not isinstance(event.get("id"), str) or not event["id"].startswith("evt_"):
        raise SandboxError("Stripe event ID missing")
    return session


def reserve_authenticated_cart(con, *, verified_customer_sub, merchant_id, delivery_zone_id,
                               items, idempotency_key, encrypted_delivery_address):
    """Only the server's verified Neon Auth identity may be passed as customer_sub."""
    if not isinstance(encrypted_delivery_address, bytes):
        raise SandboxError("Encrypt the delivery address in the BFF before DB insert")
    rows = con.execute("SELECT * FROM garak_order_v2.reserve_trusted_order(%s,%s,%s,%s,%s,%s)",
        (verified_customer_sub, merchant_id, delivery_zone_id,
         json.dumps(items, separators=(",", ":")), idempotency_key,
         encrypted_delivery_address)).fetchall()
    if len(rows) != 1:
        raise SandboxError("Order reservation failed")
    r = rows[0]
    return {"order_id": str(r["confirmed_order_id"]), "total_krw": r["total_due_krw"],
            "idempotent_reuse": r["idempotent_reuse"], "currency": "KRW",
            "state": "payment_pending"}


def create_test_checkout(con, *, verified_customer_sub, order_id, key, success_url,
                         cancel_url, create_session=None):
    _trusted_test_inputs(key, success_url, cancel_url)
    order = con.execute("""SELECT id,merchant_id,customer_auth_sub,total_krw,state
        FROM garak_order_v2.orders WHERE id=%s AND customer_auth_sub=%s""",
        (order_id, verified_customer_sub)).fetchone()
    if not order:
        raise SandboxError("Order not found or not owned")
    if order["state"] != "payment_pending":
        raise SandboxError("Order not payable")
    prev = con.execute("""SELECT provider_checkout_id,checkout_url
        FROM garak_order_v2.payment_attempts WHERE order_id=%s AND provider='stripe'
        ORDER BY created_at LIMIT 1""", (order_id,)).fetchone()
    if prev:
        if not str(prev["checkout_url"]).startswith("https://checkout.stripe.com/"):
            raise SandboxError("Existing Stripe session URL invalid")
        return {"checkout_url": prev["checkout_url"], "session_id": prev["provider_checkout_id"],
                "sandbox_only": True, "existing": True}
    params = {
        "mode": "payment", "client_reference_id": order["customer_auth_sub"],
        "success_url": success_url, "cancel_url": cancel_url,
        "metadata[order_id]": str(order["id"]),
        "metadata[merchant_id]": str(order["merchant_id"]),
        "line_items[0][quantity]": "1",
        "line_items[0][price_data][currency]": "krw",
        "line_items[0][price_data][unit_amount]": str(order["total_krw"]),
        "line_items[0][price_data][product_data][name]": "가락한상 테스트 주문",
    }
    if create_session is None:
        def create_session(data):
            req = Request("https://api.stripe.com/v1/checkout/sessions",
                data=urlencode(data).encode(), headers={
                   "Authorization": "Bearer "+key,
                   "Content-Type": "application/x-www-form-urlencoded",
                   "Idempotency-Key": "garak-test-order-"+order_id}, method="POST")
            with urlopen(req, timeout=12) as response:
                return json.loads(response.read(65536))
    session = create_session(params)
    if (not isinstance(session, dict) or session.get("livemode") is not False
            or not str(session.get("id", "")).startswith("cs_test_")
            or not str(session.get("url", "")).startswith("https://checkout.stripe.com/")):
        raise SandboxError("Stripe did not return a verified TEST Checkout URL")
    changed = con.execute("""INSERT INTO garak_order_v2.payment_attempts
        (order_id,provider,provider_checkout_id,checkout_url,amount_krw,currency,livemode)
        VALUES(%s,'stripe',%s,%s,%s,'KRW',false)
        ON CONFLICT(order_id) DO NOTHING RETURNING provider_checkout_id""",
        (order["id"],session["id"],session["url"],order["total_krw"])).fetchone()
    if not changed:
        raise SandboxError("Concurrent checkout session; reload and reuse existing")
    return {"checkout_url": session["url"], "session_id": session["id"],
            "sandbox_only": True, "existing": False}


def accept_test_webhook(con, raw, signature, *, webhook_test_secret):
    """Must run inside one DB transaction; the handler sends exact raw bytes."""
    event = verify_stripe_test_signature(raw, signature, webhook_test_secret)
    if event.get("type") not in EVENTS:
        return {"processed": False, "ignored": True}
    session = event.get("data", {}).get("object")
    if not isinstance(session, dict):
        raise SandboxError("Missing checkout session")
    attempt = con.execute("""SELECT id,order_id,provider_checkout_id,amount_krw,currency,
        livemode,state FROM garak_order_v2.payment_attempts
        WHERE provider='stripe' AND provider_checkout_id=%s FOR UPDATE""",
        (session.get("id"),)).fetchone()
    if not attempt:
        raise SandboxError("Unregistered checkout")
    order = con.execute("""SELECT id,merchant_id,customer_auth_sub,total_krw,state,version
        FROM garak_order_v2.orders WHERE id=%s FOR UPDATE""",
        (attempt["order_id"],)).fetchone()
    if not order:
        raise SandboxError("Order missing")
    validate_paid_session(event, order, attempt)
    duplicate = con.execute("SELECT event_id FROM garak_order_v2.payment_events WHERE event_id=%s",
                            (event["id"],)).fetchone()
    if duplicate:
        return {"processed": False, "duplicate": True, "state": order["state"]}
    con.execute("""INSERT INTO garak_order_v2.payment_events
        (event_id,order_id,provider,event_kind,signature_checked,amount_krw)
        VALUES(%s,%s,'stripe',%s,true,%s)""",
        (event["id"],order["id"],event["type"],order["total_krw"]))
    if order["state"] != "payment_pending":
        if order["state"] in {"paid","merchant_accepted","preparing","ready_for_pickup",
              "dispatch_requested","rider_assigned","picked_up","in_transit",
              "delivered","refund_pending","refunded"}:
            return {"processed": False, "duplicate_payment": True, "state": order["state"]}
        raise SandboxError("Invalid payment completion state")
    con.execute("""UPDATE garak_order_v2.orders SET state='paid',version=version+1,
        updated_at=now() WHERE id=%s AND state='payment_pending'""", (order["id"],))
    con.execute("UPDATE garak_order_v2.payment_attempts SET state='paid' WHERE id=%s",
                (attempt["id"],))
    con.execute("""UPDATE garak_order_v2.inventory_holds SET state='consumed'
                   WHERE order_id=%s AND state='held'""", (order["id"],))
    con.execute("""INSERT INTO garak_order_v2.notification_outbox
        (order_id,event,recipient_role,recipient_subject,order_version)
        VALUES(%s,'new_paid_order','merchant',%s,%s) ON CONFLICT DO NOTHING""",
        (order["id"],str(order["merchant_id"]),order["version"]+1))
    return {"processed": True, "state": "paid", "order_id": str(order["id"])}
