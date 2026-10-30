"""Local synthetic concurrency validation, not production load testing."""
import tempfile,threading,time,os,sys,socket,http.client,json,statistics
from concurrent.futures import ThreadPoolExecutor,as_completed
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from admin_core.database import init_db,connect
from admin_core.server import Server
with tempfile.TemporaryDirectory() as tmp:
 db=Path(tmp)/'stress.sqlite3';os.environ['GARAK_BOOTSTRAP_PASSWORD']='ConcurrencyTestPassword_2026'
 con=init_db(db);con.close()
 server=Server(('127.0.0.1',0),db);port=server.server_address[1]
 t=threading.Thread(target=server.serve_forever,daemon=True);t.start()
 def request(method,path,data=None,headers=None):
  c=http.client.HTTPConnection('127.0.0.1',port,timeout=10)
  start=time.perf_counter();body=json.dumps(data).encode() if data is not None else None
  c.request(method,path,body=body,headers={'Content-Type':'application/json',**(headers or {})});r=c.getresponse();payload=r.read();elapsed=(time.perf_counter()-start)*1000
  out={'status':r.status,'data':json.loads(payload.decode()) if payload else None,'headers':dict(r.getheaders()),'ms':elapsed};c.close();return out
 login=request('POST','/api/auth/login',{'username':'admin','password':'ConcurrencyTestPassword_2026'});assert login['status']==200
 cookie=login['headers']['Set-Cookie'].split(';')[0];csrf=login['data']['csrf'];headers={'Cookie':cookie,'X-Garak-CSRF':csrf}
 def checkout(i):return request('POST','/api/admin/orders/create',{'items':[{'slug':'bangeo-hoe','qty':1}]},headers)
 with ThreadPoolExecutor(max_workers=14) as ex:
  resp=list(ex.map(checkout,range(50)))
 success=sum(x['status']==201 for x in resp);rejected=sum(x['status']==400 for x in resp)
 with connect(db) as con:
  stock=con.execute("SELECT stock FROM products WHERE slug='bangeo-hoe'").fetchone()[0]
  orders=con.execute('SELECT COUNT(*) FROM orders').fetchone()[0]
 assert success==20 and rejected==30 and stock==0 and orders==20,(success,rejected,stock,orders)
 lat=[]
 with ThreadPoolExecutor(max_workers=10) as ex:
  for x in ex.map(lambda i:request('GET','/api/public/products'),range(100)):
   assert x['status']==200;lat.append(x['ms'])
 output={'mode':'LOCAL_SYNTHETIC','simultaneous_checkout_requests':50,'successful_order_reservations':success,'rejected_out_of_stock':rejected,'final_stock':stock,'orders':orders,'public_read_requests':100,'public_read_p50_ms':round(statistics.median(lat),2),'public_read_p95_ms':round(sorted(lat)[94],2),'passed':True,'note':'Single local machine SQLite/Python. Not representative of production network or Neon.'}
 (ROOT/'docs'/'QA_CONCURRENCY.json').write_text(json.dumps(output,ensure_ascii=False,indent=2),encoding='utf-8')
 print(json.dumps(output,ensure_ascii=False,indent=2));server.shutdown();server.server_close()
