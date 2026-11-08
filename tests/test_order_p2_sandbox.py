"""Isolated P2 test-only integration checks (no Stripe network or real payments)."""
import hashlib
import hmac
import json
import sqlite3
import time
import unittest

from admin_core.order_p2_sandbox import (
    SandboxError, setup, draft, get_order, attach_test_checkout,
    paid_webhook, act, dashboard, inbox, verify_stripe_test_signature,
)

CUSTOMER={"role":"customer","sub":"customer_7"}
MERCHANT={"role":"merchant","sub":"17"}
OTHER_MERCHANT={"role":"merchant","sub":"18"}
RIDER={"role":"rider","sub":"rider_2"}
OTHER_RIDER={"role":"rider","sub":"rider_3"}
OPS={"role":"ops","sub":"operator_1"}
QUOTE={"source":"server_catalog","subtotal_krw":25000,
       "merchant_id":17,"checkout_enabled":False}
KEY="sk_test_synthetic_not_real"
SECRET="whsec_synthetic_test_only"


class SandboxCheckoutTests(unittest.TestCase):
    def setUp(self):
        self.con=sqlite3.connect(":memory:", isolation_level=None)
        self.con.row_factory=sqlite3.Row
        setup(self.con)

    def tearDown(self):
        self.con.close()

    def new_order(self, key="repeatable_order_key_01"):
        return draft(self.con,CUSTOMER,QUOTE,key,delivery_fee_krw=2000)

    def checkout(self, order):
        captured={}
        def fake_create(params):
            captured.update(params)
            return {"livemode":False,"id":"cs_test_synthetic_987",
                    "url":"https://checkout.stripe.com/c/pay/sandbox"}
        r=attach_test_checkout(self.con,CUSTOMER,order["id"],api_key=KEY,
            success_url="https://example.invalid/order/return",
            cancel_url="https://example.invalid/order/cancel",
            create_session=fake_create)
        return r,captured

    def event(self, order, *, eid="evt_one", status="paid", currency="krw", amount=27000, livemode=False,
              session_id="cs_test_synthetic_987", merchant_id="17"):
        return {"id":eid,"type":"checkout.session.completed","livemode":livemode,
                "data":{"object":{
                    "livemode":livemode,"id":session_id,"mode":"payment",
                    "status":"complete","payment_status":status,"currency":currency,
                    "amount_total":amount,"client_reference_id":"customer_7",
                    "metadata":{"order_id":order["id"],"merchant_id":merchant_id}
                }}}

    def signed(self, event, *, stamp=None, secret=SECRET):
        stamp=int(time.time()) if stamp is None else stamp
        raw=json.dumps(event,separators=(",",":"),ensure_ascii=False).encode()
        mac=hmac.new(secret.encode(),str(stamp).encode()+b"."+raw,hashlib.sha256).hexdigest()
        return raw,f"t={stamp},v1={mac}"

    def paid(self, order, **changes):
        payload,signature=self.signed(self.event(order,**changes))
        return paid_webhook(self.con,payload,signature,signing_secret=SECRET)

    def test_draft_is_server_priced_and_idempotent(self):
        a=self.new_order()
        b=self.new_order()
        self.assertEqual(a["id"],b["id"])
        self.assertEqual(a["total_krw"],27000)
        self.assertEqual(a["currency"],"krw")
        self.assertEqual(self.con.execute("SELECT count(*) FROM p2_sandbox_orders").fetchone()[0],1)

    def test_draft_rejects_reused_key_with_new_price(self):
        self.new_order()
        altered=dict(QUOTE,subtotal_krw=1)
        with self.assertRaises(SandboxError):
            draft(self.con,CUSTOMER,altered,"repeatable_order_key_01",delivery_fee_krw=2000)

    def test_draft_rejects_unverified_or_client_quote(self):
        for quote in ({"subtotal_krw":10,"merchant_id":17},dict(QUOTE,checkout_enabled=True),
                      dict(QUOTE,subtotal_krw=0),dict(QUOTE,subtotal_krw=True)):
            with self.assertRaises(SandboxError):
                draft(self.con,CUSTOMER,quote,"safe_sandbox_key_001")

    def test_checkout_rejects_live_and_non_https(self):
        a=self.new_order()
        for key in ("sk_live_any","rk_live_any",""):
            with self.assertRaises(SandboxError):
                attach_test_checkout(self.con,CUSTOMER,a["id"],api_key=key,
                    success_url="https://example.invalid/ok",
                    cancel_url="https://example.invalid/cancel",
                    create_session=lambda _: {})
        with self.assertRaises(SandboxError):
            attach_test_checkout(self.con,CUSTOMER,a["id"],api_key=KEY,
                success_url="http://example.invalid/ok",
                cancel_url="https://example.invalid/cancel",create_session=lambda _: {})

    def test_test_checkout_generates_krw_amount_from_server(self):
        a=self.new_order()
        result,params=self.checkout(a)
        self.assertTrue(result["sandbox_only"])
        self.assertEqual(params["line_items[0][price_data][unit_amount]"],"27000")
        self.assertEqual(params["line_items[0][price_data][currency]"],"krw")
        self.assertEqual(params["metadata[merchant_id]"],"17")
        with self.assertRaises(SandboxError):
            self.checkout(a)

    def test_refuses_live_checkout_response_even_with_test_key(self):
        a=self.new_order()
        with self.assertRaises(SandboxError):
            attach_test_checkout(self.con,CUSTOMER,a["id"],api_key=KEY,
                success_url="https://example.invalid/ok",
                cancel_url="https://example.invalid/cancel",
                create_session=lambda _:{"livemode":True,"id":"cs_live_synthetic",
                    "url":"https://checkout.stripe.com/c/pay/live"})
        self.assertIsNone(self.con.execute(
            "SELECT checkout_session_id FROM p2_sandbox_orders WHERE id=?",(a["id"],)).fetchone()[0])

    def test_signed_paid_webhook_and_merchant_notification(self):
        a=self.new_order();self.checkout(a)
        status=self.paid(a)
        self.assertEqual(status,{"processed":True,"state":"paid"})
        now=get_order(self.con,CUSTOMER,a["id"])
        self.assertEqual(now["version"],1)
        self.assertEqual([n["event"] for n in inbox(self.con,MERCHANT)],["new_paid_order"])
        self.assertEqual(inbox(self.con,OTHER_MERCHANT),[])

    def test_signature_replay_and_unpaid_blocked(self):
        a=self.new_order();self.checkout(a)
        event=self.event(a)
        raw,header=self.signed(event)
        with self.assertRaises(SandboxError):
            paid_webhook(self.con,raw,header[:-4]+"0000",signing_secret=SECRET)
        stale,stale_sig=self.signed(event,stamp=int(time.time())-3600)
        with self.assertRaises(SandboxError):
            paid_webhook(self.con,stale,stale_sig,signing_secret=SECRET)
        raw,h=self.signed(self.event(a,status="unpaid"))
        with self.assertRaises(SandboxError):
            paid_webhook(self.con,raw,h,signing_secret=SECRET)
        self.assertEqual(get_order(self.con,CUSTOMER,a["id"])["state"],"payment_pending")
        self.assertEqual(inbox(self.con,MERCHANT),[])

    def test_amount_currency_merchant_and_session_mismatch_fail_closed(self):
        a=self.new_order();self.checkout(a)
        cases=({"amount":1},{"currency":"usd"},{"merchant_id":"18"},
               {"session_id":"cs_test_other"},{"livemode":True})
        for kw in cases:
            ev=self.event(a,**kw)
            raw,h=self.signed(ev)
            with self.assertRaises(SandboxError):
                paid_webhook(self.con,raw,h,signing_secret=SECRET)
            self.assertEqual(get_order(self.con,CUSTOMER,a["id"])["state"],"payment_pending")

    def test_webhook_is_idempotent_even_distinct_paid_event_ids(self):
        a=self.new_order();self.checkout(a)
        self.assertTrue(self.paid(a)["processed"])
        self.assertFalse(self.paid(a)["processed"])
        self.assertTrue(self.paid(a,eid="evt_two")["duplicate_payment"])
        self.assertEqual(len(inbox(self.con,MERCHANT)),1)

    def test_role_scope_and_cross_tenant_denied(self):
        a=self.new_order();self.checkout(a);self.paid(a)
        with self.assertRaises(SandboxError):get_order(self.con,OTHER_MERCHANT,a["id"])
        with self.assertRaises(SandboxError):get_order(self.con,OTHER_RIDER,a["id"])
        with self.assertRaises(SandboxError):
            act(self.con,OTHER_MERCHANT,a["id"],"merchant_accept",1)
        with self.assertRaises(SandboxError):
            act(self.con,{"role":"customer","sub":"other"},a["id"],"customer_cancel",1)
        self.assertEqual(len(dashboard(self.con,MERCHANT)),1)
        self.assertEqual(dashboard(self.con,OTHER_MERCHANT),[])
        self.assertEqual(dashboard(self.con,RIDER),[])
        self.assertEqual(len(dashboard(self.con,OPS)),1)

    def test_merchant_dispatch_rider_delivery_and_outbox(self):
        a=self.new_order();self.checkout(a);self.paid(a)
        events=[("merchant_accept",1),("merchant_prepare",2),
                ("merchant_ready",3),("merchant_request_dispatch",4)]
        for event,version in events:
            status=act(self.con,MERCHANT,a["id"],event,version)
        self.assertEqual(status["state"],"dispatch_requested")
        with self.assertRaises(SandboxError):
            act(self.con,OTHER_RIDER,a["id"],"rider_accept",5,approved_riders=("rider_2",))
        status=act(self.con,RIDER,a["id"],"rider_accept",5,approved_riders=("rider_2",))
        self.assertEqual(status["state"],"rider_assigned")
        with self.assertRaises(Exception):
            act(self.con,OTHER_RIDER,a["id"],"rider_accept",5,approved_riders=("rider_3",))
        for event,ver in [("rider_pickup",6),("rider_start_delivery",7),("rider_deliver",8)]:
            status=act(self.con,RIDER,a["id"],event,ver)
        self.assertEqual(status["state"],"delivered")
        self.assertEqual(len(dashboard(self.con,RIDER)),1)
        self.assertIn("delivered",[n["event"] for n in inbox(self.con,CUSTOMER)])
        self.assertIn("rider_assigned",[n["event"] for n in inbox(self.con,MERCHANT)])
        self.assertEqual(inbox(self.con,OTHER_RIDER),[])

    def test_unverified_payment_service_cannot_set_paid(self):
        a=self.new_order()
        with self.assertRaises(SandboxError):
            act(self.con,{"role":"payment_service","sub":"stripe"},a["id"],"payment_verified",0)
        with self.assertRaises(SandboxError):
            act(self.con,CUSTOMER,a["id"],"merchant_accept",0)

    def test_stale_version_cannot_advance(self):
        a=self.new_order();self.checkout(a);self.paid(a)
        act(self.con,MERCHANT,a["id"],"merchant_accept",1)
        with self.assertRaises(Exception):
            act(self.con,MERCHANT,a["id"],"merchant_prepare",1)
        self.assertEqual(get_order(self.con,CUSTOMER,a["id"])["state"],"merchant_accepted")


if __name__=="__main__":
    unittest.main()
