import tempfile,unittest,os,sqlite3
from pathlib import Path
from admin_core.database import init_db
from tools.db_snapshot import snapshot,verify,restore
class BackupRecoveryTests(unittest.TestCase):
 def test_backup_integrity_and_restore(self):
  with tempfile.TemporaryDirectory() as d:
   d=Path(d);db=d/'active.sqlite3';bk=d/'backup.sqlite3';target=d/'recovered.sqlite3'
   os.environ['GARAK_BOOTSTRAP_PASSWORD']='LocalBackupTest_2026!'
   con=init_db(db);con.close()
   m=snapshot(db,bk);self.assertEqual(verify(bk)['sha256'],m['sha256'])
   result=restore(bk,target);self.assertTrue(result['restored'])
   with sqlite3.connect(target) as con:self.assertEqual(con.execute('select count(*) from products').fetchone()[0],44)
   with self.assertRaises(FileExistsError):restore(bk,target)
 def test_tampered_copy_rejected(self):
  with tempfile.TemporaryDirectory() as d:
   d=Path(d);db=d/'active.sqlite3';bk=d/'backup.sqlite3'
   os.environ['GARAK_BOOTSTRAP_PASSWORD']='LocalBackupTest_2026!'
   con=init_db(db);con.close();snapshot(db,bk)
   with bk.open('ab') as f:f.write(b'junk')
   with self.assertRaises(ValueError):verify(bk)
if __name__=='__main__':unittest.main()
