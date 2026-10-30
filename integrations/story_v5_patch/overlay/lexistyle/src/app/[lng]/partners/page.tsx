import Link from "next/link";
import type { Metadata } from "next";
export const metadata:Metadata={title:"상인·요리사·협회 홍보관",description:"가락시장 상인, 생산자, 유통사, 요리사, 단체의 협력·홍보 공간"};
export default async function PartnersPage({params}:{params:Promise<{lng:string}>}){
const {lng}=await params;
const items=[
{title:"가락시장 상인",body:"판매 점포의 실제 상품과 브랜드 스토리를 소개합니다. 노출 전 점포·사업자 확인이 필요합니다.",href:`/${lng}/brands`,action:"점포관 살펴보기"},
{title:"요리사·Blogger",body:"본인 동의를 받은 Blogger 콘텐츠와 레시피를 연결합니다. 계정별 OAuth·승인 DB 연동은 운영 설정이 필요합니다.",href:`/${lng}/recipes`,action:"레시피 보기"},
{title:"유통업체·협회",body:"물류·유통·협회의 제휴 제안과 공지 공간입니다. 신청서는 관리자 확인 후 공개합니다.",href:`/${lng}/market-board`,action:"홍보 게시판"},
{title:"쿠팡·배달 플랫폼",body:"판매채널 입점은 각 사 공식 절차와 별도 계약이 우선입니다. 자동 입점을 보장하지 않습니다.",href:`/${lng}/market-board`,action:"연동 안내"}
];return <div className="mx-auto max-w-6xl px-4 py-10"><nav className="mb-4 text-sm text-dim"><Link href={`/${lng}`}>쇼핑몰</Link> / 홍보관</nav><h1 className="text-3xl font-bold">가락시장 상인·요리사·협회 홍보관</h1><p className="mt-3 text-dim">실제 입점·제휴 관계가 확인된 정보만 공개합니다. 홍보물은 광고·협찬 표시를 구분합니다.</p><div className="mt-8 grid gap-4 md:grid-cols-2">{items.map(it=><section key={it.title} className="rounded-2xl border border-line p-6"><h2 className="text-xl font-bold">{it.title}</h2><p className="mt-3 text-sm leading-7 text-dim">{it.body}</p><Link className="mt-4 inline-block rounded-xl bg-[#0e5c8c] px-5 py-3 text-white" href={it.href}>{it.action}</Link></section>)}</div></div>;
}
