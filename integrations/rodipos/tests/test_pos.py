import json, tempfile, threading, unittest, urllib.error, urllib.request
from pathlib import Path
from server import init_db,db_conn,create_order,settle_demo,status_order,print_jobs,update_print,serve,confirm_payment

class RodiPosTests(unittest.TestCase):
    def setUp(self):
        self.dir=tempfile.TemporaryDirectory();self.path=Path(self.dir.name)/'pos.sqlite3';init_db(self.path)
    def tearDown(self):self.dir.cleanup()
    def test_new_order_total_and_items(self):
        v=create_order(self.path,[{'id':'flat-white','qty':2},{'id':'meat-pie','qty':1}], 't_'+'a'*20)
        self.assertEqual(v['total'],16400);self.assertEqual(v['status'],'PENDING_PAYMENT')
        self.assertEqual(len(v['items']),2)
    def test_retries_idempotent(self):
        x=[{'id':'long-black','qty':1}];first=create_order(self.path,x,'t_'+'b'*20)
        self.assertEqual(first['id'],create_order(self.path,x,'t_'+'b'*20)['id'])
        with self.assertRaises(ValueError):create_order(self.path,[{'id':'long-black','qty':2}],'t_'+'b'*20)
        with db_conn(self.path) as db:self.assertEqual(db.execute('SELECT COUNT(*) FROM orders').fetchone()[0],1)
    def test_reject_wrong_amount_or_products(self):
        with self.assertRaises(ValueError):create_order(self.path,[{'id':'unknown','qty':1}],'t_'+'c'*20)
        with self.assertRaises(ValueError):create_order(self.path,[{'id':'flat-white','qty':True}],'t_'+'d'*20)
        with self.assertRaises(ValueError):create_order(self.path,[{'id':'flat-white','qty':1},{'id':'flat-white','qty':1}],'t_'+'d'*20)
    def test_paid_queue_and_staff_status(self):
        a=create_order(self.path,[{'id':'flat-white','qty':1}],'t_'+'e'*20)
        b=create_order(self.path,[{'id':'meat-pie','qty':1}],'t_'+'f'*20)
        v=settle_demo(self.path,a['id']);self.assertEqual(v['queue_no'],1)
        self.assertEqual(settle_demo(self.path,a['id'])['queue_no'],1)
        self.assertEqual(settle_demo(self.path,b['id'])['queue_no'],2)
        for step in ('MAKING','READY','COLLECTED'):
            v=status_order(self.path,a['id'],step);self.assertEqual(v['status'],step)
        with self.assertRaises(ValueError):status_order(self.path,a['id'],'PAID')
    def test_concurrent_number_unique(self):
        orders=[create_order(self.path,[{'id':'flat-white','qty':1}], 't_'+str(i).zfill(20)) for i in range(12)]
        result=[]
        def work(o):result.append(settle_demo(self.path,o['id'])['queue_no'])
        threads=[threading.Thread(target=work,args=(o,)) for o in orders]
        [t.start() for t in threads];[t.join() for t in threads]
        self.assertEqual(sorted(result),list(range(1,13)))
    def test_print_retry_and_confirmation(self):
        o=create_order(self.path,[{'id':'flat-white','qty':1}],'t_'+'h'*20);settle_demo(self.path,o['id'])
        job=print_jobs(self.path)[0];self.assertEqual(job['queue_no'],1)
        update_print(self.path,job['id'],False,'paper out');self.assertEqual(print_jobs(self.path)[0]['attempts'],1)
        update_print(self.path,job['id'],True)
        self.assertEqual(print_jobs(self.path),[])
    def test_no_unverified_bridge_success(self):
        o=create_order(self.path,[{'id':'flat-white','qty':1}],'t_'+'i'*20)
        with self.assertRaises(PermissionError):confirm_payment(self.path,o['id'],{'type':'SUCCESS','response':{'paymentMethod':'CARD'}})
        with db_conn(self.path) as db:self.assertEqual(db.execute('SELECT status FROM orders').fetchone()[0],'PENDING_PAYMENT')
    def test_option_variants_and_idempotent_cart(self):
        key='t_'+'z'*20
        v=create_order(self.path,[{'id':'flat-white','qty':1,'option':'HOT'},{'id':'flat-white','qty':2,'option':'ICED'}],key)
        self.assertEqual(v['total'],14400)
        self.assertEqual({x['drink_option'] for x in v['items']},{'HOT','ICED'})
        v2=create_order(self.path,[{'id':'flat-white','qty':1,'option':'HOT'},{'id':'flat-white','qty':2,'option':'ICED'}],key)
        self.assertEqual(v2['id'],v['id'])
        with self.assertRaises(ValueError):create_order(self.path,[{'id':'meat-pie','qty':1,'option':'HOT'}],'t_'+'v'*20)
    def test_timeout_not_paid(self):
        o=create_order(self.path,[{'id':'flat-white','qty':1}],'t_'+'j'*20)
        v=confirm_payment(self.path,o['id'],{'type':'TIMEOUT'})
        self.assertEqual(v['status'],'PENDING_PAYMENT');self.assertIsNone(v['queue_no'])

