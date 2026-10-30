#!/usr/bin/env python3
"""Overlay reviewed Next.js features onto a local skvive/garak checkout.
Does not deploy, does not overwrite DB, does not alter Git without user action.
Usage: python integrate_into_garak.py /path/to/garak
"""
from pathlib import Path
import sys, shutil

ROOT=Path(__file__).resolve().parent
assert len(sys.argv)==2,"Usage: python integrate_into_garak.py /path/to/garak"
checkout=Path(sys.argv[1]).resolve()
app=checkout/'lexistyle'
if not (app/'package.json').exists() or not (app/'src/app/[lng]/page.tsx').exists():
 raise SystemExit("ABORT: expected skvive/garak with lexistyle/ Next.js app")

def safe_patch(relative,needle,replacement):
 path=app/relative;old=path.read_text('utf-8')
 if replacement in old:return "already-patched"
 if old.count(needle)<1:raise SystemExit(f"ABORT: missing anchor in {relative}. No changes made to this file")
 path.write_text(old.replace(needle,replacement),'utf-8')
 return 'patched'

# Preflight all existing source anchors before doing any writes.
checks=[
('src/app/[lng]/page.tsx','<CategoryChips />','<CategoryChips />\n      <RecipePromoStrip />'),
('src/app/[lng]/product/[slug]/page.tsx','      <section id="reviews"','      <RecipeProductLinks slug={product.slug} lng={lng} />\n      <section id="reviews"'),
('src/components/site-header.tsx','  { label: "점포관", href: "/brands" },','  { label: "점포관", href: "/brands" },\n  { label: "레시피", href: "/recipes" },\n  { label: "홍보관", href: "/partners" },'),
('src/components/sections/quick-links.tsx','  { key: "food" as const, label: "홈마카세", href: "/subscription" },','  { key: "food" as const, label: "뚝딱 레시피", href: "/recipes" },'),
('src/app/[lng]/product/[slug]/page.tsx','        <DutyCalculator price={price} />','        {/* 국내 쇼핑몰에는 관세 계산기 노출 안 함 */}'),
('src/app/[lng]/product/[slug]/page.tsx','        <AddToLookButton slug={product.slug} />','        {/* 기존 패션 룩북 액션 비노출 */}'),
('src/app/[lng]/product/[slug]/page.tsx','관세 포함가 · 결제 후 추가 청구 없음','배송비·원산지·중량은 판매 조건을 확인해 주세요'),
('src/app/[lng]/community/page.tsx','#LEXILOOK','가락한상 이야기'),
('src/app/[lng]/community/page.tsx','실착 사진','상품 사진'),
('src/app/[lng]/community/page.tsx','착용한 사진','받으신 상품 사진'),
('src/components/site-header.tsx','브랜드, 상품, #LEXILOOK 검색','수산·축산·청과 상품 검색'),
]
for rel,needle,rep in checks:
 src=(app/rel).read_text('utf-8')
 if src.count(needle)<1 and rep not in src:raise SystemExit(f"ABORT: mismatched or stale repository anchor {rel}: {needle[:45]}")
for src in (ROOT/'overlay/lexistyle').rglob('*'):
 if src.is_file():
  rel=src.relative_to(ROOT/'overlay/lexistyle');target=app/rel
  if target.exists() and target.read_bytes()!=src.read_bytes():raise SystemExit(f"ABORT: existing collision {target}")
# Check 2 additional sensitive source replacements (no speculative market price changes).
replchecks=[
 ("src/app/[lng]/prices/page.tsx","const prevPrice ="),
 ("src/components/sections/price-ticker.tsx","시세급락"),
]
for rel,anchor in replchecks:
 old=(app/rel).read_text("utf-8")
 if anchor not in old and old != (ROOT/"replacements/lexistyle"/rel).read_text("utf-8"):
  raise SystemExit(f"ABORT: price source changed; manual review required: {rel}")
# Apply copy after verification.
for src in (ROOT/'overlay/lexistyle').rglob('*'):
 if src.is_file():
  dest=app/src.relative_to(ROOT/'overlay/lexistyle');dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(src,dest)
for src in (ROOT/'replacements/lexistyle').rglob('*'):
 if src.is_file():
  dest=app/src.relative_to(ROOT/'replacements/lexistyle');dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(src,dest)
for rel,needle,rep in checks:print(safe_patch(rel,needle,rep),rel)
# Imports use matching anchors, idempotently.
safe_patch('src/app/[lng]/page.tsx', 'import { HeroEditorial } from "@/components/sections/hero-editorial";', 'import { HeroEditorial } from "@/components/sections/hero-editorial";\nimport { RecipePromoStrip } from "@/components/garak/recipe-promo-strip";')
safe_patch('src/app/[lng]/product/[slug]/page.tsx','import type { Metadata } from "next";', 'import type { Metadata } from "next";\nimport { RecipeProductLinks } from "@/components/garak/recipe-product-links";')
# Remove unused imported components from the PDP after no-use replacement.
pdp=app/'src/app/[lng]/product/[slug]/page.tsx'
s=pdp.read_text('utf-8').replace('import { DutyCalculator } from "@/components/duty-calculator";\n','').replace('import { AddToLookButton } from "@/components/looks/AddToLookButton";\n','')
pdp.write_text(s,'utf-8')
# Remove demonstrably obsolete international-shopping SEO phrases.
category=app/'src/app/[lng]/category/[cat]/page.tsx'
if category.exists():
 s=category.read_text('utf-8').replace('LEXI가 고른','가락한상에서 고른').replace('관세 포함 가격으로 해외에서 바로 배송합니다.','상품별 중량·원산지·배송 조건을 확인해 주세요.')
 category.write_text(s,'utf-8')
# Separate CSS-independent home panel; commerce layout stays untouched.
print('SUCCESS: overlay installed; run npm ci && npm run build in lexistyle; apply SQL migration after review')
