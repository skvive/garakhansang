#!/usr/bin/env python3
"""Copy only new operations launch routes into a CLONED source in a separate branch. No production writes."""
import sys,shutil
from pathlib import Path
if len(sys.argv)!=2:raise SystemExit('Usage: python integrations/apply_ops_next_overlay.py PATH_TO_CLONED_SKVIVE_GARAK')
root=Path(__file__).resolve().parent;target=Path(sys.argv[1]).resolve()/'lexistyle'
if not (target/'package.json').exists() or not (target/'src/app/[lng]/page.tsx').exists():raise SystemExit('ABORT: not a skvive/garak compatible checkout')
files=[p for p in (root/'nextjs_overlay'/'lexistyle').rglob('*') if p.is_file()]
for p in files:
 dest=target/p.relative_to(root/'nextjs_overlay'/'lexistyle')
 if dest.exists() and dest.read_bytes()!=p.read_bytes():raise SystemExit('ABORT: source conflict at '+str(dest))
for p in files:
 dest=target/p.relative_to(root/'nextjs_overlay'/'lexistyle');dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(p,dest)
 print('CREATED',dest)
print('OK: launch route only; no SSO, database synchronization, payment testing or deployment has occurred')
