"""Stripe TEST-only V2 gateway: signed webhook, price matching, test key and idempotency."""
import hashlib
import hmac
import json
import os
import time
import unittest
from unittest.mock import patch
from admin_core.order_p2_sandbox import SandboxError
from admin_core.order_v2_pg_checkout import (
    validate_paid_session,create_test_checkout,accept_test_webhook,
    reserve_authenticated_cart,
)

ID="11111111-1111-4111-8111-111111111111"
MID="22222222-2222-4222-8222-222222222222"
ORDER={"id":ID,"merchant_id":MID,"customer_auth_sub":"test_customer_1",
       "total_krw":27000,"state":"payment_pending","version":0}
ATTEMPT={"id":"attempt-1","order_id":ID,"provider_checkout_id":"cs_test_order_1",
         "amount_krw":27000,"currency":"KRW","livemode":False,"state":"pending"}

def event(**kw):
    session={"id":"cs_test_order_1","livemode":False,"mode":"payment",
       "status":"complete","payment_status":"paid","currency":"krw","amount_total":27000,
       "client_reference_id":"test_customer_1",
       "metadata":{"order_id":ID,"merchant_id":MID}}
    session.update({k:v for k,v in kw.items() if k not in {"event_livemode","event_type"}})
    return {"id":"evt_v2_1","livemode":kw.get("event_livemode",False),
            "type":kw.get("event_type","checkout.session.completed"),
            "data":{"object":session}}

class Cursor:
    def __init__(self,rows=()):self.rows=rows
    def fetchone(self):return self.rows[0] if self.rows else None
    def fetchall(self):return list(self.rows)

class FakeDB:
    def __init__(self):
        self.order=dict(ORDER);self.attempt=None;self.event_ids=set();self.outbox=[]
        self.hold_state="held"
    def execute(self,sql,params=()):
        if "reserve_trusted_order" in sql:
            return Cursor([{"confirmed_order_id":ID,"total_due_krw":27000,
                            "idempotent_reuse":False}])
        if sql.lstrip().startswith("SELECT") and "FROM garak_order_v2.orders" in sql:
            return Cursor([dict(self.order)])
        if sql.lstrip().startswith("SELECT") and "FROM garak_order_v2.payment_attempts" in sql:
            return Cursor([dict(self.attempt)]) if self.attempt else Cursor()
        if "INSERT INTO garak_order_v2.payment_attempts" in sql:
            if self.attempt:return Cursor()
            self.attempt={**ATTEMPT,"provider_checkout_id":params[1],
                          "checkout_url":params[2]};return Cursor([{"provider_checkout_id":params[1]}])
        if "SELECT event_id FROM" in sql:return Cursor([{"event_id":"dup"}] if params[0] in self.event_ids else [])
        if "INSERT INTO garak_order_v2.payment_events" in sql:
            self.event_ids.add(params[0]);return Cursor()
        if "UPDATE garak_order_v2.orders" in sql:
            self.order.update(state="paid",version=self.order["version"]+1);return Cursor()
        if "UPDATE garak_order_v2.payment_attempts" in sql:
            self.attempt["state"]="paid";return Cursor()
        if "UPDATE garak_order_v2.inventory_holds" in sql:
            self.hold_state="consumed";return Cursor()
        if "INSERT INTO garak_order_v2.notification_outbox" in sql:
            self.outbox.append(params);return Cursor()
        raise AssertionError("unexpected SQL: "+sql)

