import Link from "next/link";
import { db,hasDb } from "@/db";
import {garakBoardPosts} from "@/db/garak-board-schema";
import {desc,eq} from "drizzle-orm";
import {MarketBoardForm} from "@/components/garak/market-board-form";
export const dynamic="force-dynamic";
export const metadata={title:"상인·유통·협회 홍보 게시판"};
export default async function MarketBoard({params}:{params:Promise<{lng:string}>}){
 const{lng}=await params;
 let items:{id:string;category:string;title:string;body:string}[]=[];
 if(hasDb())try{items=await db().select({id:garakBoardPosts.id,category:garakBoardPosts.category,title:garakBoardPosts.title,body:garakBoardPosts.body}).from(garakBoardPosts).where(eq(garakBoardPosts.status,"approved")).orderBy(desc(garakBoardPosts.createdAt)).limit(40)}catch{/*migration pending*/}
 return <div className="mx-auto max-w-5xl px-4 py-10"><nav className="text-sm text-dim"><Link href={`/${lng}`}>쇼핑몰</Link> / 홍보 게시판</nav><h1 className="mt-5 text-3xl font-bold">가락시장 홍보 광장</h1><p className="mt-3 text-sm text-dim">상인·유통업체·협회·요리사 소개. 미승인 게시글은 공개되지 않습니다. 유료 광고는 별도로 표시합니다.</p><div className="mt-7 grid gap-4">{items.length?items.map(it=><article key={it.id} className="rounded-xl border border-line p-5"><p className="text-xs text-dim">{it.category}</p><h2 className="mt-1 font-bold">{it.title}</h2><p className="mt-3 whitespace-pre-wrap text-sm leading-7">{it.body}</p></article>):<p className="rounded-xl bg-fog p-8">현재 승인된 홍보 게시물이 없습니다. 운영 설정 후 검수된 글만 게시합니다.</p>}</div><MarketBoardForm lng={lng}/></div>;
}
