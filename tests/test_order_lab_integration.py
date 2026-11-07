"""Full local (synthetic) customer -> ops -> merchant -> rider E2E API tests."""
from __future__ import annotations

import http.client
import json
import tempfile
import threading
import unittest
from pathlib import Path

from admin_core.database import connect
from admin_core.order_lab_server import LabServer, init_lab

PASSWORDS={r:"LocalSandboxOnlyPassword__"+r+"42" for r in ("customer","merchant","rider","ops")}


class LabHttpTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp=tempfile.TemporaryDirectory()
        cls.path=Path(cls.temp.name)/"staging-lab.sqlite3"
        cls.merchant_id=init_lab(cls.path,PASSWORDS)
        cls.server=LabServer(("127.0.0.1",0),cls.path)
        cls.port=cls.server.server_address[1]
        cls.thread=threading.Thread(target=cls.server.serve_forever,daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.temp.cleanup()

    def setUp(self):
        with connect(self.path) as db:
            db.execute("DELETE FROM p3_lab_sessions")
            db.execute("DELETE FROM p2_sandbox_outbox")
            db.execute("DELETE FROM p2_sandbox_events")
            db.execute("DELETE FROM p2_sandbox_orders")
            db.execute("UPDATE p3_lab_rider_status SET approved=1,on_duty=1 WHERE subject='r_demo'")
            db.execute("UPDATE products SET stock=20")
            db.execute("UPDATE merchants SET status='pending',verified=0")
            db.execute("UPDATE merchants SET status='active',verified=1 WHERE id=?",
                       (self.merchant_id,))

    def request(self, method, path, data=None, session=None, csrf_override=None):
        conn=http.client.HTTPConnection("127.0.0.1",self.port,timeout=5)
        headers={"Content-Type":"application/json"}
        if session:
            headers["Cookie"]=session[0]
            if method=="POST":headers["X-Lab-CSRF"]=session[1] if csrf_override is None else csrf_override
        payload=json.dumps(data,ensure_ascii=False).encode() if data is not None else None
        conn.request(method,path,body=payload,headers=headers)
        res=conn.getresponse()
        raw=res.read()
        body=json.loads(raw.decode()) if res.getheader("Content-Type","").startswith("application/json") else raw
        status=res.status
        cookie=res.getheader("Set-Cookie","").split(";",1)[0]
        conn.close()
        return status,body,cookie

    def login(self,username):
        code,body,cookie=self.request("POST","/lab/api/login",
                                   {"username":username,"password":PASSWORDS[username]})
        self.assertEqual(code,200,body)
        return cookie,body["csrf"]

    def order(self,customer):
        code,items,_=self.request("GET","/lab/api/products",session=customer)
        self.assertEqual(code,200)
        self.assertTrue(items["items"])
        slug=items["items"][0]["slug"]
        code,obj,_=self.request("POST","/lab/api/order/draft",
                          {"items":[{"slug":slug,"qty":1}],
                           "idempotency_key":"integration-test-key-42"},
                           session=customer)
        self.assertEqual(code,201,obj)
        return obj["order"]

    def test_host_only_loopback(self):
        with self.assertRaises(RuntimeError):
            LabServer(("0.0.0.0",0),self.path)

    def test_health_and_anonymous_are_separate(self):
        self.assertEqual(self.request("GET","/lab/api/health")[0],200)
        self.assertEqual(self.request("GET","/lab/api/products")[0],401)
        self.assertEqual(self.request("GET","/admin/index.html")[0],404)

    def test_auth_and_csrf_rejects_foreign_and_role(self):
        customer=self.login("customer")
        self.assertEqual(self.request("POST","/lab/api/order/draft",
                            {"items":[],"idempotency_key":"foo"},session=customer,
                            csrf_override="bad")[0],401)
        self.assertEqual(self.request("POST","/lab/api/merchants/approve",
                            {"id":int(self.merchant_id)},session=customer)[0],403)
        self.assertEqual(self.request("GET","/lab/api/merchants",session=customer)[0],403)
        self.assertEqual(self.request("GET","/lab/api/riders",session=customer)[0],403)

    def test_full_order_payment_merchant_rider_delivery(self):
        customer,merchant,rider,ops=(self.login(r) for r in ("customer","merchant","rider","ops"))
        order=self.order(customer)
        oid=order["id"]
        self.assertEqual(order["state"],"payment_pending")
        self.assertEqual(order["delivery_fee_krw"],2000)
        self.assertEqual(self.request("POST",f"/lab/api/order/{oid}/simulate-paid",
                                      session=customer)[0],403)
        code,p,_=self.request("POST",f"/lab/api/order/{oid}/simulate-paid",
                              {},session=ops)
        self.assertEqual(code,200,p)
        self.assertTrue(p["synthetic_event"])
        merchant_orders=self.request("GET","/lab/api/orders",session=merchant)[1]["items"]
        self.assertEqual(merchant_orders[0]["state"],"paid")
        self.assertEqual(self.request("GET","/lab/api/inbox",session=merchant)[1]["items"][0]["event"],
                         "new_paid_order")
        for event,version in (("merchant_accept",1),("merchant_prepare",2),
                              ("merchant_ready",3),("merchant_request_dispatch",4)):
            code,p,_=self.request("POST",f"/lab/api/order/{oid}/transition",
                             {"event":event,"version":version},session=merchant)
            self.assertEqual(code,200,(event,p))
        dispatch=self.request("GET","/lab/api/dispatch",session=rider)[1]["items"]
        self.assertEqual(len(dispatch),1)
        self.assertEqual(dispatch[0]["id"],oid)
        for event,version in (("rider_accept",5),("rider_pickup",6),
                              ("rider_start_delivery",7),("rider_deliver",8)):
            code,p,_=self.request("POST",f"/lab/api/order/{oid}/transition",
                         {"event":event,"version":version},session=rider)
            self.assertEqual(code,200,(event,p))
        done=self.request("GET","/lab/api/orders",session=customer)[1]["items"][0]
        self.assertEqual(done["state"],"delivered")
        self.assertEqual(self.request("GET","/lab/api/settlements",session=merchant)[0],200)
        settlement=self.request("GET","/lab/api/settlements",session=merchant)[1]["items"][0]
        self.assertFalse(settlement["payout_executed"])
        self.assertEqual(settlement["gross_krw"],order["subtotal_krw"])

    def test_rider_approval_required(self):
        customer=self.login("customer")
        ops=self.login("ops")
        rider=self.login("rider")
        order=self.order(customer)
        oid=order["id"]
        self.request("POST",f"/lab/api/order/{oid}/simulate-paid",{},session=ops)
        merchant=self.login("merchant")
        for event,v in (("merchant_accept",1),("merchant_prepare",2),
                        ("merchant_ready",3),("merchant_request_dispatch",4)):
            self.request("POST",f"/lab/api/order/{oid}/transition",
                         {"event":event,"version":v},session=merchant)
        self.assertEqual(self.request("POST","/lab/api/riders/approve",
                         {"sub":"r_demo","approved":False},session=ops)[0],200)
        self.assertEqual(self.request("GET","/lab/api/dispatch",session=rider)[1]["items"],[])
        self.assertEqual(self.request("POST",f"/lab/api/order/{oid}/transition",
                         {"event":"rider_accept","version":5},session=rider)[0],400)

    def test_merchant_stock_and_simulated_refund(self):
        customer=self.login("customer")
        merchant=self.login("merchant")
        ops=self.login("ops")
        order=self.order(customer)
        oid=order["id"]
        self.request("POST",f"/lab/api/order/{oid}/simulate-paid",{},session=ops)
        code,p,_=self.request("POST",f"/lab/api/order/{oid}/transition",
                              {"event":"customer_cancel","version":1},session=customer)
        self.assertEqual(code,200,p)
        self.assertEqual(p["order"]["state"],"refund_pending")
        code,p,_=self.request("POST",f"/lab/api/order/{oid}/simulate-refund",{},session=ops)
        self.assertEqual(code,200,p)
        self.assertTrue(p["synthetic_refund"])
        self.assertEqual(self.request("GET","/lab/api/orders",session=customer)[1]["items"][0]["state"],
                         "refunded")
        slug=self.request("GET","/lab/api/products",session=merchant)[1]["items"][0]["slug"]
        self.assertEqual(self.request("POST","/lab/api/products/stock",
                              {"slug":slug,"stock":0},session=merchant)[0],200)
        self.assertEqual(self.request("GET","/lab/api/products",session=merchant)[1]["items"][0]["stock"],0)

    def test_stripe_test_webhook_http_signature_required(self):
        import hashlib
        import hmac
        import time
        from admin_core.order_p2_sandbox import attach_test_checkout
        customer=self.login("customer")
        merchant=self.login("merchant")
        order=self.order(customer)
        oid=order["id"]
        sid="cs_test_http_synthetic_123"
        with connect(self.path) as db:
            attach_test_checkout(db,{"role":"customer","sub":"c_demo"},oid,
                api_key="sk_test_http_fake",
                success_url="https://example.invalid/ok",
                cancel_url="https://example.invalid/cancel",
                create_session=lambda _:{"livemode":False,"id":sid,
                   "url":"https://checkout.stripe.com/c/pay/http-lab"})
        secret="whsec_http_test_only"
        self.server.lab_test_webhook_secret=secret
        event={"id":"evt_http_test_only","livemode":False,"type":"checkout.session.completed",
          "data":{"object":{"id":sid,"livemode":False,"mode":"payment",
             "status":"complete","payment_status":"paid","currency":"krw",
             "amount_total":order["total_krw"],"client_reference_id":"c_demo",
             "metadata":{"order_id":oid,"merchant_id":order["merchant_id"]}}}}
        payload=json.dumps(event,separators=(",",":")).encode()
        stamp=int(time.time())
        signature=hmac.new(secret.encode(),str(stamp).encode()+b"."+payload,
                            hashlib.sha256).hexdigest()
        def post(sig):
            conn=http.client.HTTPConnection("127.0.0.1",self.port,timeout=5)
            conn.request("POST","/lab/api/stripe/webhook",payload,
                headers={"Content-Type":"application/json",
                         "Stripe-Signature":f"t={stamp},v1={sig}"})
            res=conn.getresponse()
            code=res.status;data=json.loads(res.read());conn.close()
            return code,data
        self.assertEqual(post("0"*64)[0],400)
        self.assertEqual(self.request("GET","/lab/api/orders",session=customer)[1]["items"][0]["state"],"payment_pending")
        code,data=post(signature)
        self.assertEqual(code,200,data)
        self.assertTrue(data["processed"])
        self.assertEqual(post(signature)[1]["duplicate"],True)
        self.assertEqual(self.request("GET","/lab/api/inbox",session=merchant)[1]["items"][0]["event"],
                         "new_paid_order")
        self.server.lab_test_webhook_secret=""


if __name__=="__main__":
    unittest.main()
