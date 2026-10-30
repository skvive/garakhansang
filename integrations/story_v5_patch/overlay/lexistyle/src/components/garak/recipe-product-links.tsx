import Link from "next/link";
import { recipesForProduct } from "@/lib/garak/recipes";
/** Existing commerce PDP stays authoritative: these links never add a fake cart item. */
export function RecipeProductLinks({ slug, lng }: { slug: string; lng: string }) {
  const found = recipesForProduct(slug);
  if (!found.length) return null;
  return <section className="mx-auto max-w-6xl px-4 py-9" aria-label="이 상품으로 만들 수 있는 요리">
    <div className="mb-4 flex items-center justify-between"><h2 className="text-xl font-bold">이 재료로 만드는 쉬운 요리</h2><Link href={`/${lng}/recipes`} className="text-sm underline">레시피 전체 보기</Link></div>
    <div className="grid grid-cols-2 gap-3 md:grid-cols-5">{found.map(r=><Link key={r.id} href={`/${lng}/recipes/${r.id}`} className="overflow-hidden rounded-xl border border-line bg-paper"><img loading="lazy" alt={`${r.title} AI 연출 시안`} src={`/garak-recipes/${r.id}.webp`} className="aspect-square w-full object-cover"/><div className="p-3"><p className="font-semibold">{r.title}</p><p className="mt-1 text-xs text-dim">{r.time}분</p></div></Link>)}</div>
  </section>;
}
