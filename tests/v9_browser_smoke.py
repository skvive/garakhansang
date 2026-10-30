"""Real Chromium on a local loopback beta server; never touches live systems."""
import json,os,pathlib,subprocess,sys,tempfile,time,socket,urllib.request,shutil
ROOT=pathlib.Path(__file__).resolve().parents[1]
try:from playwright.sync_api import sync_playwright
except ImportError:raise SystemExit('Browser QA SKIPPED: pip install playwright and local chromium are required')
CHROME=next((x for x in [shutil.which('chromium'),shutil.which('google-chrome'),shutil.which('chrome'),'/usr/bin/chromium',os.path.join(os.environ.get('PROGRAMFILES',''),'Google','Chrome','Application','chrome.exe'),os.path.join(os.environ.get('PROGRAMFILES(X86)',''),'Google','Chrome','Application','chrome.exe')] if x and pathlib.Path(x).exists()),None)
if not CHROME:raise SystemExit('Browser QA SKIPPED: system Chromium missing')
with socket.socket() as sock:
 sock.bind(('127.0.0.1',0));port=sock.getsockname()[1]
checks=[]; errors=[];output=ROOT/'QA_V9_RESULTS';output.mkdir(exist_ok=True)
with tempfile.TemporaryDirectory(prefix='garak_browser_') as td:
 db=pathlib.Path(td)/'qa.sqlite3'
 proc=subprocess.Popen([sys.executable,'-m','admin_core.server','--host','127.0.0.1','--port',str(port),'--db',str(db)],cwd=ROOT,stdout=subprocess.DEVNULL,stderr=subprocess.STDOUT)
 try:
  base='http://127.0.0.1:'+str(port)
  for _ in range(75):
   if proc.poll() is not None:break
   try:
    with urllib.request.urlopen(base+'/api/health',timeout=.5) as resp:
     if resp.status==200:break
   except Exception:time.sleep(.1)
  else:raise RuntimeError('Local service failed to start')
  cred=(db.parent/'FIRST_LOGIN_LOCAL_ONLY.txt').read_text('utf8')
  password=cred.partition('Password: ')[2].strip()
  targets=[('home','/'),('category','/category/beauty.html'),('product','/product/bangeo-hoe.html'),('recipe_list','/recipes/index.html'),('recipe_detail','/recipes/recipe-001.html'),('community','/community/index.html'),('cart','/cart.html'),('merchant','/merchant/index.html'),('admin','/admin/')]
  with sync_playwright() as pw:
   browser=pw.chromium.launch(headless=True,executable_path=CHROME,args=['--no-sandbox','--disable-dev-shm-usage'])
   for device,viewport in [('PC',{'width':1366,'height':900}),('MOBILE',{'width':390,'height':844})]:
    context=browser.new_context(viewport=viewport,locale='ko-KR',accept_downloads=True)
    page=context.new_page()
    page.on('pageerror',lambda ex: errors.append({'device':device,'message':str(ex)[:200]}))
    for name,path in targets:
     response=page.goto(base+path,wait_until='domcontentloaded',timeout=15000)
     page.wait_for_timeout(150)
     code=response.status if response else 0
     over=page.evaluate('document.documentElement.scrollWidth > window.innerWidth+3')
     title=page.title()
     checks.append({'device':device,'page':name,'http':code,'overflow':over,'title':title})
     if name=='home':page.screenshot(path=str(output/('BROWSER_'+device+'_HOME.png')),full_page=False)
     if name=='recipe_detail' and device=='MOBILE':page.screenshot(path=str(output/'BROWSER_MOBILE_RECIPE.png'),full_page=False)
     if code!=200 or over:errors.append({'device':device,'page':name,'http':code,'overflow':over})
    page.goto(base+'/admin/',wait_until='domcontentloaded')
    page.locator('#loginForm input[name="username"]').fill('admin')
    page.locator('#loginForm input[name="password"]').fill(password)
    page.locator('#loginForm button[type="submit"]').click()
    page.locator('#app:not([hidden])').wait_for(timeout=10000)
    page.wait_for_timeout(350)
    if device=='PC':page.screenshot(path=str(output/'BROWSER_PC_DASHBOARD.png'),full_page=False)
    checks.append({'device':device,'page':'admin_login','result':'PASS'})
    context.close()
   browser.close()
 finally:
  proc.terminate()
  try:proc.wait(timeout=4)
  except subprocess.TimeoutExpired:proc.kill()
report={'checks':checks,'runtime_errors':errors,'passed':not errors and len(checks)==20,'environment':'local browser with temporary SQLite demo DB'}
(output/'BROWSER_SMOKE.json').write_text(json.dumps(report,indent=2,ensure_ascii=False),encoding='utf8')
print(json.dumps({'tests':len(checks),'errors':errors,'passed':report['passed']},ensure_ascii=False))
if not report['passed']:sys.exit(1)