class V2StripeTests(unittest.TestCase):
    def test_accepts_only_correct_paid_session(self):
        self.assertEqual(validate_paid_session(event(),ORDER,ATTEMPT)["amount_total"],27000)
    def test_rejects_unpaid_wrong_amount_currency_merchant_or_live(self):
        for kw in ({"payment_status":"unpaid"},{"amount_total":26999},
                   {"currency":"usd"},{"event_livemode":True},
                   {"livemode":True},{"client_reference_id":"other"},
                   {"metadata":{"order_id":ID,"merchant_id":"wrong"}},
                   {"id":"cs_test_forged"},{"event_type":"charge.refunded"}):
            with self.subTest(kw=kw),self.assertRaises(SandboxError):
                validate_paid_session(event(**kw),ORDER,ATTEMPT)
    def test_test_key_only_and_approved_return_host(self):
        with patch.dict(os.environ,{"GARAK_ORDER_V2_CHECKOUT_ORIGIN":"https://preview.example.invalid"}):
            db=FakeDB()
            for key in ("sk_live_dont_use","rk_test_not_secret",""):
                with self.assertRaises(SandboxError):
                    create_test_checkout(db,verified_customer_sub=ORDER["customer_auth_sub"],order_id=ID,
                        key=key,success_url="https://preview.example.invalid/success",
                        cancel_url="https://preview.example.invalid/cancel",create_session=lambda _: {})
            with self.assertRaises(SandboxError):
                create_test_checkout(db,verified_customer_sub=ORDER["customer_auth_sub"],order_id=ID,
                  key="sk_test_fake",success_url="https://attacker.invalid/success",
                  cancel_url="https://preview.example.invalid/cancel",create_session=lambda _: {})
    def test_session_uses_server_order_krw_without_cents_multiplier(self):
        captured={}
        with patch.dict(os.environ,{"GARAK_ORDER_V2_CHECKOUT_ORIGIN":"https://preview.example.invalid"}):
            db=FakeDB()
            def mock(payload):
                captured.update(payload)
                return {"livemode":False,"id":"cs_test_order_1",
                        "url":"https://checkout.stripe.com/c/pay/qa"}
            kwargs=dict(verified_customer_sub=ORDER["customer_auth_sub"],order_id=ID,
                key="sk_test_not_real",success_url="https://preview.example.invalid/success",
                cancel_url="https://preview.example.invalid/cancel",create_session=mock)
            a=create_test_checkout(db,**kwargs);b=create_test_checkout(db,**kwargs)
            self.assertEqual(captured["line_items[0][price_data][unit_amount]"],"27000")
            self.assertEqual(captured["line_items[0][price_data][currency]"],"krw")
            self.assertFalse(a["existing"]);self.assertTrue(b["existing"])
    def test_signature_paid_then_duplicate_and_outbox_once(self):
        db=FakeDB();db.attempt={**ATTEMPT}
        e=event();payload=json.dumps(e,separators=(",",":")).encode();secret="whsec_v2_only"
        stamp=int(time.time());sig=hmac.new(secret.encode(),str(stamp).encode()+b"."+payload,hashlib.sha256).hexdigest()
        header=f"t={stamp},v1={sig}"
        with self.assertRaises(SandboxError):
            accept_test_webhook(db,payload,header[:-1]+"0",webhook_test_secret=secret)
        self.assertEqual(db.order["state"],"payment_pending")
        self.assertTrue(accept_test_webhook(db,payload,header,webhook_test_secret=secret)["processed"])
        self.assertEqual(db.hold_state,"consumed")
        self.assertEqual(len(db.outbox),1)
        self.assertTrue(accept_test_webhook(db,payload,header,webhook_test_secret=secret)["duplicate"])
        self.assertEqual(len(db.outbox),1)
    def test_reservation_requires_encrypted_address(self):
        db=FakeDB()
        with self.assertRaises(SandboxError):
            reserve_authenticated_cart(db,verified_customer_sub="user1",merchant_id=MID,
                delivery_zone_id=MID,items=[],idempotency_key="key_1234567890",
                encrypted_delivery_address="not encrypted")
        v=reserve_authenticated_cart(db,verified_customer_sub="user1",merchant_id=MID,
             delivery_zone_id=MID,items=[{"product_id":MID,"qty":2}],
             idempotency_key="key_1234567890",encrypted_delivery_address=b"0"*64)
        self.assertEqual(v["total_krw"],27000)

if __name__=="__main__":unittest.main()
