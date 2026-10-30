import Link from "next/link";
import { GARAK_RECIPES } from "@/lib/garak/recipes";
export function RecipePromoStrip(){
const selected=[GARAK_RECIPES[0],GARAK_RECIPES[60],GARAK_RECIPES[88]];
return <section className="mx-auto max-w-6xl px-4 py-10" aria-label="가락한상 레시피"><div className="mb-5 flex items-center justify-between"><div><p className="text-sm font-semibold text-[#0e5c8c]">가락한상 푸드매거진</p><h2 className="mt-1 text-2xl font-bold">장보기부터 요리까지, 뚝딱 132선</h2></div><Link href="/ko/recipes" className="text-sm underline">전체보기</Link></div><div className="grid grid-cols-3 gap-3">{selected.map(r=><Link key={r.id} href={`/ko/recipes/${r.id}`} className="overflow-hidden rounded-xl border border-line"><img src={`/garak-recipes/${r.id}.webp`} alt={`${r.title} AI 시안`} loading="lazy" className="aspect-square w-full object-cover"/><p className="p-3 text-sm font-semibold">{r.title} · {r.time}분</p></Link>)}</div><p className="mt-3 text-xs text-dim">AI 연출 이미지 · 조리 실증 전 시안</p></section>;
}
