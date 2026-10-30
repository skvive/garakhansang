"""Verify packaged file hashes; ignores only user-created runtime and QA output."""
from pathlib import Path
import hashlib,json,sys
root=Path(__file__).resolve().parents[1]
p=root/'MANIFEST_SHA256.json'
if not p.exists():print('missing MANIFEST_SHA256.json');sys.exit(1)
items=json.loads(p.read_text('utf-8'))['files']
errors=[]
for relative,expected in items.items():
 path=root/relative
 if not path.is_file():errors.append('missing '+relative);continue
 got=hashlib.sha256(path.read_bytes()).hexdigest()
 if expected!=got:errors.append('hash mismatch '+relative)
print('VERIFY SHA256: checked',len(items),'files, errors:',len(errors))
if errors:print('\n'.join(errors[:30]));sys.exit(1)
