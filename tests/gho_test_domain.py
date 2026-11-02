import copy, sys, tempfile, unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'backend'))
import domain

class DomainTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory()
  self.db_path=Path(self.tmp.name)/'demo.sqlite'
  domain.init_db(self.db_path)
  self.db=domain.db_connect(self.db_path)
 def tearDown(self):self.db.close();self.tmp.cleanup()
 def sample(self):return {'lines':[{'id':'g1','qty':2,'proc':''},{'id':'g2','qty':1,'proc':''}],'coupon_id':'marketday'}
 def create(self,key='mytestidempotency111',data=None):return domain.create_orders(self.db,data or self.sample(),key)
 def assertErr(self,fn,status):
  with self.assertRaises(domain.DomainError) as cm:fn()
  self.assertEqual(cm.exception.status,status)
 def test_seed(self):
  self.assertEqual(len(domain.markets(self.db)),5)
  self.assertEqual(len(domain.products(self.db)),17)
 def test_market_split_and_cross_market_coupon(self):
  data={'lines':[{'id':'g1','qty':1},{'id':'n1','qty':1},{'id':'r1','qty':1}],'coupon_id':'fish'}
  result=self.create('market_split_123456',data)
  self.assertEqual({x['market_id'] for x in result['orders']},{'garak','noryang','region'})
  self.assertTrue(all(o['discount']==0 for o in result['orders']))
  self.assertEqual(len(set(x['checkout_id'] for x in result['orders'])),1)
 def test_server_prices_cannot_be_overridden(self):
  data=self.sample();data['lines'][0]['price']=1
  result=self.create('server_prices_123',data)
  self.assertEqual(result['orders'][0]['subtotal'],49700)
 def test_idempotent_same_body(self):
  data=self.sample();a=self.create('duplicate_req_123',data)
  stock=self.db.execute('SELECT stock FROM products WHERE id="g1"').fetchone()[0]
  b=self.create('duplicate_req_123',copy.deepcopy(data))
  self.assertEqual(a,b)
  self.assertEqual(self.db.execute('SELECT stock FROM products WHERE id="g1"').fetchone()[0],stock)
  self.assertEqual(self.db.execute('SELECT count(*) FROM orders').fetchone()[0],1)
 def test_idempotent_reject_different_body(self):
  self.create('duplicate_other_123')
  self.assertErr(lambda:self.create('duplicate_other_123',{'lines':[{'id':'g1','qty':1}]}),409)
 def test_atomic_stock_insufficiency(self):
  before=self.db.execute('SELECT stock FROM products WHERE id="g2"').fetchone()[0]
  self.assertErr(lambda:self.create('stock_short_12345',{'lines':[{'id':'g1','qty':1},{'id':'g2','qty':99}]}),409)
  self.assertEqual(self.db.execute('SELECT stock FROM products WHERE id="g1"').fetchone()[0],30)
  self.assertEqual(self.db.execute('SELECT stock FROM products WHERE id="g2"').fetchone()[0],before)
 def test_processing_only_supported(self):
  self.assertErr(lambda:self.create('sliced_unsupported_123',{'lines':[{'id':'g1','qty':1,'proc':'sliced'}]}),409)
  x=self.create('sliced_supported_123',{'lines':[{'id':'n1','qty':1,'proc':'sliced'}]})
  self.assertEqual(x['orders'][0]['subtotal'],32900)
 def test_coupon_per_market(self):
  x=self.create('market_coupon_12345',{'lines':[{'id':'g1','qty':3},{'id':'n1','qty':2}],'coupon_id':'marketday'})
  self.assertEqual({o['market_id']:o['discount'] for o in x['orders']},{'garak':2970,'noryang':0})
 def test_all_merchant_workflow(self):
  x=self.create();oid=x['orders'][0]['id']
  stores=domain.get_orders(self.db)[0]['fulfillment']
  self.assertErr(lambda:domain.hub_collect(self.db,oid,'hub'),409)
  self.assertErr(lambda:domain.merchant_status(self.db,oid,stores[0]['merchant_id'],'accepted','merchant'),409)
  domain.mock_pay(self.db,oid,'customer',x['customer_action_token'])
  for f in stores:
   domain.merchant_status(self.db,oid,f['merchant_id'],'accepted','merchant')
   domain.merchant_status(self.db,oid,f['merchant_id'],'ready','merchant')
  job=domain.hub_collect(self.db,oid,'hub')
  self.assertErr(lambda:domain.dispatch_update(self.db,job['job_id'],'pick_up','','rider'),409)
  domain.dispatch_update(self.db,job['job_id'],'assign','데모 기사','hub')
  domain.dispatch_update(self.db,job['job_id'],'pick_up','','rider')
  domain.dispatch_update(self.db,job['job_id'],'deliver','','rider')
  self.assertEqual(domain.get_orders(self.db)[0]['status'],'delivered')
 def test_role_restriction(self):
  x=self.create();oid=x['orders'][0]['id']
  self.assertErr(lambda:domain.hub_collect(self.db,oid,'customer'),403)
  self.assertErr(lambda:domain.approve_merchant(self.db,'fake','merchant'),403)
  self.assertErr(lambda:domain.update_stock(self.db,'other','g1',1,'merchant'),403)
 def test_cancel_restores_stock(self):
  x=self.create();oid=x['orders'][0]['id']
  self.assertEqual(self.db.execute('SELECT stock FROM products WHERE id="g1"').fetchone()[0],28)
  domain.cancel_order(self.db,oid,'customer',x['customer_action_token'])
  self.assertEqual(self.db.execute('SELECT stock FROM products WHERE id="g1"').fetchone()[0],30)
  self.assertErr(lambda:domain.cancel_order(self.db,oid,'customer',x['customer_action_token']),409)
 def test_onboard_requires_approval(self):
  merchant=domain.apply_merchant(self.db,{'market_id':'dong','name':'시연 원단 도매상'},'merchant')
  self.assertEqual(merchant['status'],'pending')
  x=domain.approve_merchant(self.db,merchant['id'],'admin')
  self.assertEqual(x['status'],'approved')
  self.assertErr(lambda:domain.approve_merchant(self.db,merchant['id'],'admin'),409)
 def test_duplicate_variants_accumulate_stock(self):
  self.assertErr(lambda:self.create('duplicates_12345',{'lines':[{'id':'g3','qty':24,'proc':''},{'id':'g3','qty':14,'proc':'sliced'}]}),409)
 def test_refuse_invalid_quantities(self):
  for q in (-1,0,1.3,True,'1',100):
   self.assertErr(lambda:self.create('bad_qty_'+str(q)+'__',{'lines':[{'id':'g1','qty':q}]}),400)

if __name__=='__main__':unittest.main()
