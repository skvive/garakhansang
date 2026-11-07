"""P2 isolated local-beta checkout-intent contract and race tests."""
from __future__ import annotations
import concurrent.futures
import http.client
import json
import os
import tempfile
import threading
import unittest
from pathlib import Path

from admin_core.database import connect,init_db,password_hash
from admin_core.server import Server

PASSWORD="P2_Admin_Test_Pass_2026!"

class OrderIntentTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.tmp=tempfile.TemporaryDirectory()
  cls.db=Path(cls.tmp.name)/"intents.sqlite3"
  cls.server=Server(("127.0.0.1",0),cls.db)
  cls.thread=threading.Thread(target=cls.server.serve_forever,daemon=True)
  cls.thread.start()
  cls.port=cls.server.server_address[1]
 @classmethod
 def tearDownClass(cls):
  cls.server.shutdown()
  cls.server.server_close()
  cls.tmp.cleanup()
 def setUp(self):
  for p in self.db.parent.glob("*"):
   if p.is_file():p.unlink(missing_ok=True)
  os.environ["GARAK_BOOTSTRAP_PASSWORD"]=PASSWORD
  os.environ["GARAK_ORDER_SANDBOX"]="1"
  with init_db(self.db,seed=True,bootstrap=True):pass
  self.cookie=None
  self.csrf=None
  self.key="OrderIntent-Test-Key-00000001"
  with connect(self.db) as con:
   con.execute("""UPDATE merchants SET status='active',verified=1
     WHERE id=(SELECT merchant_id FROM products WHERE slug='bangeo-hoe')""")
 def tearDown(self):
  os.environ.pop("GARAK_ORDER_SANDBOX",None)
 def req(self,method,path,data=None,key=None,csrf=True,cookie=True):
  client=http.client.HTTPConnection("127.0.0.1",self.port,timeout=15)
  h={"Content-Type":"application/json"}
  if cookie and self.cookie:h["Cookie"]=self.cookie
  if csrf and self.csrf:h["X-Garak-CSRF"]=self.csrf
  if key:h["Idempotency-Key"]=key
  body=json.dumps(data,ensure_ascii=False).encode() if data is not None else None
  client.request(method,path,body=body,headers=h)
  resp=client.getresponse()
  raw=resp.read().decode()
  out=(resp.status,json.loads(raw),dict(resp.getheaders()))
  client.close()
  return out
 def login(self,username="admin",password=PASSWORD):
  status,data,headers=self.req("POST","/api/auth/login",{"username":username,"password":password})
  self.assertEqual(status,200,data)
  self.cookie=headers["Set-Cookie"].split(";",1)[0]
  self.csrf=data["csrf"]
 def payload(self,qty=2):
  return {"items":[{"slug":"bangeo-hoe","qty":qty}],"delivery_type":"delivery"}
 def make(self,key=None,data=None):
  return self.req("POST","/api/admin/order-intents",
    self.payload() if data is None else data,key=key or self.key)
 def test_unauthenticated_denied(self):
  self.assertEqual(self.make()[0],401)
  self.assertEqual(self.req("GET","/api/admin/order-intents")[0],401)
 def test_requires_explicit_sandbox_flag(self):
  self.login()
  os.environ.pop("GARAK_ORDER_SANDBOX",None)
  self.assertEqual(self.make()[0],503)
  self.assertEqual(self.req("GET","/api/admin/order-intents")[0],503)
 def test_csrf_enforced(self):
  self.login()
  self.assertEqual(self.req("POST","/api/admin/order-intents",self.payload(),key=self.key,csrf=False)[0],403)
 def test_idempotent_replay(self):
  self.login()
  a=self.make();b=self.make()
  self.assertEqual((a[0],b[0]),(201,200),(a,b))
  self.assertEqual(a[1]["data"]["reference"],b[1]["data"]["reference"])
  with connect(self.db) as con:
   self.assertEqual(con.execute("SELECT count(*) FROM checkout_intents").fetchone()[0],1)
   self.assertEqual(con.execute("SELECT count(*) FROM audit_logs WHERE action='checkout_intent_created'").fetchone()[0],1)
 def test_conflicting_key_rejected(self):
  self.login();self.assertEqual(self.make()[0],201)
  self.assertEqual(self.make(data=self.payload(3))[0],409)
 def test_missing_or_invalid_key_rejected(self):
  self.login()
  for key in ["short","Contains Spaces In Idempotency Key","é"*20,"a"*97]:
   self.assertEqual(self.make(key=key)[0],400,key)
  self.assertEqual(self.req("POST","/api/admin/order-intents",self.payload())[0],400)
 def test_client_total_and_pii_rejected(self):
  self.login()
  for field,value in [("price",1),("address","private"),("card","1234"),("payment","paid"),("customer_name","demo")]:
   p=self.payload();p[field]=value
   self.assertEqual(self.make(data=p)[0],400,field)
 def test_client_nested_price_or_pii_rejected(self):
  self.login()
  for name,value in [("price",1),("client_total_krw",1),
                     ("phone","010-0000-0000"),("card_number","4111111111111111")]:
   data=self.payload()
   data["items"][0][name]=value
   self.assertEqual(self.make(data=data)[0],400,name)
  with connect(self.db) as con:
   self.assertEqual(con.execute("SELECT count(*) FROM checkout_intents").fetchone()[0],0)
 def test_extra_option_payload_rejected(self):
  self.login()
  data=self.payload()
  data["items"][0]["options"]=[{"group_id":"prep","choice_ids":["clean"],"payment":"fake"}]
  self.assertEqual(self.make(data=data)[0],400)
 def test_unverified_merchant_rejected(self):
  self.login()
  with connect(self.db) as con:
   con.execute("""UPDATE merchants SET verified=0
       WHERE id=(SELECT merchant_id FROM products WHERE slug='bangeo-hoe')""")
  self.assertEqual(self.make()[0],400)
 def test_stock_check_rejected(self):
  self.login()
  self.assertEqual(self.make(data=self.payload(40))[0],400)
 def test_no_payment_or_stock_or_real_orders(self):
  self.login()
  with connect(self.db) as con:
   stock=con.execute("SELECT stock FROM products WHERE slug='bangeo-hoe'").fetchone()[0]
   orders=con.execute("SELECT count(*) FROM orders").fetchone()[0]
  code,data,_=self.make()
  self.assertEqual(code,201,data)
  intent=data["data"]
  self.assertEqual(intent["status"],"awaiting_delivery_policy")
  self.assertFalse(intent["checkout_enabled"])
  self.assertIsNone(intent["payable_total_krw"])
  self.assertFalse(intent["merchant_notified"])
  self.assertFalse(intent["dispatch_enabled"])
  self.assertEqual(intent["payment_status"],"not_initiated")
  self.assertEqual(intent["subtotal_krw"],110000)
  with connect(self.db) as con:
   self.assertEqual(con.execute("SELECT stock FROM products WHERE slug='bangeo-hoe'").fetchone()[0],stock)
   self.assertEqual(con.execute("SELECT count(*) FROM orders").fetchone()[0],orders)
 def test_snapshot_preserved_on_replay_and_new_price_requote(self):
  self.login()
  a=self.make()[1]["data"]
  with connect(self.db) as con:
   con.execute("UPDATE products SET price=57000 WHERE slug='bangeo-hoe'")
  b=self.make()[1]["data"]
  self.assertEqual(b["subtotal_krw"],a["subtotal_krw"])
  c=self.make(key="OrderIntent-Test-Key-00000002")[1]["data"]
  self.assertEqual(c["subtotal_krw"],114000)
 def test_read_and_list(self):
  self.login();made=self.make()[1]["data"]
  code,data,_=self.req("GET","/api/admin/order-intents/"+made["reference"])
  self.assertEqual(code,200)
  self.assertEqual(data["data"]["reference"],made["reference"])
  code,data,_=self.req("GET","/api/admin/order-intents")
  self.assertEqual(code,200)
  self.assertEqual(len(data["data"]["items"]),1)
 def test_abandon_requires_version_and_owner(self):
  self.login();created=self.make()[1]["data"]
  base="/api/admin/order-intents/"+created["reference"]+"/abandon"
  self.assertEqual(self.req("POST",base,{"expected_version":0})[0],400)
  self.assertEqual(self.req("POST",base,{"expected_version":1})[0],200)
  self.assertEqual(self.req("POST",base,{"expected_version":1})[0],409)
  data=self.req("GET","/api/admin/order-intents/"+created["reference"])[1]["data"]
  self.assertEqual((data["status"],data["version"]),("abandoned",2))
 def test_different_admin_cannot_reuse_or_cancel_other_key(self):
  self.login()
  old=self.make()[1]["data"]
  with connect(self.db) as con:
   con.execute("INSERT INTO users(username,password_hash,role,created_at) VALUES(?,?,?,?)",
              ("ops_a",password_hash("Ops_Account_Test_P2_Pass!"),"ops","2026-11-07"))
  self.login("ops_a","Ops_Account_Test_P2_Pass!")
  self.assertEqual(self.req("GET","/api/admin/order-intents/"+old["reference"])[0],404)
  self.assertEqual(self.req("POST","/api/admin/order-intents/"+old["reference"]+"/abandon",
                             {"expected_version":1})[0],404)
  new=self.make()[1]["data"]
  self.assertNotEqual(new["reference"],old["reference"])
 def test_parallel_same_key_only_one_record(self):
  self.login()
  with concurrent.futures.ThreadPoolExecutor(max_workers=6) as pool:
   res=list(pool.map(lambda i:self.make(),range(6)))
  self.assertEqual(sorted(v[0] for v in res),[200]*5+[201],[x[0] for x in res])
  refs={x[1]["data"]["reference"] for x in res}
  self.assertEqual(len(refs),1)
  with connect(self.db) as con:
   self.assertEqual(con.execute("SELECT count(*) FROM checkout_intents").fetchone()[0],1)
 def test_approved_options_snapshot(self):
  self.login()
  with connect(self.db) as con:
   now="2026-11-07T00:00:00+00:00"
   pid=con.execute("SELECT id FROM products WHERE slug='bangeo-hoe'").fetchone()[0]
   groups=[{"id":"prep","title":"손질","required":True,"min_select":1,"max_select":1,
            "choices":[{"id":"clean","label":"손질 후","additional_krw":3000,"stock":5}]}]
   con.execute("""INSERT INTO product_option_sets
      (product_id,version,status,groups_json,created_at,approved_at)
      VALUES(?,1,'approved',?,?,?)""",(pid,json.dumps(groups),now,now))
  payload=self.payload()
  payload["items"][0]["options"]=[{"group_id":"prep","choice_ids":["clean"]}]
  data=self.make(data=payload)[1]["data"]
  self.assertEqual(data["subtotal_krw"],116000)
  self.assertEqual(data["quote"]["items"][0]["options_version"],1)
  self.assertEqual(data["quote"]["items"][0]["selected_options"][0]["choice_id"],"clean")
 def test_public_payment_merchant_dispatch_remain_blocked(self):
  self.login()
  for path in ("/api/v1/mobile/orders","/api/v1/mobile/payments/prepare",
               "/api/v1/mobile/payments/confirm","/api/v1/merchant/orders",
               "/api/v1/rider/dispatch"):
   self.assertEqual(self.req("POST",path,{"event":"paid"})[0],404,path)

if __name__=="__main__":unittest.main()
