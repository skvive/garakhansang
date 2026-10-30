#!/usr/bin/env python3
"""Preflight all Next.js patches on a temporary SOURCE SUBSET, then commit file changes with rollback.
Local git checkout only; never pushes or deploys. Requires a clean feature branch for --apply.
"""
from __future__ import annotations
import argparse, datetime, hashlib, json, os, pathlib, shutil, subprocess, sys, tempfile
ROOT=pathlib.Path(__file__).resolve().parents[1]
SRC=ROOT/'integrations/story_v5_patch'
OPS=ROOT/'integrations/apply_ops_next_overlay.py'
NEEDED=[
 'package.json',
 'src/app/[lng]/page.tsx',
 'src/app/[lng]/layout.tsx',
 'src/app/[lng]/product/[slug]/page.tsx',
 'src/app/[lng]/category/[cat]/page.tsx',
 'src/app/[lng]/prices/page.tsx',
 'src/app/[lng]/community/page.tsx',
 'src/components/site-header.tsx',
 'src/components/sections/quick-links.tsx',
 'src/components/sections/price-ticker.tsx',
]
def sh(cmd,cwd):
    p=subprocess.run(cmd,cwd=cwd,text=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
    if p.returncode:raise RuntimeError(' '.join(cmd)+' failed: '+p.stdout[-1500:])
    return p.stdout.strip()
def hash_file(p):return hashlib.sha256(p.read_bytes()).hexdigest() if p.is_file() else None

def run(checkout,apply=False):
    checkout=checkout.resolve();app=checkout/'lexistyle'
    if not (checkout/'.git').exists() or not app.is_dir():raise RuntimeError('git-cloned skvive/garak repository required (must contain .git and lexistyle/)')
    branch=sh(['git','branch','--show-current'],checkout)
    if apply and (not branch or branch in {'main','master','production','develop'}):
        raise RuntimeError('ABORT: --apply requires a dedicated feature branch, not '+repr(branch))
    if apply and sh(['git','status','--porcelain','--untracked-files=all'],checkout):
        raise RuntimeError('ABORT: working tree is not clean. Commit/stash before integration.')
    for rel in NEEDED:
        if not (app/rel).is_file():raise RuntimeError('Missing source file: '+rel)
    with tempfile.TemporaryDirectory(prefix='garak_staging_') as folder:
        staging=pathlib.Path(folder)/'checkout'
        stage_app=staging/'lexistyle'
        for rel in NEEDED:
            target=stage_app/rel;target.parent.mkdir(parents=True,exist_ok=True)
            shutil.copy2(app/rel,target)
        # Include existing add-ons so previously installed bundles are correctly recognized.
        overlay_roots=[SRC/'overlay/lexistyle',SRC/'story-next-overlay/lexistyle',ROOT/'integrations/nextjs_overlay/lexistyle']
        for base in overlay_roots:
            if not base.exists():continue
            for f in base.rglob('*'):
                if not f.is_file():continue
                rel=f.relative_to(base);existing=app/rel
                if existing.is_file():
                    dst=stage_app/rel;dst.parent.mkdir(parents=True,exist_ok=True)
                    shutil.copy2(existing,dst)
        sh([sys.executable,str(SRC/'apply_story_v5.py'),str(staging)],ROOT)
        sh([sys.executable,str(OPS),str(staging)],ROOT)
        changes=[]
        for f in stage_app.rglob('*'):
            if not f.is_file():continue
            rel=f.relative_to(stage_app);dest=app/rel
            before=hash_file(dest);after=hash_file(f)
            if before!=after:changes.append({'path':rel.as_posix(),'before':before,'after':after,'kind':'modify' if before else 'add'})
        summary={'checkout':str(checkout),'branch':branch,'dry_run':not apply,'files_changed':len(changes),'changes':changes}
        print(json.dumps(summary,ensure_ascii=False,indent=2),flush=True)
        if not apply:return summary
        # No modifications to real checkout occurred before this point.
        for item in changes:
            if hash_file(app/item['path'])!=item['before']:
                raise RuntimeError('ABORT: source changed during patch preflight: '+item['path'])
        backup_dir=checkout/'.git'/'garak_onepack_backups'/datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%SZ')
        backup_dir.mkdir(parents=True,exist_ok=True)
        completed=[]
        try:
            for item in changes:
                original=app/item['path'];staged=stage_app/item['path']
                if original.exists():
                    backup=backup_dir/item['path'];backup.parent.mkdir(parents=True,exist_ok=True)
                    shutil.copy2(original,backup)
                original.parent.mkdir(parents=True,exist_ok=True)
                tmp=original.with_name(original.name+'.garak-tmp')
                shutil.copy2(staged,tmp);os.replace(tmp,original)
                completed.append(item)
        except Exception:
            for item in reversed(completed):
                target=app/item['path'];saved=backup_dir/item['path']
                if saved.exists():shutil.copy2(saved,target)
                else:target.unlink(missing_ok=True)
            raise
        (backup_dir/'manifest.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding='utf-8')
        print('APPLIED to feature branch. Local backup:',backup_dir)
        print('Next step in lexistyle: npm ci ; npm run build ; preview deployment and sandbox purchase flow tests.')
        return summary

def main():
    a=argparse.ArgumentParser(description='Safe Next.js integration staging for garak git checkout')
    a.add_argument('checkout',type=pathlib.Path)
    grp=a.add_mutually_exclusive_group();grp.add_argument('--dry-run',action='store_true');grp.add_argument('--apply',action='store_true')
    args=a.parse_args()
    try:run(args.checkout,args.apply)
    except (RuntimeError,OSError) as e:
        print('FAILED / NO LIVE DEPLOYMENT:',e,file=sys.stderr);sys.exit(2)
if __name__=='__main__':main()
