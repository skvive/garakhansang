"""Off-network browser validation using genuine browser DOM + Python domain bridge.
No HTTP browser E2E claimed: the sandbox blocks Chromium loopback network.
"""
import base64,json,mimetypes,sys
from pathlib import Path
from playwright.sync_api import sync_playwright
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'backend'))
import domain
STATIC=ROOT/'storefront'
DB=ROOT/'backend/browser-qa.sqlite'
if DB.exists():DB.unlink()
domain.init_db(DB)
OUT=ROOT/'docs/screenshots'
OUT.mkdir(parents=True,exist_ok=True)
checks=[];errors=[]
def test(name,ok):
 checks.append({'name':name,'passed':bool(ok)})
 if not ok:print('FAIL',name)

def bridge(source,req):
 path=req['path'].split('/v1')[-1].split('?')[0]
 mode=req.get('method','GET');payload=req.get('body') or {};token=req.get('authorization','').removeprefix('Bearer ');role='admin' if token=='qa-local-admin-token' else 'customer'
 try:
  with domain.db_connect(DB) as db:
   if mode=='GET':
    data={
      '/health':{'ok':True,'mode':'demo'},'/markets':domain.markets(db),'/merchants':domain.merchants(db),
      '/products':domain.products(db),'/orders':domain.get_orders(db),'/dashboard':domain.dashboard(db)}.get(path)
    if data is None:raise domain.DomainError('not found',404)
    if path in ('/orders','/dashboard'):domain.require_role(role, {'admin'})
   elif path=='/orders':data=domain.create_orders(db,payload,req.get('idempotency',''),role)
   elif path.endswith('/mock-pay'):data=domain.mock_pay(db,path.split('/')[2],role,token)
   elif path.endswith('/approve'):data=domain.approve_merchant(db,path.split('/')[2],role)
   elif '/merchants/' in path and path.endswith('/status'):
    v=path.split('/');data=domain.merchant_status(db,v[2],v[4],payload['status'],role)
   elif path.endswith('/hub-collect'):data=domain.hub_collect(db,path.split('/')[2],role)
   elif '/dispatch/' in path:
    v=path.split('/');data=domain.dispatch_update(db,v[2],v[3].replace('-','_'),payload.get('rider_alias',''),role)
   elif path=='/merchants/apply':data=domain.apply_merchant(db,payload,role)
   elif path.endswith('/stock'):
    v=path.split('/');data=domain.update_stock(db,v[2],v[4],payload['stock'],role)
   else:raise domain.DomainError('not found',404)
  return {'status':200,'data':data}
 except domain.DomainError as e:return {'status':e.status,'data':{'error':str(e)}}

FETCH_SHIM='''window.fetch=async function(url,opt={}){
 const body=opt.body?JSON.parse(opt.body):null;
 const r=await window.pyBridge({path:String(url),method:opt.method||'GET',body,authorization:opt.headers?.['Authorization']||'',idempotency:opt.headers?.['Idempotency-Key']||''});
 return new Response(JSON.stringify(r.data),{status:r.status,headers:{'Content-Type':'application/json'}});
};'''

def dataurl(file):
 mime=mimetypes.guess_type(str(file))[0] or 'application/octet-stream'
 return f'data:{mime};base64,'+base64.b64encode(file.read_bytes()).decode()

def ops_html():
 html=(STATIC/'order/ops.html').read_text()
 html=html.replace('<link rel="stylesheet" href="ops.css">','<style>'+ (STATIC/'order/ops.css').read_text()+'</style>')
 html=html.replace('<script defer src="ops.js"></script>','<script>'+ (STATIC/'order/ops.js').read_text()+'</script>')
 html=html.replace('src="mascot-rider.webp"','src="'+dataurl(STATIC/'order/mascot-rider.webp')+'"')
 return html