class HttpTests(unittest.TestCase):
    def setUp(self):
        self.dir=tempfile.TemporaryDirectory();self.server=serve('127.0.0.1',0,Path(self.dir.name)/'pos.sqlite3',staff_token='test-staff-token',bridge_token='test-bridge-token')
        self.thread=threading.Thread(target=self.server.serve_forever,daemon=True);self.thread.start()
    def tearDown(self):
        self.server.shutdown();self.server.server_close();self.thread.join(timeout=2);self.dir.cleanup()
    def req(self,path,method='GET',data=None,headers=None):
        body=json.dumps(data).encode() if data is not None else None
        req=urllib.request.Request(f'http://127.0.0.1:{self.server.server_port}{path}',body,method=method,headers={'Content-Type':'application/json',**(headers or {})})
        try:
            with urllib.request.urlopen(req) as r:
                payload=r.read();return r.status, json.loads(payload) if path.startswith('/api/') else payload
        except urllib.error.HTTPError as e:
            return e.code,json.loads(e.read())
    def test_rest_checkout_staff_authorization(self):
        code,p=self.req('/api/orders','POST',{'items':[{'id':'flat-white','qty':1}]},{'Idempotency-Key':'idem_'+'x'*20})
        self.assertEqual(code,201)
        self.assertEqual(self.req('/api/staff/orders')[0],401)
        self.assertEqual(self.req('/api/bridge/pending')[0],401)
        self.assertEqual(self.req('/api/demo/orders/'+p['id']+'/pay','POST',{})[0],200)
        code,r=self.req('/api/staff/orders',headers={'Authorization':'Bearer test-staff-token'})
        self.assertEqual(code,200);self.assertEqual(len(r['orders']),1)
        code,r=self.req(f"/api/staff/orders/{p['id']}/status",'POST',{'status':'READY'},{'Authorization':'Bearer test-staff-token'})
        self.assertEqual(code,400)
        code,r=self.req(f"/api/staff/orders/{p['id']}/status",'POST',{'status':'MAKING'},{'Authorization':'Bearer test-staff-token'})
        self.assertEqual(code,200)
    def test_ui_routes_and_refuse_remote_demo(self):
        self.assertEqual(self.req('/')[0],200)
        self.assertEqual(self.req('/staff.html')[0],200)
        self.assertEqual(self.req('/assets.css')[0],200)
        self.assertEqual(self.req('/receipt.html')[0],200)
        self.assertEqual(self.req('/receipt.js')[0],200)
        self.assertEqual(self.req('/api/health')[1]['mode'],'SIMULATION_ONLY')

if __name__=='__main__': unittest.main()
