import http.client, tempfile, threading, unittest, json, os
from pathlib import Path
from admin_core.database import init_db,connect
from admin_core.server import Server

class BetaTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.temp=tempfile.TemporaryDirectory();cls.db=Path(cls.temp.name)/'beta.sqlite3'
  cls.server=Server(('127.0.0.1',0),cls.db);cls.port=cls.server.server_address[1]
  cls.thread=threading.Thread(target=cls.server.serve_forever,daemon=True);cls.thread.start()
 @classmethod
 def tearDownClass(cls):cls.server.shutdown();cls.server.server_close();cls.temp.cleanup()
 def setUp(self):
  for p in self.db.parent.glob('*'):p.unlink(missing_ok=True)
  os.environ['GARAK_BOOTSTRAP_PASSWORD']='TestingOnly_Admin_2026!'
  with init_db(self.db):pass
  self.cookie='';self.csrf=''
 def req(self,method,path,body=None,cookie=None,csrf=None):
  conn=http.client.HTTPConnection('127.0.0.1',self.port,timeout=5)
  headers={'Content-Type':'application/json','Host':f'127.0.0.1:{self.port}'}
  if cookie or self.cookie:headers['Cookie']=cookie or self.cookie
  if csrf or self.csrf:headers['X-Garak-CSRF']=csrf or self.csrf
  data=json.dumps(body,ensure_ascii=False).encode() if body is not None else None
  conn.request(method,path,body=data,headers=headers);res=conn.getresponse();payload=res.read();out=(res.status,json.loads(payload.decode()) if res.getheader('Content-Type','').startswith('application/json') else payload,dict(res.getheaders()));conn.close();return out
 def login(self,username='admin',password='TestingOnly_Admin_2026!'):
  status,data,headers=self.req('POST','/api/auth/login',{'username':username,'password':password})
  self.assertEqual(status,200,data)
  self.cookie='garak_admin_session='+headers['Set-Cookie'].split(';')[0].split('=',1)[1]
  self.csrf=data['csrf']
 def create_order(self,slug='bangeo-hoe',qty=2):
  self.login();return self.req('POST','/api/admin/orders/create',{'items':[{'slug':slug,'qty':qty}]})
 def test_01_health(self):
  st,d,_=self.req('GET','/api/health');self.assertEqual(st,200);self.assertEqual(d['payments'],'simulation_only')
 def test_02_seed_content(self):
  with connect(self.db) as c:self.assertEqual(c.execute('select count(*) from products').fetchone()[0],44);self.assertEqual(c.execute('select count(*) from recipes').fetchone()[0],132)
 def test_03_site(self):
  for p in ['/index.html','/admin/','/recipes/index.html','/product/bangeo-hoe.html']:
   st,d,h=self.req('GET',p);self.assertEqual(st,200,p);self.assertIn(b'<!',d[:100].lower())
 def test_04_unauthorized(self):self.assertEqual(self.req('GET','/api/admin/products')[0],401)
 def test_05_invalid_login(self):self.assertEqual(self.req('POST','/api/auth/login',{'username':'admin','password':'wrong'})[0],401)
 def test_06_login_and_me(self):
  self.login();st,d,_=self.req('GET','/api/auth/me');self.assertTrue(d['authenticated']);self.assertEqual(d['user']['role'],'superadmin')
 def test_07_csrf_required(self):
  self.login();self.csrf='';self.assertEqual(self.req('PATCH','/api/admin/products/1',{'price':100})[0],403)
 def test_08_overview(self):
  self.login();_,d,_=self.req('GET','/api/admin/overview');self.assertEqual(d['kpis']['products'],44);self.assertEqual(d['kpis']['recipes'],132)
 def test_09_products_patch(self):
  self.login();st,d,_=self.req('PATCH','/api/admin/products/1',{'price':60000});self.assertEqual(st,200);self.assertEqual(d['item']['price'],60000)
 def test_10_stock_direct_blocked(self):
  self.login();self.assertEqual(self.req('PATCH','/api/admin/products/1',{'stock':1000})[0],400)
 def test_11_stock_adjust(self):
  self.login();st,d,_=self.req('POST','/api/admin/inventory/adjust',{'product_id':1,'delta':-3,'reason':'inventory count'});self.assertEqual(st,200);self.assertEqual(d['stock'],17)
 def test_12_stock_insufficient(self):
  self.login();self.assertEqual(self.req('POST','/api/admin/inventory/adjust',{'product_id':1,'delta':-50,'reason':'inventory count'})[0],400)
  with connect(self.db) as c:self.assertEqual(c.execute('select stock from products where id=1').fetchone()[0],20)
 def test_13_order_reserves(self):
  st,d,_=self.create_order();self.assertEqual(st,201);self.assertEqual(d['payment_mode'],'simulation');self.assertEqual(d['subtotal'],110000)
  with connect(self.db) as c:self.assertEqual(c.execute('select stock from products where slug=?',('bangeo-hoe',)).fetchone()[0],18)
 def test_14_order_out_of_stock(self):
  self.login();self.assertEqual(self.req('POST','/api/admin/orders/create',{'items':[{'slug':'bangeo-hoe','qty':50}]})[0],400)
 def test_15_order_state_invalid(self):
  _,d,_=self.create_order();self.assertEqual(self.req('POST',f"/api/admin/orders/{d['order_id']}/transition",{'status':'delivered'})[0],400)
 def test_16_cancel_restock(self):
  _,d,_=self.create_order();st,x,_=self.req('POST',f"/api/admin/orders/{d['order_id']}/transition",{'status':'canceled'});self.assertEqual(st,200)
  with connect(self.db) as c:
   self.assertEqual(c.execute('select stock from products where slug=?',('bangeo-hoe',)).fetchone()[0],20)
   self.assertEqual(c.execute('select count(*) from inventory_moves').fetchone()[0],2)
 def test_17_shipping_requires_tracking(self):
  _,d,_=self.create_order();id=d['order_id'];self.req('POST',f'/api/admin/orders/{id}/transition',{'status':'paid_test'});self.req('POST',f'/api/admin/orders/{id}/transition',{'status':'processing'});self.assertEqual(self.req('POST',f'/api/admin/orders/{id}/transition',{'status':'shipped'})[0],400)
 def delivered(self):
  _,d,_=self.create_order();id=d['order_id'];self.req('POST',f'/api/admin/orders/{id}/transition',{'status':'paid_test'});self.req('POST',f'/api/admin/orders/{id}/transition',{'status':'processing'})
  with connect(self.db) as c:ship=c.execute('select id from shipments where order_id=?',(id,)).fetchone()[0]
  self.req('PATCH',f'/api/admin/shipments/{ship}',{'carrier':'베타배송사','tracking':'TEST-00001234'})
  self.assertEqual(self.req('POST',f'/api/admin/orders/{id}/transition',{'status':'shipped'})[0],200)
  self.assertEqual(self.req('POST',f'/api/admin/orders/{id}/transition',{'status':'delivered'})[0],200)
  return id
 def test_18_delivery(self):
  id=self.delivered();self.assertTrue(id>0)
 def test_19_settlement(self):
  self.delivered();st,d,_=self.req('POST','/api/admin/settlements/generate',{});self.assertEqual(st,200);self.assertEqual(d['new_settlements'],1)
  st,d,_=self.req('GET','/api/admin/settlements');self.assertEqual(d['count'],1);self.assertEqual(d['items'][0]['gross'],110000);self.assertEqual(d['items'][0]['fee'],8800)
 def test_20_settlement_idempotence(self):
  self.delivered();self.req('POST','/api/admin/settlements/generate',{});self.assertEqual(self.req('POST','/api/admin/settlements/generate',{})[1]['new_settlements'],0)
 def test_21_unverified_merchant_block(self):
  self.login();self.assertEqual(self.req('PATCH','/api/admin/merchants/1',{'status':'active'})[0],400)
 def test_22_unverified_posts_block(self):
  self.login();self.assertEqual(self.req('PATCH','/api/admin/posts/1',{'status':'approved'})[0],400)
 def test_23_verified_posts(self):
  self.login();st,d,_=self.req('PATCH','/api/admin/posts/1',{'status':'approved','verified':1});self.assertEqual(st,200)
  self.assertEqual(len(self.req('GET','/api/public/posts')[1]['items']),1)
 def test_24_unreviewed_recipe_block(self):
  self.login();self.assertEqual(self.req('PATCH','/api/admin/recipes/1',{'status':'published'})[0],400)
 def test_25_reviewed_recipe(self):
  self.login();st,d,_=self.req('PATCH','/api/admin/recipes/1',{'status':'published','reviewed':1});self.assertEqual(st,200);self.assertEqual(len(self.req('GET','/api/public/recipes')[1]['items']),1)
 def test_26_integration_no_fake_connected(self):
  self.login();self.assertEqual(self.req('PATCH','/api/admin/integrations/1',{'status':'connected'})[0],400)
 def test_27_roles(self):
  self.login();st,d,_=self.req('POST','/api/admin/users/create',{'username':'chef_editor','role':'content'});self.assertEqual(st,201)
  self.cookie='';self.csrf='';self.login('chef_editor',d['one_time_password']);self.assertEqual(self.req('POST','/api/admin/orders/create',{'items':[{'slug':'bangeo-hoe','qty':1}]})[0],403)
  self.assertEqual(self.req('GET','/api/admin/recipes')[0],200)
 def test_28_user_audit(self):
  self.login();self.req('PATCH','/api/admin/products/1',{'price':45000});st,d,_=self.req('GET','/api/admin/audit_logs');self.assertGreaterEqual(d['count'],2)
 def test_29_report_from_db(self):
  self.create_order();st,d,_=self.req('GET','/api/admin/reports');self.assertEqual(st,200);self.assertEqual(d['daily_sales'][0]['gross'],110000)
 def test_30_public_stock(self):
  self.login();self.req('POST','/api/admin/inventory/adjust',{'product_id':1,'delta':-4,'reason':'stock adjustment'});
  st,d,_=self.req('GET','/api/public/product/bangeo-hoe');self.assertEqual(d['product']['stock'],16)
 def test_31_logout(self):
  self.login();self.assertEqual(self.req('POST','/api/auth/logout',{})[0],200);self.assertEqual(self.req('GET','/api/admin/products')[0],401)
 def test_32_change_password(self):
  self.login();st,d,_=self.req('POST','/api/auth/password',{'current_password':'TestingOnly_Admin_2026!','new_password':'Another_Strong_Admin_Pass_2026'});self.assertEqual(st,200)
  self.cookie='';self.csrf='';self.login('admin','Another_Strong_Admin_Pass_2026')
 def test_33_sql_injection_search_safe(self):
  self.login();st,d,_=self.req('GET',"/api/admin/products?q=%27%20OR%201%3D1%20--");self.assertEqual(st,200);self.assertEqual(d['count'],0)
 def test_34_reject_product_negative_price(self):
  self.login();self.assertEqual(self.req('PATCH','/api/admin/products/1',{'price':-100})[0],400)
 def test_35_create_post_and_public_moderation(self):
  self.login();st,d,_=self.req('POST','/api/admin/posts',{'category':'merchants','organization':'테스트 업체','title':'상인 테스트 소식','body':'이 게시물은 승인 전 비공개입니다.'});self.assertEqual(st,201);self.assertEqual(len(self.req('GET','/api/public/posts')[1]['items']),0)
 def test_36_strict_origin(self):
  self.login();conn=http.client.HTTPConnection('127.0.0.1',self.port);headers={'Content-Type':'application/json','Cookie':self.cookie,'X-Garak-CSRF':self.csrf,'Origin':'https://evil.example'};conn.request('PATCH','/api/admin/products/1','{"price":100}',headers);resp=conn.getresponse();self.assertEqual(resp.status,403);resp.read();conn.close()
 def test_37_session_hash_db(self):
  self.login();
  with connect(self.db) as c:
   raw=c.execute('select id_hash from sessions').fetchone()[0];self.assertEqual(len(raw),64);self.assertNotIn('garak_admin_session',raw)
 def test_38_demo_report_no_real(self):
  self.login();d=self.req('GET','/api/admin/reports')[1];self.assertTrue(d['synthetic'])
 def test_39_status_double_cancel_blocked(self):
  _,d,_=self.create_order();id=d['order_id'];self.req('POST',f'/api/admin/orders/{id}/transition',{'status':'canceled'});self.assertEqual(self.req('POST',f'/api/admin/orders/{id}/transition',{'status':'canceled'})[0],400)
 def test_40_role_must_not_self_promote(self):
  self.login();self.assertEqual(self.req('PATCH','/api/admin/users/1',{'role':'support'})[0],400)

 def test_41_create_product_as_draft(self):
  self.login();st,d,_=self.req('POST','/api/admin/products',{'slug':'test-fish-pack','name':'데모 조기 생선 세트','category':'seafood','merchant_id':1,'price':23000,'stock':5});self.assertEqual(st,201);self.assertEqual(d['status'],'draft')
  self.assertEqual(self.req('GET','/api/public/product/test-fish-pack')[0],404)
 def test_42_create_recipe_as_draft(self):
  self.login();st,d,_=self.req('POST','/api/admin/recipes',{'title':'데모 조기 간장조림','category':'수산','main_ingredient':'조기','product_slug':'bangeo-hoe','minutes':20});self.assertEqual(st,201)
  self.assertEqual(d['status'],'draft')
 def test_43_order_details(self):
  _,d,_=self.create_order();st,res,_=self.req('GET',f"/api/admin/orders/{d['order_id']}/details");self.assertEqual(st,200);self.assertEqual(res['items'][0]['qty'],2)
 def test_44_public_event_reporting(self):
  st,d,_=self.req('POST','/api/public/events',{'event':'view_recipe','path':'/recipes/recipe-001.html'});self.assertEqual(st,202)
  self.login();rep=self.req('GET','/api/admin/reports')[1];self.assertTrue(any(x['event_name']=='view_recipe' for x in rep['traffic']))
 def test_45_public_event_rejects_pii_in_path(self):
  self.assertEqual(self.req('POST','/api/public/events',{'event':'page_view','path':'user@gmail.com'})[0],400)

if __name__=='__main__':unittest.main(verbosity=2)
