#!/usr/bin/env python3
"""Local-beta SQLite snapshot, integrity verification, and non-destructive restore.
NEVER run this against a production Neon database: that uses separate Postgres tools.
"""
import argparse,datetime,hashlib,json,os,sqlite3,sys,tempfile
from pathlib import Path
from urllib.parse import quote

def digest(path):
 h=hashlib.sha256()
 with path.open('rb') as f:
  for chunk in iter(lambda:f.read(1024*1024),b''):h.update(chunk)
 return h.hexdigest()

def db_ok(path):
 if not path.is_file():raise ValueError('DB 파일이 없습니다.')
 con=sqlite3.connect('file:'+quote(str(path.resolve()))+'?mode=ro',uri=True)
 try:
  check=con.execute('PRAGMA integrity_check').fetchone()[0]
  if check!='ok':raise ValueError('SQLite 무결성 실패: '+str(check))
  fk=con.execute('PRAGMA foreign_key_check').fetchall()
  if fk:raise ValueError(f'외래키 불일치: {len(fk)}')
  return {'integrity':'ok','foreign_keys':'ok'}
 finally:con.close()

def metadata(snapshot):return snapshot.with_suffix(snapshot.suffix+'.manifest.json')

def snapshot(source,dest):
 source=Path(source).resolve();dest=Path(dest).absolute()
 if not source.is_file():raise ValueError('원본 DB 없음')
 if dest.exists() or metadata(dest).exists():raise FileExistsError('이미 존재하는 스냅샷은 덮어쓰지 않습니다.')
 if source==dest:raise ValueError('백업 파일은 원본과 별도 경로여야 합니다.')
 dest.parent.mkdir(parents=True,exist_ok=True)
 fd,tmp=tempfile.mkstemp(prefix='.garak_backup_',suffix='.sqlite3',dir=dest.parent)
 os.close(fd)
 try:
  src=sqlite3.connect('file:'+quote(str(source))+'?mode=ro',uri=True)
  try:
   db=sqlite3.connect(tmp)
   try:src.backup(db)
   finally:db.close()
  finally:src.close()
  db_ok(Path(tmp));os.chmod(tmp,0o600)
  os.replace(tmp,dest)
  m={'type':'garak_local_beta_sqlite','sha256':digest(dest),'bytes':dest.stat().st_size,'created_at_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'verified':True,'source':'local_beta_only'}
  metadata(dest).write_text(json.dumps(m,indent=2,ensure_ascii=False),encoding='utf-8')
  return m
 finally:
  if Path(tmp).exists():Path(tmp).unlink()

def verify(path):
 path=Path(path).resolve();md=metadata(path)
 if not md.is_file():raise ValueError('매니페스트 없음')
 m=json.loads(md.read_text(encoding='utf-8'))
 if m.get('type')!='garak_local_beta_sqlite' or m.get('sha256')!=digest(path):raise ValueError('해시 불일치: 변조되었거나 손상된 백업')
 db_ok(path)
 return {'ok':True,'sha256':m['sha256'],'bytes':path.stat().st_size}

def restore(source,dest):
 source=Path(source).resolve();dest=Path(dest).absolute()
 verify(source)
 if dest.exists():raise FileExistsError('복원 대상 파일이 존재합니다. 원본을 덮어쓰지 않습니다.')
 if dest.is_symlink():raise ValueError('심볼릭 링크 대상 사용 불가')
 dest.parent.mkdir(parents=True,exist_ok=True)
 fd,tmp=tempfile.mkstemp(prefix='.garak_restore_',suffix='.sqlite3',dir=dest.parent)
 os.close(fd)
 try:
  with source.open('rb') as inp,open(tmp,'wb') as out:
   for chunk in iter(lambda:inp.read(1024*1024),b''):out.write(chunk)
  db_ok(Path(tmp));os.chmod(tmp,0o600);os.replace(tmp,dest)
  return {'restored':True,'destination':str(dest),'sha256':digest(dest)}
 finally:
  if Path(tmp).exists():Path(tmp).unlink()

def main():
 p=argparse.ArgumentParser(description='가락한상 로컬 베타 SQLite 백업/검증/복원 (Neon 불가)')
 p.add_argument('command',choices=['snapshot','verify','restore']);p.add_argument('source');p.add_argument('destination',nargs='?')
 a=p.parse_args()
 if a.command!='verify' and not a.destination:p.error('snapshot/restore 명령은 destination 필요')
 try:r={'snapshot':snapshot,'verify':verify,'restore':restore}[a.command](a.source,*([a.destination] if a.destination else []));print(json.dumps(r,ensure_ascii=False,indent=2))
 except Exception as e:print('ERROR:',e,file=sys.stderr);sys.exit(1)
if __name__=='__main__':main()
