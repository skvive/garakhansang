import Link from "next/link";
import Image from "next/image";
/** Garak market story #2 — hero is merchandised, not a fashion carousel. */
export function GarakStoryHero() {
  return <>
    <section className="garak-story-next-hero" aria-label="가락시장 스토리 쇼핑몰">
      <div className="garak-story-next-hero-inner">
        <div className="garak-story-next-copy">
          <p className="garak-next-eyebrow">가락시장의 좋은 식재료를 식탁으로</p>
          <h1>가락시장의 신선함을<br/>우리 집 식탁으로.</h1>
          <p>수산을 중심으로 축산과 제철 농산까지. 오늘 좋은 식재료를 고르고, 그 뒤에 담긴 상인의 이야기도 만나보세요.</p>
          <div className="garak-next-actions"><Link href="/ko/category/beauty">지금 장보기</Link><Link href="/ko/recipes">뚝딱 레시피 보기</Link></div>
          <small>상품별 원산지·규격·재고·배송 조건은 판매 정보 확인 후 표시합니다. AI 연출 이미지</small>
        </div>
        <div className="garak-story-next-feature">
          <Image alt="완성 요리 연출 사진" src="/garak-recipes/recipe-002.webp" width={240} height={145} unoptimized />
          <b>오늘 뭐 해 먹지?</b><p>132가지 뚝딱 요리와 장보기</p><Link href="/ko/recipes">레시피 전체 보기 →</Link>
        </div>
      </div>
    </section>
    <nav className="garak-story-next-shortcuts" aria-label="상품과 콘텐츠 바로가기">
      {[
        {icon:"🐟",name:"수산",href:"/ko/category/beauty"},
        {icon:"🥩",name:"축산",href:"/ko/category/life"},
        {icon:"🥬",name:"농산·청과",href:"/ko/category/kids"},
        {icon:"🍱",name:"한상 세트",href:"/ko/category/fashion"},
        {icon:"🍳",name:"132가지 레시피",href:"/ko/recipes"},
        {icon:"👩‍🍳",name:"요리사",href:"/ko/partners"},
        {icon:"🏪",name:"상인 이야기",href:"/ko/community"},
        {icon:"📣",name:"홍보광장",href:"/ko/market-board"},
      ].map(x=><Link key={x.name} href={x.href}><span aria-hidden>{x.icon}</span>{x.name}</Link>)}
    </nav>
  </>;
}
