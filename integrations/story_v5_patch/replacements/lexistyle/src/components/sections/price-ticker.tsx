import Link from "next/link";
import { products } from "@/lib/dummy-data";
/** 실거래 데이터가 없는 동안 실제 경매 시세로 표시하지 않는다. */
export function PriceTicker(){
const items=products.slice(0,7);
return <section className="bg-[#0e2431] px-4 py-3 text-white" aria-label="판매가격 안내"><div className="mx-auto flex max-w-6xl flex-wrap items-center gap-4"><Link href="/ko/prices" className="shrink-0 rounded-lg bg-white/15 px-3 py-1 font-bold">예시 판매가 · 시세 아님</Link><div className="flex flex-1 gap-5 overflow-x-auto whitespace-nowrap">{items.map(p=><Link href={`/ko/product/${p.slug}`} key={p.slug} className="text-sm hover:underline">{p.name.split("(")[0].trim()} <b>{p.price.toLocaleString("ko-KR")}원</b></Link>)}</div></div></section>;
}