def customer_html():
 html=(STATIC/'order/index.html').read_text()
 html=html.replace('<link rel="stylesheet" href="styles.css">','<style>'+(STATIC/'order/styles.css').read_text()+'</style>')
 js=(STATIC/'order/app.js').read_text()
 images={}
 for p in (STATIC/'assets/images').glob('*.webp'):images[p.name]=dataurl(p)
 for p in (STATIC/'assets/editorial').glob('*.webp'):images['../editorial/'+p.name]=dataurl(p)
 js=js.replace("const ROOT = '../assets/images/';",'const IMAGE_URLS = '+json.dumps(images)+';')
 js=js.replace("const BRAND = '../assets/brand/'; const RIDER = 'mascot-rider.webp';", "const BRAND = ''; const RIDER = "+json.dumps(dataurl(STATIC/'order/mascot-rider.webp'))+';')
 js=js.replace('const photo=p=>ROOT+p.img;','const photo=p=>IMAGE_URLS[p.img]||"";')
 html=html.replace('<script defer src="app.js"></script>','<script>'+js+'</script>')
 return html

with sync_playwright() as p:
 browser=p.chromium.launch(executable_path='/usr/bin/chromium',headless=True,args=['--no-sandbox'])
 for width,height,label in [(390,844,'mobile'),(1280,900,'desktop')]:
  ctx=browser.new_context(viewport={'width':width,'height':height})
  ctx.expose_binding('pyBridge',bridge)
  ctx.add_init_script(FETCH_SHIM)
  page=ctx.new_page();page.on('pageerror',lambda e:errors.append(str(e)))
  page.set_content(ops_html(),wait_until='load')
  page.locator('#demoAdminToken').fill('qa-local-admin-token')
  page.locator('#adminLogin button').click()
  page.wait_for_timeout(250)
  test('ops API status '+label,'API 연결됨' in page.locator('#apiState').inner_text())
  test('ops no horizontal overflow '+label,page.evaluate('document.documentElement.scrollWidth<=innerWidth+1'))
  test('ops dashboard '+label,'운영 대시보드' in page.locator('#pageHeading').inner_text())
  page.screenshot(path=str(OUT/f'ops_overview_{label}.png'),full_page=True)
  page.locator('[data-panel="merchants"]').click()
  test('merchant entry form '+label,page.locator('#applyMerchant').count()==1)
  page.screenshot(path=str(OUT/f'ops_merchants_{label}.png'),full_page=True)
  if label=='mobile':
   page.locator('[data-panel="campaigns"]').click()
   page.screenshot(path=str(OUT/'ops_campaigns_mobile.png'),full_page=True)
   page.locator('[data-panel="overview"]').click()
   page.locator('#seedOrder').click()
   page.wait_for_timeout(500)
   test('mock order seed',int(page.locator('.stat b').first.inner_text())>0)
   page.locator('[data-panel="fulfillment"]').click()
   page.screenshot(path=str(OUT/'ops_fulfillment_mobile.png'),full_page=True)
  ctx.close()
 ctx=browser.new_context(viewport={'width':390,'height':844})
 ctx.expose_binding('pyBridge',bridge);ctx.add_init_script(FETCH_SHIM)
 page=ctx.new_page();page.on('pageerror',lambda e:errors.append(str(e)))
 page.set_content(customer_html(),wait_until='load')
 test('customer app header','GARAK HANSANG ORDER' in page.content())
 page.screenshot(path=str(OUT/'customer_home_mobile.png'),full_page=True)
 page.locator('[data-detail="g1"]').first.click();page.locator('[data-add-detail="g1"]').click()
 page.locator('[data-tab="cart"]').first.click()
 test('customer cart present','당일 딸기' in page.locator('#mainContent').inner_text())
 page.screenshot(path=str(OUT/'customer_cart_mobile.png'),full_page=True)
 page.locator('[data-checkout]').click();page.wait_for_timeout(600)
 test('customer checkout and MY','시연 주문 내역' in page.locator('#mainContent').inner_text())
 test('customer no overflow',page.evaluate('document.documentElement.scrollWidth<=innerWidth+1'))
 page.screenshot(path=str(OUT/'customer_my_mobile.png'),full_page=True)
 ctx.close();browser.close()
result={'checks':checks,'errors':errors,'method':'Chromium rendered inline source with Python domain API bridge; NOT HTTP browser E2E'}
(OUT.parent/'BROWSER_QA.json').write_text(json.dumps(result,ensure_ascii=False,indent=2))
print(json.dumps(result,ensure_ascii=False,indent=2))
assert not errors,errors
assert all(x['passed'] for x in checks)
