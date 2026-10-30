"use client";
import { useMemo, useState } from "react";
import Link from "next/link";
import type { GarakRecipe } from "@/lib/garak/recipes";

type Props = { recipes: GarakRecipe[]; lng: string };
export function RecipeBrowser({ recipes, lng }: Props) {
  const [q, setQ] = useState("");
  const [cat, setCat] = useState("전체");
  const [sort, setSort] = useState("time");
  const shown = useMemo(() => {
    const term = q.trim().normalize("NFC").toLocaleLowerCase("ko-KR");
    const out = recipes.filter((r) => (cat === "전체" || r.category === cat) &&
      (!term || [r.title, r.main, r.intro, ...r.ingredients].join(" ").normalize("NFC").toLocaleLowerCase("ko-KR").includes(term)));
    return out.sort((a,b) => sort === "name" ? a.title.localeCompare(b.title,"ko") : a.time - b.time);
  }, [q,cat,sort,recipes]);
  return <>
    <div className="rounded-2xl border border-line bg-white p-4 shadow-sm">
      <div className="flex flex-col gap-3 md:flex-row">
        <label className="flex-1"><span className="sr-only">레시피 검색</span><input value={q} onChange={e => setQ(e.target.value)} type="search" placeholder="예: 광어, 소불고기, 감자" className="w-full rounded-xl border border-line p-3 text-ink" /></label>
        <label><span className="sr-only">정렬</span><select value={sort} onChange={e=>setSort(e.target.value)} className="rounded-xl border border-line bg-white p-3"><option value="time">빠른 조리순</option><option value="name">가나다순</option></select></label>
      </div>
      <div className="mt-3 flex flex-wrap gap-2" aria-label="레시피 카테고리">{["전체", "수산", "축산", "농산"].map(x=><button key={x} type="button" aria-pressed={cat===x} onClick={()=>setCat(x)} className={`rounded-full px-4 py-2 text-sm ${cat===x?"bg-[#0e5c8c] text-white":"bg-fog text-ink"}`}>{x}</button>)}</div>
    </div>
    <p aria-live="polite" className="my-4 text-sm text-dim">총 {shown.length}가지 요리 · 요리 전문가 검수 전 콘텐츠</p>
    {shown.length===0?<p className="rounded-xl bg-fog p-8 text-center">검색 결과가 없습니다. 다른 재료를 입력해 주세요.</p>:
      <div className="grid grid-cols-2 gap-3 md:grid-cols-3 lg:grid-cols-4">{shown.map(r=><Link key={r.id} href={`/${lng}/recipes/${r.id}`} className="overflow-hidden rounded-2xl border border-line bg-paper transition-shadow hover:shadow-lg"><img loading="lazy" src={`/garak-recipes/${r.id}.webp`} alt={`${r.title} AI 조리 콘셉트 이미지`} className="aspect-square w-full object-cover" /><div className="p-3"><p className="text-xs text-dim">{r.category} · {r.time}분 · {r.servings}인분</p><h2 className="mt-1 font-bold text-ink">{r.title}</h2><p className="mt-1 text-xs text-dim">재료로 상품 찾기</p></div></Link>)}</div>}
  </>;
}
