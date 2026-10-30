import Link from "next/link";
import type { Metadata } from "next";
import { notFound } from "next/navigation";
import { findGarakRecipe } from "@/lib/garak/recipes";
import { getProductBySlug } from "@/lib/catalog";
type Params = {params:Promise<{lng:string;id:string}>};
export const dynamic = "force-dynamic"; // Live catalog links must not freeze at build time.
export async function generateMetadata({params}:Params):Promise<Metadata>{const {id}=await params;const r=findGarakRecipe(id);return {title:r?`${r.title} | 뚝딱 레시피`:"레시피",description:r?.intro};}
export default async function RecipeDetail({params}:Params){
  const {lng,id}=await params;
  const r=findGarakRecipe(id);
  if(!r)notFound();
  let product:Awaited<ReturnType<typeof getProductBySlug>>=null;
  try { product=await getProductBySlug(r.sku); } catch { /* DB offline: no false buy CTA */ }
  return <article className="mx-auto max-w-6xl px-4 pb-20 pt-6">
    <nav className="mb-5 text-sm text-dim"><Link href={`/${lng}`}>쇼핑몰</Link> / <Link href={`/${lng}/recipes`}>레시피</Link> / {r.title}</nav>
    <div className="grid gap-7 md:grid-cols-2"><div><img alt={`${r.title} AI 음식 연출 이미지 (완성 사진 검수 전)`} src={`/garak-recipes/${r.id}.webp`} className="w-full rounded-2xl object-cover"/><p className="mt-2 text-xs text-dim">AI 음식 연출 시안 · 실제 완성 요리와 다를 수 있음 · 이미지 일치 검수 전</p></div>
      <div><p className="text-sm font-semibold text-[#0e5c8c]">{r.category} · 약 {r.time}분 · {r.servings}인분</p><h1 className="mt-2 text-3xl font-bold text-ink md:text-4xl">{r.title}</h1><p className="mt-4 leading-7 text-dim">{r.intro}</p>
        <section className="mt-7 rounded-2xl bg-fog p-5"><h2 className="text-lg font-bold">준비 재료</h2><ul className="mt-3 list-inside list-disc space-y-2 text-sm">{r.ingredients.map((it,i)=><li key={i}>{it}</li>)}</ul></section>
        <section className="mt-5 rounded-2xl border border-[#0e5c8c]/25 p-5"><h2 className="text-lg font-bold">가락한상에서 재료 찾기</h2>{product?<><p className="mt-2 text-sm">연결 상품: {product.name}</p><Link href={`/${lng}/product/${product.slug}`} className="mt-4 inline-flex rounded-xl bg-[#0e5c8c] px-6 py-3 font-bold text-white">상품 상세·재고·가격 확인</Link></>:<><p className="mt-2 text-sm text-dim">이 레시피와 연결된 판매 상품이 확인되지 않았습니다. 카테고리에서 재고를 확인해 주세요.</p><Link href={`/${lng}/category/${r.category==="수산"?"beauty":r.category==="축산"?"life":"kids"}`} className="mt-4 inline-flex rounded-xl bg-[#0e5c8c] px-6 py-3 font-bold text-white">상품 찾아보기</Link></>}</section>
      </div></div>
    <section className="mt-9"><h2 className="text-2xl font-bold">조리 순서</h2><ol className="mt-5 space-y-4">{r.steps.map((s,i)=><li key={i} className="flex gap-4 rounded-xl border border-line bg-paper p-4"><span className="flex size-9 shrink-0 items-center justify-center rounded-full bg-[#0e5c8c] font-bold text-white">{i+1}</span><p className="pt-1 leading-7">{s}</p></li>)}</ol></section>
    <section className="mt-7 rounded-xl bg-[#fff7e8] p-5"><h2 className="font-bold">식품안전·조리 안내</h2><p className="mt-2 text-sm leading-7">{r.safety}</p><p className="mt-3 text-xs">본 레시피는 요리 전문가의 검증을 거치기 전이며 원산지·신선도·중량·알레르기 정보는 실제 상품 상세에서 확인하세요.</p></section>
    <div className="mt-8"><Link href={`/${lng}/recipes`} className="rounded-xl border border-line px-5 py-3">다른 레시피 보기</Link></div>
  </article>;
}
