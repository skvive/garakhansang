"""V7 edge-case tests; independent databases, no real commerce transactions."""
import unittest, tempfile, threading, os, json, http.client
from pathlib import Path
from admin_core.database import init_db, connect
from admin_core.server import Server

class V7Regressions(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.temp=tempfile.TemporaryDirectory();cls.db=Path(cls.temp.name)/'test.sqlite3'
  cls.server=Server(('127.0.0.1',0),cls.db);cls.port=cls.server.server_address[1]
  cls.thread=threading.Thread(target=cls.server.serve_forever,daemon=True);cls.thread.start()
 @classmethod
 def tearDownClass(cls):cls.server.shutdown();cls.server.server_close();cls.temp.cleanup()
 def setUp(self):
  for p in self.db.parent.glob('*'):p.unlink(missing_ok=True)
  os.environ['GARAK_BOOTSTRAP_PASSWORD']='OnlyLocalStrongTest_2026!'
  with init_db(self.db):pass
  self.cookie='';self.csrf=''
 def req(self,method,path,body=None):
  h={'Content-Type':'application/json'}
  if self.cookie:h['Cookie']=self.cookie
  if self.csrf:h['X-Garak-CSRF']=self.csrf
  c=http.client.HTTPConnection('127.0.0.1',self.port,timeout=5)
  c.request(method,path,json.dumps(body,ensure_ascii=False).encode() if body is not None else None,h)
  r=c.getresponse();b=r.read();out=(r.status,json.loads(b.decode()) if b else {},dict(r.getheaders()));c.close();return out
 def login(self):
  code,body,h=self.req('POST','/api/auth/login',{'username':'admin','password':'OnlyLocalStrongTest_2026!'})
  self.assertEqual(code,200);self.cookie=h['Set-Cookie'].split(';')[0];self.csrf=body['csrf']
 def stock(self):
  with connect(self.db) as con:return con.execute("SELECT stock FROM products WHERE slug='bangeo-hoe'").fetchone()[0]
 def test_duplicate_overstock_rejected_without_side_effect(self):
  self.login();status,data,_=self.req('POST','/api/admin/orders/create',{'items':[{'slug':'bangeo-hoe','qty':12},{'slug':'bangeo-hoe','qty':12}]})
  self.assertEqual(status,400);self.assertIn('합산',data['error']);self.assertEqual(self.stock(),20)
  with connect(self.db) as c:self.assertEqual(c.execute('SELECT COUNT(*) FROM orders').fetchone()[0],0)
 def test_duplicate_valid_quantities_are_merged(self):
  self.login();status,d,_=self.req('POST','/api/admin/orders/create',{'items':[{'slug':'bangeo-hoe','qty':6},{'slug':'bangeo-hoe','qty':4}]})
  self.assertEqual(status,201);self.assertEqual(self.stock(),10)
  with connect(self.db) as c:
   row=c.execute('SELECT COUNT(*),SUM(qty) FROM order_items').fetchone();self.assertEqual(tuple(row),(1,10))
 def test_multiple_products_roll_back_on_second_out_of_stock(self):
  self.login();status,d,_=self.req('POST','/api/admin/orders/create',{'items':[{'slug':'bangeo-hoe','qty':2},{'slug':'yeon-eo','qty':50}]})
  self.assertEqual(status,400);self.assertEqual(self.stock(),20)
  with connect(self.db) as c:self.assertEqual(c.execute('SELECT COUNT(*) FROM orders').fetchone()[0],0)
 def test_bool_qty_is_invalid(self):
  self.login();self.assertEqual(self.req('POST','/api/admin/orders/create',{'items':[{'slug':'bangeo-hoe','qty':True}]})[0],400)
 def test_password_rotation_revokes_all_sessions(self):
  self.login();c1=self.cookie;csrf1=self.csrf
  self.login();c2=self.cookie
  self.assertEqual(self.req('POST','/api/auth/password',{'current_password':'OnlyLocalStrongTest_2026!','new_password':'NewStrongPassword_2026!'} )[0],200)
  self.assertEqual(self.req('GET','/api/admin/products')[0],401)
  self.cookie=c1;self.csrf=csrf1;self.assertEqual(self.req('GET','/api/admin/products')[0],401)
 def test_shipping_status_cannot_bypass_order_machine(self):
  self.login();d=self.req('POST','/api/admin/orders/create',{'items':[{'slug':'bangeo-hoe','qty':1}]})[1]
  with connect(self.db) as c: sid=c.execute('SELECT id FROM shipments WHERE order_id=?',(d['order_id'],)).fetchone()[0]
  self.assertEqual(self.req('PATCH',f'/api/admin/shipments/{sid}',{'status':'delivered','carrier':'test','tracking':'TEST1'})[0],400)
  with connect(self.db) as c:self.assertEqual(c.execute('SELECT status FROM shipments WHERE id=?',(sid,)).fetchone()[0],'pending')
 def test_merchant_cannot_be_active_after_unverification(self):
  self.login();self.assertEqual(self.req('PATCH','/api/admin/merchants/1',{'verified':1,'status':'active'})[0],200)
  self.assertEqual(self.req('PATCH','/api/admin/merchants/1',{'verified':0})[0],400)
  with connect(self.db) as c:self.assertEqual(c.execute('SELECT verified FROM merchants WHERE id=1').fetchone()[0],1)
 def test_new_product_publish_requires_verified_active_merchant(self):
  self.login();d=self.req('POST','/api/admin/products',{'slug':'test-seafood','name':'신규 테스트 수산물','category':'seafood','merchant_id':1,'price':10000,'stock':3})[1]
  pid=d['id'];self.assertEqual(self.req('PATCH',f'/api/admin/products/{pid}',{'status':'published'})[0],400)
  self.assertEqual(self.req('PATCH','/api/admin/merchants/1',{'status':'active','verified':1})[0],200)
  self.assertEqual(self.req('PATCH',f'/api/admin/products/{pid}',{'status':'published'})[0],200)
 def test_zero_or_negative_qty_cannot_modify_stock(self):
  self.login()
  for qty in [0,-1,51]:self.assertEqual(self.req('POST','/api/admin/orders/create',{'items':[{'slug':'bangeo-hoe','qty':qty}]})[0],400)
  self.assertEqual(self.stock(),20)
if __name__=='__main__':unittest.main()
