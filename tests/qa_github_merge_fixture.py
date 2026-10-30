import pathlib,tempfile,subprocess,sys,json
PACK=pathlib.Path(__file__).resolve().parents[1];merger=PACK/'tools/merge_into_github.py'
files={
'package.json':'{"name":"garak-smoke","version":"1.0.0"}',
'src/app/[lng]/page.tsx':'import { HeroEditorial } from "@/components/sections/hero-editorial";\nexport default function Home(){return <main><HeroEditorial /><CategoryChips /></main>}',
'src/app/[lng]/layout.tsx':'import "../globals.css";\nexport default function Layout(){return <body className="min-h-dvh pb-16 md:pb-0">demo</body>}',
'src/app/[lng]/product/[slug]/page.tsx':'import type { Metadata } from "next";\nimport { DutyCalculator } from "@/components/duty-calculator";\nimport { AddToLookButton } from "@/components/looks/AddToLookButton";\nexport default function P(){return <article>        <DutyCalculator price={price} />        <AddToLookButton slug={product.slug} /><p>관세 포함가 · 결제 후 추가 청구 없음</p>      <section id="reviews">Reviews</section></article>}',
'src/app/[lng]/category/[cat]/page.tsx':'export const description="LEXI가 고른 상품, 관세 포함 가격으로 해외에서 바로 배송합니다.";',
'src/app/[lng]/prices/page.tsx':'const prevPrice = 123;export default function Page(){return <main>fake ticker</main>}',
'src/app/[lng]/community/page.tsx':'export default function Page(){return <div>#LEXILOOK 실착 사진 착용한 사진</div>}',
'src/components/site-header.tsx':'export const GNB=[\n  { label: "점포관", href: "/brands" },\n];\nexport const placeholder="브랜드, 상품, #LEXILOOK 검색";',
'src/components/sections/quick-links.tsx':'const x=[\n  { key: "food" as const, label: "홈마카세", href: "/subscription" },\n];',
'src/components/sections/price-ticker.tsx':'export const label="시세급락";'
}
def call(args,cwd):
 p=subprocess.run(args,cwd=cwd,text=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
 return p.returncode,p.stdout
with tempfile.TemporaryDirectory() as td:
 root=pathlib.Path(td)/'garak';root.mkdir();app=root/'lexistyle'
 for name,s in files.items():
  f=app/name;f.parent.mkdir(parents=True,exist_ok=True);f.write_text(s,encoding='utf8')
 for cmd in [['git','init','-q'],['git','config','user.email','test@example.test'],['git','config','user.name','QA'],['git','add','.'],['git','commit','-qm','baseline']]:
  ec,s=call(cmd,root);assert ec==0,(cmd,s)
 ec,s=call([sys.executable,str(merger),str(root),'--dry-run'],root)
 print('DRYRUN',ec,s[-1000:]);assert ec==0
 assert 'RecipePromoStrip' not in (app/'src/app/[lng]/page.tsx').read_text('utf8')
 ec,s=call([sys.executable,str(merger),str(root),'--apply'],root)
 print('REJECT MAIN',ec,s[-500:]);assert ec!=0
 ec,s=call(['git','checkout','-qb','feature/garak-onepack'],root);assert ec==0,s
 ec,s=call([sys.executable,str(merger),str(root),'--apply'],root)
 print('APPLY',ec,s[-1200:]);assert ec==0,s
 page=(app/'src/app/[lng]/page.tsx').read_text('utf8');assert 'GarakStoryHero' in page and 'RecipePromoStrip' in page
 ec,s=call([sys.executable,str(merger),str(root),'--dry-run'],root)
 print('RE-DRYRUN',ec,s[-700:]);assert ec==0,s;assert '"files_changed": 0' in s,s[-2000:]
print('ALL MERGE QA PASSED')
