import unittest
from pathlib import Path
from admin_core.database import init_db
from admin_core.server import Server
import tempfile,threading,http.client,os
class MediaAuthTest(unittest.TestCase):
 def test_media_requires_session(self):
  with tempfile.TemporaryDirectory() as d:
   os.environ['GARAK_BOOTSTRAP_PASSWORD']='OnlyLocalTestPass_2026!'
   con=init_db(Path(d)/'db.sqlite3');con.close()
   s=Server(('127.0.0.1',0),Path(d)/'db.sqlite3');t=threading.Thread(target=s.serve_forever,daemon=True);t.start()
   try:
    c=http.client.HTTPConnection('127.0.0.1',s.server_address[1]);c.request('GET','/admin/recipe-media.html');r=c.getresponse();r.read();self.assertEqual(r.status,401);c.close()
   finally:s.shutdown();s.server_close()
if __name__=='__main__':unittest.main()
