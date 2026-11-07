"""Local-beta E2E tests for admin revisions and server-priced product options."""
from __future__ import annotations
import http.client
import json
import os
import tempfile
import threading
import unittest
from pathlib import Path
from admin_core.database import init_db,connect,password_hash
from admin_core.server import Server

class OptionsTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.tmp=tempfile.TemporaryDirectory()
  cls.db=Path(cls.tmp.name)/"options.sqlite3"
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
   p.unlink(missing_ok=True)
  os.environ["GARAK_BOOTSTRAP_PASSWORD"]="TestingOnly_Admin_2026!"
  with init_db(self.db):pass
  self.cookie=None
  self.csrf=None
 def request(self,method,path,body=None,csrf=True):
  con=http.client.HTTPConnection("127.0.0.1",self.port,timeout=8)
  headers={"Content-Type":"application/json"}
  if self.cookie:headers["Cookie"]=self.cookie
  if csrf and self.csrf:headers["X-Garak-CSRF"]=self.csrf
  encoded=json.dumps(body,ensure_ascii=False).encode() if body is not None else None
  con.request(method,path,encoded,headers=headers)
  res=con.getresponse()
  raw=res.read()
  result=(res.status,json.loads(raw.decode("utf-8")),dict(res.getheaders()))
  con.close()
  return result
 def login(self,username="admin",password="TestingOnly_Admin_2026!"):
  status,data,headers=self.request("POST","/api/auth/login",{"username":username,"password":password})
  self.assertEqual(status,200,data)
  self.cookie=headers["Set-Cookie"].split(";",1)[0]
  self.csrf=data["csrf"]
 def merchant_active(self):
  with connect(self.db) as con:
   con.execute("""UPDATE merchants SET status='active',verified=1
                  WHERE id=(SELECT merchant_id FROM products WHERE slug='bangeo-hoe')""")
 def groups(self):
  return [
   {"id":"prepare","title":"손질 방식","required":True,
    "choices":[{"id":"clean","label":"손질 후","additional_krw":3000,"stock":7},
               {"id":"whole","label":"손질 전","additional_krw":0}]},
   {"id":"side","title":"추가 사이드","required":False,"max_select":2,
    "choices":[{"id":"rice","label":"공기밥","additional_krw":1000},
               {"id":"sauce","label":"소스","additional_krw":500}]},
  ]
 def draft(self,groups=None):
  self.login()
  return self.request("POST","/api/admin/product-options/bangeo-hoe/revisions",
          {"groups":self.groups() if groups is None else groups})
 def approve(self,version=1):
  self.merchant_active()
  return self.request("POST",f"/api/admin/product-options/bangeo-hoe/revisions/{version}/approve",{})
 def item(self,options,qty=2):
  return {"items":[{"slug":"bangeo-hoe","qty":qty,"options":options,"price_krw":1}]}
 def valid(self):
  return [{"group_id":"prepare","choice_ids":["clean"]},
          {"group_id":"side","choice_ids":["rice","sauce"]}]
 def test_draft_not_public_until_approved(self):
  status,data,_=self.draft()
  self.assertEqual(status,201,data)
  self.assertEqual(data["data"]["version"],1)
  self.merchant_active()
  _,detail,_=self.request("GET","/api/v1/mobile/products/bangeo-hoe")
  self.assertEqual(detail["data"]["option_groups"],[])
  self.assertEqual(detail["data"]["options_version"],0)
  _,admin,_=self.request("GET","/api/admin/product-options/bangeo-hoe")
  self.assertEqual(admin["latest_draft"]["version"],1)
 def test_approved_options_server_quote(self):
  self.assertEqual(self.draft()[0],201)
  self.assertEqual(self.approve()[0],200)
  _,detail,_=self.request("GET","/api/v1/mobile/products/bangeo-hoe")
  self.assertEqual(detail["data"]["options_version"],1)
  self.assertEqual(len(detail["data"]["option_groups"]),2)
  status,quote,_=self.request("POST","/api/v1/mobile/cart/quote",self.item(self.valid()))
  self.assertEqual(status,200,quote)
  line=quote["data"]["items"][0]
  self.assertEqual(line["base_unit_price_krw"],55000)
  self.assertEqual(line["option_unit_price_krw"],4500)
  self.assertEqual(line["unit_price_krw"],59500)
  self.assertEqual(line["line_total_krw"],119000)
  self.assertEqual(quote["data"]["subtotal_krw"],119000)
  self.assertIsNone(quote["data"]["payable_total_krw"])
  self.assertFalse(quote["data"]["checkout_enabled"])
 def test_required_option_absent_blocks_quote(self):
  self.draft()
  self.approve()
  self.assertEqual(self.request("POST","/api/v1/mobile/cart/quote",self.item([]))[0],400)
 def test_unknown_option_blocks_quote(self):
  self.draft()
  self.approve()
  self.assertEqual(self.request("POST","/api/v1/mobile/cart/quote",self.item(
    [{"group_id":"prepare","choice_ids":["invalid"]}]))[0],400)
 def test_quantity_exceeds_choice_stock(self):
  self.draft()
  self.approve()
  self.assertEqual(self.request("POST","/api/v1/mobile/cart/quote",self.item(self.valid(),8))[0],400)
 def test_duplicate_choice_blocks(self):
  self.draft()
  self.approve()
  self.assertEqual(self.request("POST","/api/v1/mobile/cart/quote",self.item(
    [{"group_id":"prepare","choice_ids":["clean","clean"]}]))[0],400)
 def test_unverified_merchant_cannot_approve(self):
  self.draft()
  self.assertEqual(self.request("POST","/api/admin/product-options/bangeo-hoe/revisions/1/approve",{})[0],400)
 def test_negative_price_draft_rejected(self):
  g=self.groups()
  g[0]["choices"][0]["additional_krw"]=-100
  self.assertEqual(self.draft(g)[0],400)
  with connect(self.db) as con:
   self.assertEqual(con.execute("SELECT count(*) FROM product_option_sets").fetchone()[0],0)
 def test_duplicate_group_draft_rejected(self):
  g=self.groups()+[self.groups()[0]]
  self.assertEqual(self.draft(g)[0],400)
 def test_draft_post_requires_csrf(self):
  self.login()
  self.assertEqual(self.request("POST","/api/admin/product-options/bangeo-hoe/revisions",
    {"groups":[]},csrf=False)[0],403)
 def test_public_cannot_read_admin_draft(self):
  self.assertEqual(self.request("GET","/api/admin/product-options/bangeo-hoe")[0],401)
 def test_ops_can_draft_but_cannot_approve(self):
  with connect(self.db) as con:
   con.execute("INSERT INTO users(username,password_hash,role,created_at) VALUES(?,?,?,?)",
     ("ops_user",password_hash("Ops_Test_Account_Pass_2026"),"ops","2026-11-07"))
  self.login("ops_user","Ops_Test_Account_Pass_2026")
  self.assertEqual(self.request("POST","/api/admin/product-options/bangeo-hoe/revisions",
    {"groups":self.groups()})[0],201)
  self.merchant_active()
  self.assertEqual(self.request("POST","/api/admin/product-options/bangeo-hoe/revisions/1/approve",{})[0],403)
 def test_revisions_are_preserved(self):
  self.draft()
  self.approve(1)
  g=self.groups()
  g[0]["choices"][0]["additional_krw"]=4000
  result=self.request("POST","/api/admin/product-options/bangeo-hoe/revisions",{"groups":g})
  self.assertEqual(result[1]["data"]["version"],2)
  self.assertEqual(self.approve(2)[0],200)
  with connect(self.db) as con:
   statuses=[(r["version"],r["status"]) for r in con.execute(
    "SELECT version,status FROM product_option_sets ORDER BY version").fetchall()]
  self.assertEqual(statuses,[(1,"superseded"),(2,"approved")])
 def test_quote_does_not_modify_orders_or_stock(self):
  self.draft()
  self.approve()
  with connect(self.db) as con:
   stock=con.execute("SELECT stock FROM products WHERE slug='bangeo-hoe'").fetchone()[0]
   orders=con.execute("SELECT count(*) FROM orders").fetchone()[0]
  self.request("POST","/api/v1/mobile/cart/quote",self.item(self.valid()))
  with connect(self.db) as con:
   self.assertEqual(con.execute("SELECT stock FROM products WHERE slug='bangeo-hoe'").fetchone()[0],stock)
   self.assertEqual(con.execute("SELECT count(*) FROM orders").fetchone()[0],orders)
 def test_real_payment_paths_still_blocked(self):
  for path in ("/api/v1/mobile/orders","/api/v1/mobile/payments/prepare",
               "/api/v1/mobile/payments/confirm"):
   self.assertEqual(self.request("POST",path,{"items":[{"slug":"bangeo-hoe","qty":1}]})[0],404)

if __name__=="__main__":
 unittest.main()
