"""Full synthetic business flow over real loopback HTTP, destructive only to ephemeral temp SQLite."""
import subprocess,sys,os,tempfile,socket,time,http.client,json,hashlib
from pathlib import Path
root=Path(__file__).resolve().parents[1];out=root/'docs'/'QA_V8_BUSINESS_FLOW.json'
steps=[]
with tempfile.TemporaryDirectory() as td:
 db=Path(td)/'scenario.sqlite3';port=8185
 env={**os.environ,'GARAK_ADMIN_DB':str(db),'GARAK_BOOTSTRAP_PASSWORD':'BetaAdminWorkflow_Only_2026!'}
 sp=subprocess.Popen([sys.executable,'-m','admin_core.server','--db',str(db),'--port',str(port)],cwd=root,env=env,stdout=subprocess.DEVNULL,stderr=subprocess.STDOUT)
 cookie='';csrf=''
 def req(method,path,data=None):
  global cookie,csrf
  h={'Content-Type':'application/json'}
  if cookie:h['Cookie']=cookie
  if csrf:h['X-Garak-CSRF']=csrf
  c=http.client.HTTPConnection('127.0.0.1',port,timeout=8)
  c.request(method,path,json.dumps(data,ensure_ascii=False).encode('utf-8') if data is not None else None,h)
  r=c.getresponse();raw=r.read();headers=dict(r.getheaders());status=r.status;c.close()
  if headers.get('Set-Cookie'):cookie=headers['Set-Cookie'].split(';')[0]
  return status,json.loads(raw) if raw else {},headers
 def check(name,cond,detail=''):
  steps.append({'step':name,'passed':bool(cond),'detail':str(detail)[:200]})
  if not cond:raise AssertionError(name+': '+str(detail)[:300])
 try:
  for _ in range(80):
   try:s=socket.create_connection(('127.0.0.1',port),timeout=.3);s.close();break
   except OSError:time.sleep(.15)
  check('health_endpoint',req('GET','/api/health')[1].get('mode')=='LOCAL_BETA')
  st,d,h=req('POST','/api/auth/login',{'username':'admin','password':'BetaAdminWorkflow_Only_2026!'})
  check('login_admin',st==200);csrf=d['csrf']
  for module in ['overview','reports','products','inventory_moves','orders','shipments','settlements','merchants','recipes','creators','posts','campaigns','customers','tickets','integrations','users','audit_logs']:
   st,d,_=req('GET','/api/admin/'+module)
   check('module_'+module,st==200,st)
  st,d,_=req('PATCH','/api/admin/merchants/1',{'verified':1,'status':'active'})
  check('merchant_verified_activated_in_simulation',st==200)
  st,d,_=req('POST','/api/admin/products',{'slug':'qa-fresh-fish8','name':'실검증 생선 세트','category':'seafood','merchant_id':1,'price':18300,'stock':6})
  check('new_product_draft',st==201 and d.get('status')=='draft');pid=d['id']
  check('draft_not_public',req('GET','/api/public/product/qa-fresh-fish8')[0]==404)
  check('publish_product',req('PATCH',f'/api/admin/products/{pid}',{'status':'published'})[0]==200)
  check('new_product_public',req('GET','/api/public/product/qa-fresh-fish8')[0]==200)
  st,d,_=req('POST','/api/admin/inventory/adjust',{'product_id':pid,'delta':-1,'reason':'QA stock audit'});check('inventory_adjust',st==200 and d['stock']==5)
  st,d,_=req('POST','/api/admin/orders/create',{'items':[{'slug':'qa-fresh-fish8','qty':2}]})
  check('order_created',st==201 and d.get('subtotal')==36600);oid=d['order_id']
  check('reservation_stock_3',req('GET','/api/public/product/qa-fresh-fish8')[1]['product']['stock']==3)
  check('reject_early_delivery',req('POST',f'/api/admin/orders/{oid}/transition',{'status':'delivered'})[0]==400)
  check('mark_paid_simulated',req('POST',f'/api/admin/orders/{oid}/transition',{'status':'paid_test'})[0]==200)
  check('order_processing',req('POST',f'/api/admin/orders/{oid}/transition',{'status':'processing'})[0]==200)
  st,d,_=req('GET',f'/api/admin/orders/{oid}/details');check('order_details',st==200 and d['items'][0]['qty']==2);sid=d['order']['id']
  st,d,_=req('GET','/api/admin/shipments');shipment_id=next(x['id'] for x in d['items'] if x['order_id']==oid)
  check('shipment_tracking_set',req('PATCH',f'/api/admin/shipments/{shipment_id}',{'carrier':'QA Carrier','tracking':'QA-TRACK-0001'})[0]==200)
  check('order_shipped',req('POST',f'/api/admin/orders/{oid}/transition',{'status':'shipped'})[0]==200)
  check('order_delivered',req('POST',f'/api/admin/orders/{oid}/transition',{'status':'delivered'})[0]==200)
  st,d,_=req('POST','/api/admin/settlements/generate',{});check('settlement_generated',st==200 and d['new_settlements']==1)
  st,d,_=req('GET','/api/admin/settlements');sl=next(x for x in d['items'] if x['order_id']==oid)
  check('settlement_8pct',sl['gross']==36600 and sl['fee']==2928 and sl['payout']==33672)
  check('settlement_idempotent',req('POST','/api/admin/settlements/generate',{})[1]['new_settlements']==0)
  st,d,_=req('POST','/api/admin/recipes',{'title':'QA 생선 맑은탕','category':'수산','main_ingredient':'생선','product_slug':'qa-fresh-fish8','minutes':25})
  check('recipe_draft',st==201 and d['status']=='draft');rid=d['id']
  check('recipe_review_then_publish',req('PATCH',f'/api/admin/recipes/{rid}',{'reviewed':1,'status':'published'})[0]==200)
  check('approved_recipe_public',any(r['source_id']==d['source_id'] for r in req('GET','/api/public/recipes')[1]['items']))
  st,post,_=req('POST','/api/admin/posts',{'category':'merchants','organization':'QA 업체','title':'QA 제철 수산 소식','body':'테스트 게시물'})
  check('community_post_pending',st==201 and post['status']=='pending');postid=post['id']
  check('unverified_post_rejected',req('PATCH',f'/api/admin/posts/{postid}',{'status':'approved'})[0]==400)
  check('verified_post_published',req('PATCH',f'/api/admin/posts/{postid}',{'verified':1,'status':'approved'})[0]==200)
  check('public_post_visible',any(p['id']==postid for p in req('GET','/api/public/posts')[1]['items']))
  check('external_fake_connected_denied',req('PATCH','/api/admin/integrations/1',{'status':'connected'})[0]==400)
  st,rep,_=req('GET','/api/admin/reports');check('report_contains_order',st==200 and any(r['gross']>=36600 for r in rep['daily_sales']))
  st,overview,_=req('GET','/api/admin/overview');check('overview_count',st==200 and overview['kpis']['orders']==1)
  st,_,_=req('POST','/api/auth/logout',{});check('logout',st==200)
  check('session_revoked',req('GET','/api/admin/products')[0]==401)
  check('sqlite_integrity',subprocess.run([sys.executable,'-c','import sqlite3,sys;print(sqlite3.connect(sys.argv[1]).execute("PRAGMA integrity_check").fetchone()[0])',str(db)],capture_output=True,text=True).stdout.strip()=='ok')
 finally:
  sp.terminate();sp.wait(timeout=8)
result={'mode':'REAL_HTTP_LOCAL_BETA','checks':steps,'total':len(steps),'passed_count':sum(x['passed'] for x in steps),'all_passed':all(x['passed'] for x in steps),'live_payments':False,'real_shipping':False}
out.write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({'checks':len(steps),'passed':result['passed_count'],'all_passed':result['all_passed']},ensure_ascii=False))
