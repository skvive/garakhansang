#!/usr/bin/env python3
"""Apply existing safe commerce/recipe overlay, then brand-wide story redesign (#2).
Usage: python apply_story_v5.py PATH_TO_CLONED_GARAK
Operate in a dedicated Git branch and back up existing files. No production writes.
"""
from pathlib import Path
import subprocess, shutil, sys
PACKAGE=Path(__file__).resolve().parent
if len(sys.argv)!=2: raise SystemExit('Usage: python apply_story_v5.py /path/to/garak')
checkout=Path(sys.argv[1]).resolve();app=checkout/'lexistyle'
assert (app/'package.json').exists() and (app/'src/app/[lng]/page.tsx').exists(), 'Expected skvive/garak source with lexistyle folder'
# Run v4 overlay (recipes, merchant board, price honesty), no database auto-migrations.
if '<GarakStoryHero />' not in (app/'src/app/[lng]/page.tsx').read_text('utf-8'):
    subprocess.run([sys.executable,str(PACKAGE/'integrate_into_garak.py'),str(checkout)],check=True)
elif not (app/'src/lib/garak/recipes.ts').exists():
    raise SystemExit('ABORT: theme present but recipe integration absent')
checks=[
 ('src/app/[lng]/page.tsx','<HeroEditorial />','<GarakStoryHero />'),
 ('src/app/[lng]/page.tsx','import { HeroEditorial } from "@/components/sections/hero-editorial";','import { GarakStoryHero } from "@/components/garak/garak-story-hero";'),
 ('src/app/[lng]/layout.tsx','import "../globals.css";','import "../globals.css";\nimport "../market-story-v5.css";'),
 ('src/app/[lng]/layout.tsx','<body className="min-h-dvh pb-16 md:pb-0">','<body className="story-next min-h-dvh pb-16 md:pb-0">'),
]
# Detect divergence BEFORE editing existing code. Idempotent and no blind global overwrite.
for rel,old,new in checks:
 s=(app/rel).read_text('utf-8')
 if new not in s and s.count(old)!=1:raise SystemExit(f'ABORT: unknown source anchor {rel}: {old}')
for f in (PACKAGE/'story-next-overlay/lexistyle').rglob('*'):
 if f.is_file():
  dest=app/f.relative_to(PACKAGE/'story-next-overlay/lexistyle')
  if dest.exists() and dest.read_bytes()!=f.read_bytes():raise SystemExit(f'ABORT: brand asset collision {dest}')
for f in (PACKAGE/'story-next-overlay/lexistyle').rglob('*'):
 if f.is_file():
  dest=app/f.relative_to(PACKAGE/'story-next-overlay/lexistyle');dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(f,dest)
for rel,old,new in checks:
 p=app/rel;s=p.read_text('utf-8')
 if new not in s:p.write_text(s.replace(old,new),'utf-8')
print('SUCCESS: v5 story theme applied to commerce source. Next: npm ci && npm run build, sandbox checkout tests, SQL review, Vercel preview deployment.')
