import Link from "next/link";
import { products, productMeta, type Product } from "@/lib/dummy-data";
import { departmentBySlug } from "@/lib/departments";

/** 중요: 임의 전일 대비/등락률을 생성하지 않는 예시 판매가격 안내판. */
export const metadata = {title:"상품 가격 안내 | 가락한상",description:"수산·축산·청과 상품의 예시 판매가격. 실제 당일 경매 시세와 다르며 주문 확정 시 판매가격을 확인해 주세요."};
const CATS=["beauty","fashion","life","kids","others","digital"];
function unitPrice(p:Product){const match=p.name.match(/(\d+(?:\.\d+)?)\s*(kg|g)/i);if(!match)return null;const g=match[2].toLowerCase()==="kg"?1000*Number(match[1]):Number(match[1]);return g>0?Math.round((p.price/g)*100):null;}
export default async function PricesPage({searchParams}:{searchParams:Promise<{cat?:string}>}){
const {cat}=await searchParams;const active=cat&&CATS.includes(cat)?cat:undefined;
const map:Record<string,string[]>={beauty:["beauty"],fashion:["women-clothing"],life:["home-garden"],kids:["kids"],others:["pet"],digital:["electronics"]};
const listed=products.filter(p=>!active||map[active]?.includes(String(p.category)));
return <div className="mx-auto max-w-6xl px-4 py-8"><h1 className="text-3xl font-bold">상품 가격 안내</h1><p className="mt-3 rounded-xl bg-[#fff4dd] p-4 text-sm leading-6">이 화면에는 데모 상품 데이터의 예시 판매가격이 표시됩니다. <strong>실제 가락시장 경매 시세가 아닙니다.</strong> 확인된 전일 경매 기록이 없어 가격 등락률은 표시하지 않습니다. 최종 가격·중량·출고 상태는 상품 상세와 결제 단계에서 확인하세요.</p>
<div className="my-5 flex flex-wrap gap-2"><Link className="rounded-full border p-2" href="/ko/prices">전체</Link>{CATS.map(c=><Link key={c} href={`/ko/prices?cat=${c}`} className={`rounded-full border px-3 py-2 ${active===c?"bg-[#0e5c8c] text-white":"bg-paper"}`}>{departmentBySlug(c)?.label??c}</Link>)}</div>
<div className="overflow-hidden rounded-xl border border-line"><div className="grid grid-cols-[minmax(0,1fr)_auto] gap-3 bg-fog p-4 text-sm font-semibold"><span>상품</span><span>참고 판매가</span></div>{listed.map(p=><Link key={p.slug} href={`/ko/product/${p.slug}`} className="grid grid-cols-[minmax(0,1fr)_auto] gap-3 border-t border-line p-4 hover:bg-fog"><span className="min-w-0"><strong className="block truncate">{p.name}</strong><small className="text-dim">{p.brand} {productMeta[p.slug]?.fatGrade?` · ${productMeta[p.slug].fatGrade}`:""}</small></span><span className="text-right font-bold">{p.price.toLocaleString("ko-KR")}원<small className="block font-normal text-dim">{unitPrice(p)?`100g당 ${unitPrice(p)?.toLocaleString("ko-KR")}원`:"중량 확인 필요"}</small></span></Link>)}</div></div>;
}
