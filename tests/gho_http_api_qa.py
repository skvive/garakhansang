"""True HTTP API regression using urllib to localhost, independent of Chromium."""
import json,subprocess,sys,tempfile,time,urllib.request,urllib.error,socket,os
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
with tempfile.TemporaryDirectory() as td:
 sock=socket.socket();sock.bind(('127.0.0.1',0));port=sock.getsockname()[1];sock.close()
 admin_token='test_local_dev_admin_token_20261102_at_least_24_chars'
 env=os.environ.copy();env['GHO_DEMO_ADMIN_TOKEN']=admin_token
 process=subprocess.Popen([sys.executable,str(ROOT/'backend/server.py'),'--port',str(port),'--db',td+'/api.sqlite'],stdout=subprocess.DEVNULL,stderr=subprocess.PIPE,env=env)
 base=f'http://127.0.0.1:{port}/order/api/v1'
 def call(path,method='GET',body=None,headers=None):
  data=json.dumps(body).encode() if body is not None else None
  req=urllib.request.Request(base+path,data=data,headers=({'Content-Type':'application/json'} if body is not None else {}) | (headers or {}),method=method)
  try:
   with urllib.request.urlopen(req,timeout=4) as r:return r.status,json.loads(r.read())
  except urllib.error.HTTPError as err:return err.code,json.loads(err.read())
 try:
  for _ in range(40):
   try:code,health=call('/health');break
   except Exception:time.sleep(.1)
  assert code==200 and health['mode']=='demo'
  code,markets=call('/markets');assert code==200 and len(markets)==5
  payload={'lines':[{'id':'g1','qty':1},{'id':'n1','qty':1}],'coupon_id':''}
  h={'Idempotency-Key':'http-integration-test123'}
  code,first=call('/orders','POST',payload,h);assert code==201,len(first['orders'])
  code,again=call('/orders','POST',payload,h);assert code==201 and again==first
  code,conflict=call('/orders','POST',{'lines':[{'id':'g1','qty':2}]},h);assert code==409
  order=first['orders'][0]['id']
  code,paid=call(f'/orders/{order}/mock-pay','POST',{},headers={'Authorization':'Bearer '+first['customer_action_token']});assert code==200 and paid['status']=='paid_mock'
  code,rs=call('/orders',headers={'Authorization':'Bearer '+admin_token});assert code==200 and len(rs)==2
  code,forbidden=call('/dashboard',headers={'X-Demo-Role':'admin'});assert code==403
  code,wrong=call('/orders/'+first['orders'][1]['id']+'/mock-pay','POST',{},headers={'Authorization':'Bearer not-the-right-token'})
  assert code==403
  code,csrf=call('/merchants/apply','POST',{'market_id':'garak','name':'위조 요청'},headers={'Origin':'https://hostile.invalid','Authorization':'Bearer '+admin_token})
  assert code==403
  print('HTTP API TESTS PASSED: health, market seed, multi-market split, idempotency, conflict, mock payment, list, role restriction, checkout ownership, CSRF origin (10 checks)')
 finally:
  process.terminate()
  try:process.wait(timeout=3)
  except subprocess.TimeoutExpired:process.kill()
