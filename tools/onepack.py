#!/usr/bin/env python3
"""Garak Hansang local one-pack launcher. No production writes or payments."""
from __future__ import annotations
import argparse, hashlib, json, os, pathlib, shutil, socket, subprocess, sys, time, urllib.error, urllib.request, webbrowser

ROOT=pathlib.Path(__file__).resolve().parents[1]
SITE=ROOT/'storefront'
MIN_PY=(3,11)

def run_cmd(command,env=None,log=None,timeout=None):
    print('RUN:', ' '.join(str(x) for x in command),flush=True)
    p=subprocess.run(command,cwd=ROOT,env=env,text=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=timeout)
    if log:
        pathlib.Path(log).parent.mkdir(parents=True,exist_ok=True)
        pathlib.Path(log).write_text(p.stdout,encoding='utf-8')
    print(p.stdout[-6000:],flush=True)
    return p.returncode

def doctor():
    checks={
      'Python >= 3.11':sys.version_info >= MIN_PY,
      'storefront/index.html':(SITE/'index.html').is_file(),
      'storefront/admin/index.html':(SITE/'admin/index.html').is_file(),
      'Python server':(ROOT/'admin_core/server.py').is_file(),
      'SQLite schema':(ROOT/'admin_core/database.py').is_file(),
      'selected design 02':(ROOT/'design_reference/SELECTED_02_MARKET_STORY_HOME.jpg').is_file(),
      'GitHub integration patch':(ROOT/'integrations/story_v5_patch/apply_story_v5.py').is_file(),
      'operations patch':(ROOT/'integrations/apply_ops_next_overlay.py').is_file(),
      'recipe dataset':(SITE/'assets/recipes.json').is_file(),
      'product dataset':(SITE/'assets/products.json').is_file(),
      'Runtime data isolated':(not (ROOT/'runtime').exists()) or (ROOT/'runtime').is_dir(),
    }
    try:
        data=json.loads((SITE/'assets/recipes.json').read_text('utf-8'))
        checks['132 recipes']=len(data)==132
        data=json.loads((SITE/'assets/products.json').read_text('utf-8'))
        checks['44 sample products']=len(data)==44
        checks['132 recipe WebP']=len(list((SITE/'assets/images/recipes').glob('*.webp')))==132
        checks['217 storefront HTML']=len(list(SITE.rglob('*.html')))==218
    except Exception as e:
        checks['Dataset parse failed']=False;print('Dataset error:',type(e).__name__,str(e))
    for key,v in checks.items():print(('PASS' if v else 'FAIL')+' | '+key)
    return 0 if all(checks.values()) else 1

def startup(open_browser=False,port=8099):
    if doctor():return 1
    os.makedirs(ROOT/'runtime',exist_ok=True)
    address='http://127.0.0.1:'+str(port)
    try:
        with socket.create_connection(('127.0.0.1',port),timeout=.3):
            print('ABORT: port',port,'is already occupied. Cannot safely start another instance.');return 2
    except OSError:pass
    print('LOCAL BETA ONLY — demo orders, no real payment / external API / live Neon writes.')
    print('Shop:',address+'/  Admin:',address+'/admin/')
    print('Bootstrap password file created on FIRST launch only: runtime/FIRST_LOGIN_LOCAL_ONLY.txt')
    # Explicit fixed loopback: never expose dev server accidentally on a public network.
    proc=subprocess.Popen([sys.executable,'-m','admin_core.server','--host','127.0.0.1','--port',str(port)],cwd=ROOT)
    try:
        ready=False
        for _ in range(45):
            if proc.poll() is not None:break
            try:
                with urllib.request.urlopen(address+'/api/health',timeout=.4) as resp:
                    if resp.status==200 and json.load(resp).get('mode')=='LOCAL_BETA':ready=True;break
            except (OSError,ValueError):time.sleep(.15)
        if not ready:
            print('FAIL: local service did not pass health check');return 3
        print('RUNNING:',address,'(Ctrl+C to stop)')
        if open_browser:
            try:webbrowser.open(address)
            except Exception:pass
        return proc.wait()
    except KeyboardInterrupt:
        print('Stopping local server.');return 0
    finally:
        if proc.poll() is None:
            proc.terminate()
            try:proc.wait(timeout=4)
            except subprocess.TimeoutExpired:proc.kill()

def qa():
    if doctor():return 1
    log_dir=ROOT/'QA_V9_RESULTS';log_dir.mkdir(exist_ok=True)
    commands=[('unittest_qa_71.log',[sys.executable,'-m','unittest','discover','-s','tests','-p','test_*.py','-q']),
        ('business_flow.log',[sys.executable,'tests/v8_full_business_flow.py']),
        ('static_audit.log',[sys.executable,'tests/release_audit.py']),
        ('concurrency.log',[sys.executable,'tests/concurrency_beta.py']),
        ('github_merge_fixture.log',[sys.executable,'tests/qa_github_merge_fixture.py'])]
    if shutil.which('node'):
        commands.append(('currency.log',['node','--test','tests/currency_contract.test.mjs']))
    else:print('NOTICE: Node.js unavailable: currency tests SKIPPED, not passed')
    results={}
    for name,cmd in commands:
        try:code=run_cmd(cmd,log=log_dir/name,timeout=160)
        except (OSError,subprocess.TimeoutExpired) as exc:
            code=2;(log_dir/name).write_text(str(exc),encoding='utf-8')
        results[name]=('PASS' if code==0 else 'FAIL')
    results['complete']=bool(shutil.which('node')) and all(v=='PASS' for v in results.values())
    (log_dir/'V9_RUN_SUMMARY.json').write_text(json.dumps(results,ensure_ascii=False,indent=2),encoding='utf-8')
    print('QA SUMMARY',json.dumps(results,ensure_ascii=False))
    return 0 if results['complete'] else 1

def main():
    parser=argparse.ArgumentParser(description='Garak Hansang V9 local beta launcher')
    sub=parser.add_subparsers(dest='command',required=True)
    run=sub.add_parser('run');run.add_argument('--port',type=int,default=8099);run.add_argument('--open-browser',action='store_true')
    sub.add_parser('doctor');sub.add_parser('qa')
    args=parser.parse_args()
    if args.command=='run':sys.exit(startup(args.open_browser,args.port))
    if args.command=='doctor':sys.exit(doctor())
    sys.exit(qa())
if __name__=='__main__':main()
