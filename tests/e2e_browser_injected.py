"""Browser DOM/JS verified against real beta backend; local URL navigation blocked by sandbox policy.
Browser assets are injected from disk, API requests relayed via http.client. This is NOT a live deployment test.
"""
import subprocess,os,sys,json,time,socket,tempfile,http.client,re,base64
from pathlib import Path
from playwright.sync_api import sync_playwright
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'docs'/'BETA_SCREENSHOTS';OUT.mkdir(parents=True,exist_ok=True)
PORT=8156
html=(ROOT/'storefront'/'admin'/'index.html').read_text('utf-8')
html=re.sub(r'<link[^>]+href="/admin/assets/admin.css"[^>]*>', '',html)
html=re.sub(r'<script[^>]+src="/admin/assets/admin.js"[^>]*></script>', '',html)
css=(ROOT/'storefront'/'admin'/'assets'/'admin.css').read_text('utf-8')
# Force login image to embed for a faithful offline capture.
image=(ROOT/'storefront'/'assets/images/hero-market.webp').read_bytes()
css=css.replace("url('/assets/images/hero-market.webp')", "url('data:image/webp;base64,"+base64.b64encode(image).decode()+"')")
js=(ROOT/'storefront'/'admin'/'assets'/'admin.js').read_text('utf-8')
bridge=(ROOT/'storefront'/'assets/js/commerce-bridge-v6.js').read_text('utf-8')

with tempfile.TemporaryDirectory() as tmp:
 env=dict(os.environ,GARAK_ADMIN_DB=str(Path(tmp)/'browser.sqlite3'),GARAK_BOOTSTRAP_PASSWORD='BrowserOnly_TestAdmin_2026!')
 child=subprocess.Popen([sys.executable,'-m','admin_core.server','--port',str(PORT)],cwd=str(ROOT),env=env,stdout=subprocess.DEVNULL,stderr=subprocess.STDOUT)
 try:
  for i in range(60):
   try:s=socket.create_connection(('127.0.0.1',PORT),.5);s.close();break
   except OSError:time.sleep(.18)
  else:raise RuntimeError('Backend failed startup')
  results={'method':'injected-browser-DOM-with-backend-HTTP-bridge','pages':[],'actions':{},'console_errors':[]}
  with sync_playwright() as pw:
   browser=pw.chromium.launch(executable_path='/usr/bin/chromium',headless=True,args=['--no-sandbox','--disable-dev-shm-usage'])
   for device,width,height in [('PC',1440,900),('MOBILE',390,844)]:
    state={'cookie':''}
    def request(path,opts):
     if not path.startswith('/'):return {'status':404,'data':{'error':'path outside local beta'}}
     conn=http.client.HTTPConnection('127.0.0.1',PORT,timeout=8)
     method=str(opts.get('method','GET')).upper();headers={'Content-Type':'application/json','Host':f'127.0.0.1:{PORT}'}
     headers.update(opts.get('headers') or {})
     if state['cookie']:headers['Cookie']=state['cookie']
     conn.request(method,path,body=(opts.get('body') or '').encode('utf-8') if opts.get('body') is not None else None,headers=headers)
     res=conn.getresponse();data=res.read().decode('utf-8','replace')
     if res.getheader('Set-Cookie'):
      state['cookie']=res.getheader('Set-Cookie').split(';')[0]
     out={'status':res.status,'text':data};conn.close();return out
    context=browser.new_context(viewport={'width':width,'height':height},device_scale_factor=1,locale='ko-KR')
    page=context.new_page();page.expose_function('__bridgeRequest',request)
    page.on('pageerror',lambda x:results['console_errors'].append(str(x)))
    page.set_content(html,wait_until='domcontentloaded');page.add_style_tag(content=css)
    page.evaluate('''() => { window.fetch=async (path, opts={})=>{let res=await window.__bridgeRequest(path,opts);return {ok:res.status>=200&&res.status<300,status:res.status,json:async()=>JSON.parse(res.text),text:async()=>res.text};}; }''')
    page.add_script_tag(content=js)
    page.locator('#loginForm input[name=username]').fill('admin');page.locator('#loginForm input[name=password]').fill('BrowserOnly_TestAdmin_2026!');page.locator('#loginForm button[type=submit]').click()
    page.locator('#content .kpi-grid').wait_for(timeout=15000)
    page.screenshot(path=str(OUT/f'{device}_overview.png'),full_page=True,timeout=12000)
    results['actions'][device+'_login']=page.locator('#roleInfo').inner_text()
    for module in ['products','inventory_moves','orders','shipments','settlements','merchants','recipes','creators','posts','campaigns','customers','tickets','integrations','users','audit_logs','reports']:
     page.evaluate('(x)=>location.hash=x',module)
     page.locator('#pageTitle').get_by_text('',exact=False) if False else None
     page.wait_for_function('(m)=>location.hash==="#"+m && !!document.querySelector("#tableSearch, #content .kpi-grid")',arg=module,timeout=10000)
     page.wait_for_timeout(85)
     if module in ['products','orders','recipes','posts','integrations','reports']:
      page.screenshot(path=str(OUT/f'{device}_{module}.png'),full_page=True,timeout=13000)
     overflow=page.evaluate('document.documentElement.scrollWidth > window.innerWidth+3')
     results['pages'].append({'device':device,'module':module,'horizontal_overflow':overflow,'title':page.locator('#pageTitle').inner_text()})
     if overflow:raise AssertionError(f'Horizontal overflow {device} {module}')
    page.evaluate('()=>location.hash="products"');page.locator('tr [data-action=edit]').first.wait_for(timeout=10000)
    page.locator('tr [data-action=edit]').first.click();page.locator('#modal').wait_for(state='visible')
    page.locator('#modalForm input[name=price]').fill('57000');page.locator('#modalForm button[type=submit]').click();page.wait_for_timeout(400);print('EDIT',page.locator('#toast').inner_text(),page.locator('#modal').is_visible(),flush=True);page.locator('#modal').wait_for(state='hidden',timeout=10000)
    results['actions'][device+'_price_edit']=page.locator('#toast').inner_text()
    page.evaluate('()=>location.hash="orders"');page.locator('[data-action=createOrder]').wait_for(timeout=10000)
    page.locator('[data-action=createOrder]').click();page.locator('#modalForm input[name=slug]').fill('bangeo-hoe');page.locator('#modalForm input[name=qty]').fill('2');page.locator('#modalForm button[type=submit]').click();page.locator('#modal').wait_for(state='hidden',timeout=10000)
    results['actions'][device+'_order_create']=page.locator('#toast').inner_text()
    page.evaluate('()=>location.hash="reports"');page.locator('#content .kpi-grid').wait_for(timeout=10000)
    results['actions'][device+'_report']=page.locator('#content .kpi-grid').inner_text()[:170]
    context.close()
   browser.close()
  assert not results['console_errors'],results['console_errors']
  (ROOT/'docs'/'QA_E2E_BROWSER.json').write_text(json.dumps(results,ensure_ascii=False,indent=2),encoding='utf-8')
  print(json.dumps({'screenshots':len(list(OUT.glob('*.png'))),'pages_tested':len(results['pages']),'actions':results['actions'],'console_errors':results['console_errors']},ensure_ascii=False,indent=2))
 finally:child.terminate();child.wait(timeout=8)
