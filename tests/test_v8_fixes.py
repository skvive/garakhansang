"""V8 failures reproduced on HTTP server; regression tests run against ephemeral beta DB only."""
import tempfile,os,http.client,json,threading,unittest
from pathlib import Path
from admin_core.database import connect,init_db
from admin_core.server import Server

class V8FailureRegression(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.tmp=tempfile.TemporaryDirectory();cls.path=Path(cls.tmp.name)/'qa.sqlite3'
  cls.server=Server(('127.0.0.1',0),cls.path);cls.port=cls.server.server_address[1]
  cls.thread=threading.Thread(target=cls.server.serve_forever,daemon=True);cls.thread.start()
 @classmethod
 def tearDownClass(cls):
  cls.server.shutdown();cls.server.server_close();cls.tmp.cleanup()
 def setUp(self):
  for p in self.path.parent.iterdir():
   if p.is_file():p.unlink(missing_ok=True)
  os.environ['GARAK_BOOTSTRAP_PASSWORD']='V8Regression-Only_2026!'
  with init_db(self.path):pass
  self.cookie='';self.csrf=''
 def request(self,method,path,payload=None):
  h={'Content-Type':'application/json'}
  if self.cookie:h['Cookie']=self.cookie
  if self.csrf:h['X-Garak-CSRF']=self.csrf
  c=http.client.HTTPConnection('127.0.0.1',self.port,timeout=7)
  c.request(method,path,json.dumps(payload,ensure_ascii=False).encode() if payload is not None else None,h)
  r=c.getresponse();data=r.read();status=r.status;headers=dict(r.getheaders());c.close()
  return status,json.loads(data) if data else {},headers
 def login(self):
  status,data,headers=self.request('POST','/api/auth/login',{'username':'admin','password':'V8Regression-Only_2026!'})
  self.assertEqual(status,200);self.cookie=headers['Set-Cookie'].split(';')[0];self.csrf=data['csrf']
 def q(self,sql,*params):
  with connect(self.path) as c:return c.execute(sql,params).fetchone()[0]
 def test_01_fractional_stock_rejected_and_preserved(self):
  self.login()
  for bad in [1.9,True,'2',None,-100001,100001]:
   self.assertEqual(self.request('POST','/api/admin/inventory/adjust',{'product_id':1,'delta':bad,'reason':'QA stock test'})[0],400)
  self.assertEqual(self.q('SELECT stock FROM products WHERE id=1'),20)
 def test_02_noninteger_product_id_rejected(self):
  self.login()
  for bad in [1.9,True,'1']:
   self.assertEqual(self.request('POST','/api/admin/inventory/adjust',{'product_id':bad,'delta':1,'reason':'QA stock test'})[0],400)
  self.assertEqual(self.q('SELECT stock FROM products WHERE id=1'),20)
 def test_03_merchant_suspended_hides_all_products(self):
  self.login();before=self.q("SELECT COUNT(*) FROM products WHERE merchant_id=1 AND status='published'")
  self.assertGreater(before,0)
  status,data,_=self.request('PATCH','/api/admin/merchants/1',{'status':'suspended'})
  self.assertEqual(status,200,data)
  self.assertEqual(self.q("SELECT COUNT(*) FROM products WHERE merchant_id=1 AND status='published'"),0)
  self.assertEqual(self.request('GET','/api/public/product/bangeo-hoe')[0],404)
  self.assertEqual(self.request('POST','/api/admin/orders/create',{'items':[{'slug':'bangeo-hoe','qty':1}]})[0],400)
  self.assertEqual(self.q('SELECT COUNT(*) FROM orders'),0)
 def test_04_merchant_reactivation_does_not_republish(self):
  self.login()
  self.assertEqual(self.request('PATCH','/api/admin/merchants/1',{'status':'suspended'})[0],200)
  self.assertEqual(self.request('PATCH','/api/admin/merchants/1',{'status':'active','verified':1})[0],200)
  self.assertEqual(self.request('GET','/api/public/product/bangeo-hoe')[0],404)
 def test_05_merchant_denied_hidden_in_catalog(self):
  self.login();self.request('PATCH','/api/admin/merchants/1',{'status':'rejected'})
  status,data,_=self.request('GET','/api/public/products')
  self.assertEqual(status,200);self.assertNotIn('bangeo-hoe',[p['slug'] for p in data['items']])
 def test_06_order_blocks_stopped_seller_even_if_published_row_legacy(self):
  self.login()
  with connect(self.path) as c:c.execute("UPDATE merchants SET status='suspended' WHERE id=1")
  self.assertEqual(self.request('POST','/api/admin/orders/create',{'items':[{'slug':'bangeo-hoe','qty':1}]})[0],400)
  self.assertEqual(self.request('GET','/api/public/product/bangeo-hoe')[0],404)
 def test_07_audit_never_stores_password_digest(self):
  self.login()
  status,u,_=self.request('POST','/api/admin/users/create',{'username':'editor8','role':'content'})
  self.assertEqual(status,201)
  with connect(self.path) as c:pw=c.execute('SELECT password_hash FROM users WHERE id=?',(u['id'],)).fetchone()[0]
  status,_,_=self.request('PATCH',f"/api/admin/users/{u['id']}",{'role':'support'})
  self.assertEqual(status,200)
  with connect(self.path) as c:
   saved='\n'.join(str(v) for row in c.execute("SELECT old_json,new_json FROM audit_logs WHERE target='users'") for v in row)
  self.assertNotIn(pw,saved);self.assertNotIn(u['one_time_password'],saved);self.assertIn('[REDACTED]',saved)
 def test_08_seller_contact_masked_in_audit(self):
  self.login();status,_,_=self.request('PATCH','/api/admin/merchants/1',{'contact':'merchant-private@example.invalid'})
  self.assertEqual(status,200)
  with connect(self.path) as c:s='\n'.join(str(v) for row in c.execute("SELECT old_json,new_json FROM audit_logs") for v in row)
  self.assertNotIn('merchant-private@example.invalid',s)
 def test_09_normal_inventory_adjustment(self):
  self.login();st,body,_=self.request('POST','/api/admin/inventory/adjust',{'product_id':1,'delta':-3,'reason':'verified QA count'})
  self.assertEqual(st,200);self.assertEqual(body['stock'],17)
 def test_10_normal_order_and_cancellation(self):
  self.login();st,order,_=self.request('POST','/api/admin/orders/create',{'items':[{'slug':'bangeo-hoe','qty':2}]})
  self.assertEqual(st,201,order)
  self.assertEqual(self.q('SELECT stock FROM products WHERE id=1'),18)
  self.assertEqual(self.request('POST',f"/api/admin/orders/{order['order_id']}/transition",{'status':'canceled'})[0],200)
  self.assertEqual(self.q('SELECT stock FROM products WHERE id=1'),20)
 def test_11_audit_redact_nested_values(self):
  from admin_core.server import redact_audit
  self.assertEqual(redact_audit({'address':{'street':'secrets'},'items':[{'api_key':'123','name':'public'}]})['items'][0]['api_key'],'[REDACTED]')
 def test_12_http_csrf_still_enforced(self):
  self.login();self.csrf='';self.assertEqual(self.request('PATCH','/api/admin/products/1',{'price':10000})[0],403)

if __name__=='__main__':unittest.main()
