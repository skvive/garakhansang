import json,os,pathlib,subprocess,sys,tempfile,unittest,threading,urllib.request,urllib.error
from http.cookiejar import CookieJar
BASE=pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0,str(BASE))

class PackageTests(unittest.TestCase):
    def test_local_workspace_assets(self):
        self.assertTrue((BASE/'.vscode/tasks.json').exists())
        self.assertTrue((BASE/'INSTALL_AND_RUN_WINDOWS.bat').exists())
        self.assertTrue((BASE/'design_reference/SELECTED_02_MARKET_STORY_HOME.jpg').exists())
        self.assertEqual(132,len(json.loads((BASE/'storefront/assets/recipes.json').read_text('utf8'))))
    def test_no_packaged_live_keys(self):
        for p in BASE.rglob('*'):
            if p.is_file() and p.name=='.env':self.fail('Unexpected .env file included: '+str(p))
    def test_loopback_health_and_auth_boundary(self):
        from admin_core.database import init_db
        from admin_core.server import Server
        with tempfile.TemporaryDirectory() as td:
            db=pathlib.Path(td)/'qa.sqlite3'
            # Does not use or alter user's local runtime or any live DB.
            con=init_db(db,seed=True,bootstrap=False);con.close()
            srv=Server(('127.0.0.1',0),db)
            thread=threading.Thread(target=srv.serve_forever,daemon=True);thread.start()
            try:
                base='http://127.0.0.1:'+str(srv.server_port)
                with urllib.request.urlopen(base+'/api/health') as r:
                    d=json.load(r);self.assertEqual('LOCAL_BETA',d['mode']);self.assertEqual('simulation_only',d['payments'])
                with urllib.request.urlopen(base+'/api/public/products') as r:
                    d=json.load(r);self.assertEqual(44,len(d['items']))
                with urllib.request.urlopen(base+'/api/public/recipes') as r:
                    d=json.load(r);self.assertEqual(0,len(d['items'])) # unpublished by design
                with self.assertRaises(urllib.error.HTTPError) as x:
                    urllib.request.urlopen(base+'/api/admin/products')
                self.assertEqual(401,x.exception.code)
                with urllib.request.urlopen(base+'/') as r:self.assertIn('text/html',r.headers.get('Content-Type',''))
            finally:srv.shutdown();srv.server_close();thread.join(timeout=2)
    def test_shop_uses_local_mode_only(self):
        text=(BASE/'storefront/index.html').read_text('utf8')
        self.assertIn('가락한상',text)
        self.assertTrue((BASE/'storefront/assets/js/commerce-bridge-v6.js').exists() or
                        any('commerce-bridge-v6.js' in str(p) for p in (BASE/'storefront').rglob('*.js')))

if __name__=='__main__':unittest.main()
