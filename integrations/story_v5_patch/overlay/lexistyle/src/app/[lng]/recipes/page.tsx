import type { Metadata } from "next";
import Link from "next/link";
import { GARAK_RECIPES } from "@/lib/garak/recipes";
import { RecipeBrowser } from "@/components/garak/recipe-browser";
export const metadata: Metadata = { title: "뚝딱 레시피 132선", description: "가락한상의 수산·축산·청과 식재료로 만드는 132가지 쉬운 요리와 장보기 연결" };
export default async function RecipesPage({params}:{params:Promise<{lng:string}>}) {
  const { lng } = await params;
  return <div className="mx-auto max-w-6xl px-4 pb-16 pt-8">
    <nav className="mb-5 text-sm text-dim"><Link href={`/${lng}`}>쇼핑몰 홈</Link> / 뚝딱 레시피</nav>
    <div className="mb-7 rounded-3xl bg-[#0e2431] px-6 py-9 text-white md:px-10"><p className="text-sm text-[#9ad2e9]">가락한상 푸드 매거진</p><h1 className="mt-2 text-3xl font-bold md:text-5xl">오늘은 뭘 먹을까? 뚝딱 레시피</h1><p className="mt-3 max-w-xl text-sm leading-7">신선한 수산·축산·청과 식재료로 즐기는 132가지 홈쿡. 마음에 드는 레시피에서 실제 판매 상품을 확인해 보세요.</p><div className="mt-5 flex flex-wrap gap-2"><Link href={`/${lng}/category/beauty`} className="rounded-lg bg-white px-4 py-2 text-sm font-semibold text-[#0e2431]">수산물 쇼핑</Link><Link href={`/${lng}/category/life`} className="rounded-lg border border-white px-4 py-2 text-sm">축산물 쇼핑</Link><Link href={`/${lng}/category/kids`} className="rounded-lg border border-white px-4 py-2 text-sm">농산물 쇼핑</Link></div></div>
    <RecipeBrowser recipes={GARAK_RECIPES} lng={lng}/>
    <p className="mt-8 text-sm leading-6 text-dim">레시피는 편집 초안이며 요리 전문가의 조리·안전 검수가 필요합니다. 이미지는 AI 음식 연출 시안으로 해당 메뉴의 실제 완성 사진과 다를 수 있습니다.</p>
  </div>;
}
