(() => {
'use strict';
const CAT = {
  seafood: {label:'수산', zone:'수산', photo:'assets/editorial/seafood.webp', href:'category/seafood.html'},
  meat: {label:'축산', zone:'축산', photo:'assets/editorial/meat.webp', href:'category/meat.html'},
  produce: {label:'청과', zone:'청과', photo:'assets/editorial/fruit.webp', href:'category/produce.html'},
  sets: {label:'한상', zone:'먹거리', photo:'assets/editorial/kitchen.webp', href:'category/sets.html'},
  extras: {label:'먹거리', zone:'먹거리', photo:'assets/editorial/kitchen.webp', href:'category/extras.html'}
};
const ZONE_CATS = {수산:['seafood'], 청과:['produce'], 축산:['meat'], 먹거리:['sets','extras']};
const BUILDINGS = [
  {id:'sales', name:'가락몰 판매동', floors:'B2 축산부산물 · B1 청과 · 1F 수산·축산 · 2F 식자재 · 3F 상가', note:'소비자 장보기 중심'},
  {id:'produce', name:'청과 도매구역', floors:'1F', note:'도매 기능 안내 · 동 경계 미확정'},
  {id:'seafood', name:'수산 도매구역', floors:'1F', note:'도매 기능 안내 · 동 경계 미확정'},
  {id:'theme', name:'테마 1~5관', floors:'B1~3F', note:'식음·식문화 테마 · 공식 배치 확인 필요'},
  {id:'office', name:'가락몰 업무동', floors:'1F~5F', note:'도서관·컨벤션·편의'}
];
const COUPON_COPY = {
  seafood: {title:'수산 장보기 체험권', benefit:'3,000원 할인', description:'3만 원 이상 장보기 조건을 가정한 시연 쿠폰'},
  meat: {title:'축산 한상 체험 쿠폰', benefit:'5,000원 할인', description:'5만 원 이상 구매를 가정한 시연 쿠폰'},
  produce: {title:'제철 과일 체험 쿠폰', benefit:'10% 할인', description:'시연용 청과 혜택'},
  sets: {title:'한상 세트 체험 쿠폰', benefit:'2,000원 할인', description:'시연용 방문 쿠폰'},
  extras: {title:'곁들임 체험 쿠폰', benefit:'1,000원 할인', description:'소스·양념 시연 쿠폰'}
};
const $ = (s, root=document) => root.querySelector(s);
const $$ = (s, root=document) => [...root.querySelectorAll(s)];
const page = document.body.dataset.page || 'home';
const currency = n => Number(n).toLocaleString('ko-KR') + '원';
const safe = s => String(s ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const storage = (key, initial) => { try { return JSON.parse(localStorage.getItem('garak-brand-'+key)) || initial; } catch { return initial; } };
const save = (key, v) => localStorage.setItem('garak-brand-'+key, JSON.stringify(v));
const liked = () => storage('likes', []);
const wallet = () => storage('wallet', []);
const routes = {home:'index.html', map:'market-map.html', stores:'stores.html', coupons:'coupons.html', events:'events.html', merchant:'merchant-center.html', guide:'market-guide.html'};
const img = p => 'assets/images/' + p + '.webp';
const mascot = (cls='') => `<img class="mascot ${cls}" src="assets/brand/mascot.webp" alt="가락한상 상인 마스코트"/>`;
const logo = `<a class="logo" href="index.html" aria-label="가락한상 홈"><img class="logo-wordmark" src="assets/brand/logo-lockup.webp" alt="가락한상"/><span class="brand-strapline">가락시장 30년 전통의 맛 <small>탐험 · 장보기 · 시연</small></span></a>`;

function shopsFromProducts() {
  const list = window.GARAK_PRODUCTS || [];
  const map = new Map();
  list.forEach(p => {
    const id = p.merchant;
    if (!map.has(id)) {
      const meta = CAT[p.category] || CAT.extras;
      map.set(id, {
        id,
        name: p.merchant,
        category: meta.label,
        catKey: p.category,
        zone: meta.zone,
        photo: img(p.image),
        intro: p.summary || '가락시장 시연 상인입니다.',
        products: [],
        coupon: 'c-' + (p.category || 'extras')
      });
    }
    map.get(id).products.push({name:p.name, price:p.price, slug:p.slug, image:p.image});
  });
  return [...map.values()];
}
function couponsFromShops(shops) {
  const seen = new Set();
  return shops.map(s => {
    if (seen.has(s.coupon)) return null;
    seen.add(s.coupon);
    const copy = COUPON_COPY[s.catKey] || COUPON_COPY.extras;
    return {id:s.coupon, shopId:s.id, ...copy};
  }).filter(Boolean);
}
function eventsFromCats() {
  return [
    {id:1, tag:'제철', type:'청과', title:'제철 과일 탐험 주간', subtitle:'청과 식재료와 레시피를 함께 살펴보는 가상 프로모션', image:'assets/editorial/fruit.webp', href:'category/produce.html'},
    {id:2, tag:'체험', type:'수산', title:'우리 바다 한상 발견', subtitle:'회·갑각류와 뚝딱 레시피로 이어지는 수산 기획', image:'assets/editorial/seafood.webp', href:'category/seafood.html'},
    {id:3, tag:'한상', type:'먹거리', title:'가락한상 시장 미식 산책', subtitle:'한상 세트와 곁들임으로 구성하는 가상 코스', image:'assets/editorial/kitchen.webp', href:'category/sets.html'},
    {id:4, tag:'상인', type:'축산', title:'상인이 소개하는 한우', subtitle:'정육 상품과 상인 이야기를 묶은 시안', image:'assets/editorial/meat.webp', href:'category/meat.html'}
  ];
}

const D = { shops: shopsFromProducts() };
D.coupons = couponsFromShops(D.shops);
D.events = eventsFromCats();
const store = id => D.shops.find(s => s.id === id);
const coupon = id => D.coupons.find(c => c.id === id);

function header() {
  const nav = [['home','홈'],['map','시장 지도'],['stores','매장 찾기'],['coupons','쿠폰'],['events','이벤트'],['guide','시장 이야기'],['merchant','상인센터']];
  return `<div class="top-notice">좋은 먹거리가 만나는 곳, <b>가락한상</b>에서 새로운 발견을! <span>· 매장·상품·쿠폰은 시연 데이터</span></div>
  <header class="site-header"><div class="container head-inner">${logo}
    <form class="search-global" id="global-search"><label class="sr-only" for="search-top">매장 또는 상품 검색</label>
    <input id="search-top" name="q" placeholder="어떤 시장의 이야기를 찾으세요?" autocomplete="off"/><button aria-label="검색" type="submit">⌕</button></form>
    <div class="head-actions">
      <a href="coupons.html">🎟️ <span>내 쿠폰 <b id="wallet-qty">0</b></span></a>
      <a href="cart.html">🛒 <span>장바구니 <b data-cart-count>0</b></span></a>
      <a href="login.html">로그인</a>
      <button id="menu-toggle" class="mobile-menu" type="button" aria-label="메뉴 열기" aria-expanded="false">☰</button>
    </div></div>
    <nav class="primary-nav" id="primary-nav" aria-label="주 메뉴"><div class="container nav-inner">
      ${nav.map(([k,v]) => `<a href="${routes[k]}" class="${page===k?'active':''}">${v}</a>`).join('')}
      <a class="nav-beta" href="category/seafood.html">장보기 →</a>
    </div></nav>
  </header>`;
}
function footer() {
  return `<footer class="site-footer"><div class="container foot-grid"><div>${logo}<p>시장의 신선함과 사람의 이야기를 더 가까이 잇습니다.<br>상품·가격·매장은 시연 데이터이며 실판매가 아닙니다.</p></div>
    <div><b>둘러보기</b><a href="stores.html">매장 찾기</a><a href="market-map.html">시장 지도</a><a href="category/seafood.html">장보기</a><a href="recipes/index.html">레시피 132</a></div>
    <div><b>혜택과 상인</b><a href="coupons.html">쿠폰 지갑</a><a href="events.html">기획전</a><a href="merchant-center.html">상인센터</a></div>
    <div><b>안내</b><p>지도와 상호·메뉴·가격은 시연용입니다. 실제 방문 전 위치·영업 여부를 확인하세요.</p><a href="map.html">Google 지도에서 가락시장 보기 ↗</a><a href="ir/index.html">브랜드·IR 자료실</a><a href="legal/privacy.html">개인정보 안내</a></div>
    </div><div class="container foot-bottom">© 2026 GARAK HANSANG · 시연 프로토타입 <span>공식 가락시장 운영 서비스 아님</span></div></footer>`;
}
function lowerNav() {
  return `<div class="bottom-nav" aria-label="모바일 메뉴">
    <a href="index.html">⌂<small>홈</small></a>
    <a href="market-map.html">⌖<small>지도</small></a>
    <a href="stores.html">▣<small>매장</small></a>
    <a href="coupons.html">🎟<small>쿠폰</small></a>
    <a href="merchant-center.html">♟<small>상인</small></a>
  </div>`;
}
function title(eyebrow,h,p=''){return `<div class="section-title"><div><span class="eyebrow">${eyebrow}</span><h2>${h}</h2>${p?`<p>${p}</p>`:''}</div></div>`;}
function card(s) {
  return `<article class="shop-card"><a class="thumb" href="store.html?id=${encodeURIComponent(s.id)}"><img src="${s.photo}" alt="${safe(s.name)} 시연 이미지" loading="lazy"><span class="photo-label">시연 이미지</span></a>
    <div class="shop-card-body"><small>${safe(s.category)} · ${safe(s.products.length)}개 상품</small>
    <div class="card-row"><a class="shop-title" href="store.html?id=${encodeURIComponent(s.id)}">${safe(s.name)}</a>
    <button class="like ${liked().includes(s.id)?'is-liked':''}" data-like="${safe(s.id)}" type="button" aria-label="관심 매장">${liked().includes(s.id)?'♥':'♡'}</button></div>
    <p>${safe(s.intro)}</p>
    <div class="card-actions"><a class="btn btn-sm btn-green" href="store.html?id=${encodeURIComponent(s.id)}">상세 보기</a>
    <button class="btn btn-sm btn-light" data-route="${safe(s.id)}">길찾기 ↗</button></div></div></article>`;
}

function home() {
  const featured = D.shops.slice(0, 8);
  return `<section class="hero" aria-labelledby="hero-heading"><div class="container hero-grid"><div class="hero-copy">
    <span class="eyebrow hero-kicker">대한민국 최대 농수산물 시장</span>
    <h1 id="hero-heading">가락시장에서<br><em>새로운 발견!</em></h1>
    <p>신선한 먹거리, 특별한 혜택. 지금 가락한상에서 만나보세요.</p>
    <div class="hero-ctas"><a class="btn btn-primary" href="stores.html">매장 둘러보기 ↗</a>
    <a class="btn btn-outline-white" href="market-map.html">시장 지도 보기</a></div>
    <div class="hero-labels"><span>✦ 시연 상인 ${D.shops.length}곳</span><span>✦ 상품 ${ (window.GARAK_PRODUCTS||[]).length }개</span><span>✦ 쿠폰·길찾기</span></div>
    </div><div class="hero-art">${mascot('hero-mascot')}<div class="quote-bubble">신선한 오늘이<br>더 맛있는 내일을 만듭니다.</div></div></div></section>
    <section class="quick container" aria-label="빠른 메뉴"><div class="quick-panel">
      ${[['📍','매장 찾기','stores.html'],['🗺️','시장 지도','market-map.html'],['🎟️','쿠폰 지갑','coupons.html'],['🍳','레시피','recipes/index.html'],['🛒','장보기','category/seafood.html'],['🏪','상인센터','merchant-center.html']]
        .map(a=>`<a href="${a[2]}"><span>${a[0]}</span><b>${a[1]}</b><small>바로가기 ↗</small></a>`).join('')}
    </div></section>
    <section class="section container">${title('TODAY AT GARAK','오늘은 어느 시장으로 갈까요?','제철 과일에서 신선한 수산, 든든한 한상까지.')}
      <div class="category-grid">${[
        ['청과','assets/editorial/fruit.webp','stores.html?category='+encodeURIComponent('청과'),'색으로 만나는 오늘'],
        ['수산','assets/editorial/seafood.webp','stores.html?category='+encodeURIComponent('수산'),'바다에서 온 신선함'],
        ['축산','assets/editorial/meat.webp','stores.html?category='+encodeURIComponent('축산'),'믿음직한 한 끼'],
        ['먹거리','assets/editorial/kitchen.webp','stores.html?category='+encodeURIComponent('먹거리'),'시장의 온기가 담긴 한상']
      ].map(a=>`<a href="${a[2]}" class="category-card"><img src="${a[1]}" alt="${a[0]} 분위기 이미지"><span>${a[0]}<small>${a[3]} ↗</small></span></a>`).join('')}</div>
    </section>
    <section class="section container"><div class="feature-split">
      <div class="feature-card feature-cream"><span class="eyebrow">DISCOVER LOCAL SHOPS</span>
        <h2>좋은 상점을 만나는<br><em>가장 따뜻한 방법</em></h2>
        <p>상인 이야기와 메뉴·쿠폰을 살펴보고 Google 지도에서 시장까지 길을 찾아보세요.</p>
        <a class="btn btn-primary" href="stores.html">추천 매장 알아보기 →</a>${mascot('feature-mascot')}</div>
      <div class="feature-card feature-dark"><span class="eyebrow">MARKET REWARDS</span>
        <h2>가락한상<br><em>쿠폰 지갑</em></h2>
        <p>매장별 시연 쿠폰을 모아두고 길찾기까지 연결해보세요.</p>
        <a class="btn btn-cream" href="coupons.html">내 쿠폰 지갑 보기 →</a>
        <div class="ticket-graphic">🎟️ <strong>좋은 오늘 할인 티켓</strong><small>사용 체험용 · 실제 결제 불가</small></div></div>
    </div></section>
    <section class="section container">${title('FEATURED MERCHANTS','가락한상이 소개하는 매장들','시연 상인입니다. 실제 입점·영업 정보는 확인이 필요합니다.')}
      <div class="shop-grid">${featured.map(s=>card(s)).join('')}</div>
      <p class="data-caution"><a class="btn btn-sm btn-primary" href="stores.html">매장 전체 보기</a> · <a class="btn btn-sm btn-light" href="category/seafood.html">상품 장보기</a></p>
    </section>
    <section class="section container"><div class="story-banner"><img src="assets/editorial/merchant.webp" alt="상인 이야기">
      <div><span class="eyebrow">THE HEART OF THE MARKET</span>
      <h2>시장을 더 즐겁게,<br>상인과 고객을 더 가깝게.</h2>
      <p>캐릭터가 안내하는 탐험, 매장 소개, 쿠폰과 132가지 레시피.</p>
      <a class="btn btn-cream" href="market-guide.html">가락한상 브랜드 이야기 →</a></div></div></section>`;
}

function stores() {
  return `<section class="page-hero page-hero-stores"><div class="container"><span class="eyebrow">GARAK STORE DIRECTORY</span>
    <h1>상점마다, 맛있는 이야기가 있어요.</h1><p>카테고리를 선택하고 가락한상 매장을 발견해보세요.</p>${mascot('page-mascot')}</div></section>
    <section class="container section" id="shop-section"><div class="filter-panel">
      <label for="store-search">매장 검색 <input id="store-search" type="search" placeholder="매장명·상품·업종 검색"/></label>
      <div class="chipbar" id="shop-filter">${['전체','수산','축산','청과','한상','먹거리'].map(c=>`<button class="chip" data-category="${c}" type="button">${c}</button>`).join('')}</div>
      <label class="toggle"><input type="checkbox" id="favorites-only"/> 관심 매장만 보기</label>
    </div>
    <div class="shop-grid" id="shop-results"></div>
    <div class="empty hidden" id="shop-empty">조건에 맞는 매장이 없습니다. <button id="reset-search" class="btn btn-sm btn-primary" type="button">전체 보기</button></div>
    <p class="data-caution">* 표기된 매장·상품·가격은 시연 데이터입니다. 실판매 정보가 아닙니다.</p></section>`;
}

function storeDetail() {
  const id = new URLSearchParams(location.search).get('id') || (D.shops[0] && D.shops[0].id);
  const s = store(id) || D.shops[0];
  if (!s) return `<section class="container section"><p>매장을 찾을 수 없습니다. <a href="stores.html">목록으로</a></p></section>`;
  const c = coupon(s.coupon);
  return `<section class="container detail-wrap"><div class="crumb"><a href="index.html">홈</a> / <a href="stores.html">매장 찾기</a> / ${safe(s.name)}</div>
    <div class="detail-grid"><div><div class="detail-photo"><img src="${s.photo}" alt="${safe(s.name)}"><span class="photo-label">시연 이미지 · 실제 점포 사진 아님</span></div>
      <div class="detail-thumbs">${s.products.slice(0,4).map(p=>`<img src="${img(p.image)}" alt="${safe(p.name)}">`).join('')}</div></div>
      <div class="detail-content"><span class="eyebrow">가락한상 매장도감 / ${safe(s.category)}</span>
      <h1>${safe(s.name)}</h1><div class="demo-tag">시연 상점 · 실입점·위치 미검증</div>
      <p class="detail-intro">${safe(s.intro)}</p>
      <dl class="store-meta"><div><dt>업종</dt><dd>${safe(s.category)}</dd></div>
      <div><dt>구역</dt><dd>${safe(s.zone)} (안내)</dd></div>
      <div><dt>층·호실</dt><dd>미검증 · 현장 확인</dd></div>
      <div><dt>상품</dt><dd>${s.products.length}개 시연</dd></div>
      <div><dt>주소</dt><dd>서울 송파구 양재대로 932 (시장 공통)</dd></div>
      <div><dt>좌표</dt><dd>점포별 GPS 미확보</dd></div></dl>
      <div class="detail-ctas">${c?`<button class="btn btn-primary" data-claim="${c.id}" type="button">🎟️ 쿠폰 받기</button>`:''}
        <button class="btn btn-secondary" data-route="${safe(s.id)}" type="button">📍 Google 길찾기</button>
        <button class="btn btn-outline" data-like="${safe(s.id)}" type="button">♡ 찜하기</button>
        <a class="btn btn-light" href="category/${s.catKey==='produce'?'produce':s.catKey==='meat'?'meat':s.catKey==='sets'?'sets':s.catKey==='extras'?'extras':'seafood'}.html">상품 목록</a>
      </div>
      <div class="mascot-tip">${mascot('tip-mascot')}<div><b>가락한상이 알려드려요!</b><p>Google 지도는 시장 입구까지 안내해요. 정확한 동·층·호실은 현장 확인이 필요해요.</p></div></div>
    </div></div>
    <div class="detail-bottom"><section class="detail-section"><h2>추천 메뉴·상품 <small>시연 가격</small></h2>
      <div class="product-list">${s.products.map((x,i)=>`<div class="product"><span>${i+1}</span><div><b>${safe(x.name)}</b><small>시연 상품 · 재고·가격 확인 전</small></div>
        <strong>${currency(x.price)}</strong>
        <a class="btn btn-sm btn-light" href="product/${encodeURIComponent(x.slug)}.html">보기</a>
        <button class="btn btn-sm btn-green" data-add-cart="${safe(x.slug)}" type="button">담기 +</button></div>`).join('')}
      </div></section>
      ${c?`<section class="detail-section coupon-highlight"><span class="eyebrow">MARKET COUPON</span><h2>${safe(c.benefit)}</h2>
        <p>${safe(c.title)} · ${safe(c.description)}</p>
        <button class="btn btn-primary" data-claim="${c.id}" type="button">시연 쿠폰 받기 ↗</button>${mascot('detail-coupon-mascot')}</section>`:''}
    </div>
    <div class="detail-map"><div><h2>찾아가는 길</h2><p>정확한 개별 점포 좌표가 없어 시장 대표 위치로 안내합니다.</p>
      <a class="btn btn-primary" href="map.html">Google 지도 페이지 열기 ↗</a></div>
      <div class="map-placeholder"><span>📍</span><b>가락시장</b><small>실측 지도가 아닌 장소 안내</small></div></div>
  </section>`;
}

function couponsPage() {
  return `<section class="page-hero page-hero-coupons"><div class="container"><span class="eyebrow">MY GARAK REWARDS</span>
    <h1>쿠폰도, 장보기의 설렘도 한 곳에.</h1><p>발견한 매장의 혜택을 모아보고 바로 길찾기까지 이어가세요.</p>${mascot('page-mascot')}</div></section>
    <div class="container section"><div class="wallet-columns"><section>
      <div class="mini-title"><h2>받을 수 있는 쿠폰</h2><span>시연 전용 · 실제 사용 불가</span></div>
      <div class="coupon-grid">${D.coupons.map(c=>{const s=store(c.shopId);return `<article class="coupon-card"><div class="coupon-top"><img src="${s?s.photo:'assets/editorial/market.webp'}" alt="">
        <div><small>${safe(s?s.category:'')} · ${safe(s?s.name:'')}</small><h3>${safe(c.benefit)}</h3><p>${safe(c.title)}</p></div></div>
        <div class="coupon-bottom"><span>${safe(c.description)}</span><button class="btn btn-sm btn-primary" data-claim="${c.id}" type="button">쿠폰 담기</button></div></article>`;}).join('')}
      </div></section>
      <aside><div class="wallet-sticky"><span class="eyebrow">MY TICKET POCKET</span>
        <h2>내 쿠폰 지갑 <span id="wallet-count"></span></h2><div id="wallet-list"></div>
        <div class="giftbox"><img src="assets/brand/og-image.jpg" alt="가락한상">
        <h3>연합 상품권</h3><p>선불 상품권 구매·충전은 상용 승인 전 비활성화되어 있습니다.</p>
        <button class="btn btn-sm btn-light" id="gift-info" type="button">상품권 서비스 준비 안내</button></div>
      </div></aside></div></div>`;
}

function mapPage() {
  return `<section class="page-hero page-hero-map"><div class="container"><span class="eyebrow">DISCOVER GARAK MARKET</span>
    <h1>시장 구역을 누르면, 이야기가 펼쳐져요.</h1>
    <p>아래 지도는 <b>실제 지형이 아닌 테마형 도식</b>입니다. 실외 이동은 Google 지도로 확인하세요.</p>${mascot('page-mascot')}</div></section>
    <section class="container section map-layout"><div class="schematic">
      <div class="schematic-top"><b>가락한상 시장 탐험 지도</b><span>ILLUSTRATIVE MAP · NOT TO SCALE</span></div>
      <div class="schematic-scene" role="group" aria-label="테마형 구역 선택 지도">
        <div class="road road-1"></div><div class="road road-2"></div>
        <button class="zone z-fruit" data-zone="청과" type="button"><span>🍎</span><b>청과 구역</b><small>과일·채소</small></button>
        <button class="zone z-sea" data-zone="수산" type="button"><span>🐟</span><b>수산 구역</b><small>신선 수산물</small></button>
        <button class="zone z-meat" data-zone="축산" type="button"><span>🥩</span><b>축산 구역</b><small>고기·정육</small></button>
        <button class="zone z-food" data-zone="먹거리" type="button"><span>🍜</span><b>가락몰</b><small>한상·곁들임</small></button>
        <span class="path-label">테마 지도 · 정확한 구역 배치는 현장자료 확인 필요</span>
      </div>
      <div class="map-actions">
        <a class="btn btn-primary" href="map.html">Google 실제 지도 열기 ↗</a>
        <a class="btn btn-secondary" href="https://www.google.com/maps/dir/?api=1&destination=${encodeURIComponent('가락시장 서울 송파구 양재대로 932')}&travelmode=walking&dir_action=navigate" target="_blank" rel="noopener noreferrer">도보 길찾기 ↗</a>
        <a class="btn btn-light" href="https://www.garak.co.kr/homepage/M0000212/market/findStore.do" target="_blank" rel="noopener noreferrer">가락몰 공식 매장찾기 ↗</a>
      </div>
      <div class="building-guide">${BUILDINGS.map(b=>`<article><b>${safe(b.name)}</b><small>${safe(b.floors)}</small><p>${safe(b.note)}</p></article>`).join('')}<p class="data-caution">층별 안내는 공식 가락몰 소개를 요약한 탐방 메모이며, 실내 도면·호실 좌표가 아닙니다.</p></div>
      </div>
      <aside class="map-detail">
        <div class="mascot-tip map-bubble">${mascot('tip-mascot')}<div><b>어느 구역을 둘러보실래요?</b><p>지도에서 구역을 선택하면 관련 시연 매장이 나타나요.</p></div></div>
        <div id="zone-results">${D.shops.map(zoneShop).join('')}</div>
        <div class="map-note">📍 <b>GPS 안내 범위</b><p>시연 매장에는 검증된 위치 좌표가 없습니다. 길찾기는 가락시장 공통 주소로 연결됩니다.</p></div>
      </aside></section>`;
}
function zoneShop(s) {
  return `<a class="zone-shop" href="store.html?id=${encodeURIComponent(s.id)}"><img src="${s.photo}" alt=""><div><b>${safe(s.name)}</b><small>${safe(s.category)} · ${s.products.length}개</small></div><span>↗</span></a>`;
}

function eventsPage() {
  return `<section class="page-hero page-hero-events"><div class="container"><span class="eyebrow">SEASONAL MARKET STORIES</span>
    <h1>신선함이 모이는 이달의 발견</h1><p>제철 상품, 시장 미식, 특별한 상인 이야기를 둘러보세요.</p>${mascot('page-mascot')}</div></section>
    <section class="container section"><div class="filter-panel"><div class="chipbar" id="event-filters">
      ${['전체','청과','수산','축산','먹거리'].map(c=>`<button class="chip ${c==='전체'?'active':''}" data-event-filter="${c}" type="button">${c}</button>`).join('')}
    </div></div>
    <div class="event-grid" id="event-results">${D.events.map(eventCard).join('')}</div>
    <div class="mascot-tip wide-tip">${mascot('tip-mascot')}<div><b>상인 여러분, 기획전을 여실 수 있어요.</b><p>입점 안내와 판매자 센터에서 다음 단계를 확인하세요.</p></div>
    <a href="merchant-center.html" class="btn btn-sm btn-primary">상인센터 가기 →</a></div></section>`;
}
function eventCard(e) {
  return `<article class="event-card"><img src="${e.image}" alt="${safe(e.type)}"><div class="event-copy">
    <span class="eyebrow">${safe(e.tag)} · 시연 행사</span><h2>${safe(e.title)}</h2><p>${safe(e.subtitle)}</p>
    <a class="btn btn-sm btn-primary" href="${e.href}">관련 상품 보기 ↗</a></div></article>`;
}

function guide() {
  return `<section class="page-hero page-hero-guide"><div class="container"><span class="eyebrow">A STORY OF GARAK HANSANG</span>
    <h1>시장은 물건보다, 사람의 마음이 먼저입니다.</h1><p>상인 마스코트가 들려주는 따뜻한 장보기 이야기.</p>${mascot('page-mascot')}</div></section>
    <section class="container section"><div class="guide-hero"><img src="assets/brand/seal.webp" alt="가락한상 인장">
      <div><span class="eyebrow">OUR BRAND IDENTITY</span>
      <h2>좋은 먹거리가 만나는 곳,<br>새로운 발견의 시작</h2>
      <p>가락한상 마스코트는 쟁반을 머리에 이고 인사하는 상인의 모습입니다. 친근함과 신선함을 담아 홈·지도·쿠폰·상인센터에서 길을 안내합니다.</p>
      <p class="data-caution">‘가락시장 30년 전통의 맛’은 브랜드 슬로건이며, 특정 사업체의 실제 영업 기간을 증명하지 않습니다.</p></div></div>
      ${title('BRAND RULES','가락한상 디자인의 다섯 가지 약속')}
      <div class="values-grid">${[['🌿','산뜻한 초록','신선함을 떠올리게 하는 가락 그린'],['🧺','따뜻한 크림','시장 기억을 떠올리는 편안함'],['❤️','정직한 강조','중요 버튼과 혜택만 선명한 붉은색'],['🐟','마스코트의 역할','안내·격려·행사에만 등장'],['📍','실제와 시연의 구분','검증되지 않은 GPS·가격은 실거래처럼 보이지 않기']].map(v=>`<article class="value-card"><span>${v[0]}</span><h3>${v[1]}</h3><p>${v[2]}</p></article>`).join('')}</div>
      <div class="guide-palette"><div class="eyebrow">COLOR PALETTE</div>
        ${[['가락 그린','#018F3B'],['크림','#F8F3E9'],['황토 브라운','#8B5E3C'],['특가 레드','#C43D2F'],['골드','#D4AF48'],['딥 그린','#123D2A']].map(c=>`<div class="swatch"><i style="background:${c[1]}"></i><b>${c[0]}</b><small>${c[1]}</small></div>`).join('')}
      </div>
      <section class="guide-image"><img src="assets/brand/logo-lockup.webp" alt="가락한상 로고">
        <div><h2>캐릭터는 과하지 않게, 곳곳에서.</h2><p>헤더에서는 로고로, 메인에서는 안내자로, 쿠폰에서는 응원하는 친구로 등장합니다.</p>
        <a class="btn btn-primary" href="stories/index.html">상인 이야기 더 보기 →</a>
        <a class="btn btn-light" href="ir/index.html">브랜드북·IR 자료실 →</a></div></section>
    </section>`;
}

function merchant() {
  return `<section class="page-hero page-hero-merchant"><div class="container"><span class="eyebrow">FOR GARAK MERCHANTS</span>
    <h1>사장님의 오늘이, 더 빛나도록.</h1><p>점포 소개부터 상품, 쿠폰·이벤트, 운영 점검까지.</p>${mascot('page-mascot')}</div></section>
    <section class="container section"><div class="merchant-stats">
      <div><span>시연 상인</span><strong>${D.shops.length}</strong><small>가상 매장</small></div>
      <div><span>시연 상품</span><strong>${(window.GARAK_PRODUCTS||[]).length}</strong><small>장보기 카탈로그</small></div>
      <div><span>운영 모드</span><strong>DEMO</strong><small>실정산 비활성</small></div>
      <div><span>점포 GPS</span><strong>0</strong><small>검증 좌표 없음</small></div>
    </div>
    ${title('MERCHANT TOOLS','상인 운영 도구')}
    <div class="tool-grid">${[
      ['🏷️','상품·가격 관리','시연 카탈로그와 판매자 센터에서 상품 구조를 확인합니다.','merchant/index.html'],
      ['🎟️','쿠폰 지갑','고객 시연 쿠폰 동선을 미리 살펴봅니다.','coupons.html'],
      ['📍','점포 지도 등록','Google 지도에서 가락시장 위치를 확인합니다.','map.html'],
      ['🍳','레시피 연결','132가지 레시피와 식재료를 잇습니다.','recipes/index.html'],
      ['📣','홍보관','상인·협회 게시판과 스토리를 엽니다.','community/index.html'],
      ['✍️','입점 신청','판매자 입점 안내 시연 화면으로 이동합니다.','merchant/apply.html']
    ].map(t=>`<a class="tool" href="${t[3]}"><span>${t[0]}</span><h3>${t[1]}</h3><p>${t[2]}</p><strong>열기 ↗</strong></a>`).join('')}
    </div>
    <div class="merchant-join"><div><span class="eyebrow">MERCHANT ONBOARDING</span>
      <h2>가락한상 입점 준비 체크리스트</h2>
      <p>신청 자료를 이 브라우저에만 임시 저장하는 체험 화면입니다. 정식 등록은 별도 승인 후 진행합니다.</p>
      <form id="merchant-demo-form"><label>점포명<input name="storeName" required maxlength="60" placeholder="예: ○○상회"/></label>
        <label>업종<select name="category" required><option>수산</option><option>축산</option><option>청과</option><option>한상</option><option>기타</option></select></label>
        <label>연락 담당자<input name="contact" required maxlength="40" placeholder="담당자 성명 (시연용)"/></label>
        <button class="btn btn-primary" type="submit">시연 신청서 저장</button></form>
      <p class="saved-note" id="merchant-save-result" role="status"></p></div>${mascot('join-mascot')}</div>
    </section>`;
}

const renderers = {home, stores, store:storeDetail, map:mapPage, coupons:couponsPage, events:eventsPage, merchant, guide};

function toast(msg) {
  let t = $('#toast');
  if (!t) { t = document.createElement('div'); t.id = 'toast'; t.className = 'toast'; t.setAttribute('role','status'); document.body.append(t); }
  t.textContent = msg; t.classList.add('show'); setTimeout(() => t.classList.remove('show'), 3200);
}
function mapsUrl() {
  return 'https://www.google.com/maps/dir/?api=1&destination=' + encodeURIComponent('가락시장 서울 송파구 양재대로 932') + '&travelmode=walking&dir_action=navigate';
}
function couponSerial(id) {
  return 'GH-DEMO-' + String(id || 'X').replace(/[^a-z0-9-]/gi, '').toUpperCase();
}
function openNavSheet(c) {
  const s = c && store(c.shopId);
  let sheet = $('#nav-sheet');
  if (!sheet) {
    sheet = document.createElement('div');
    sheet.id = 'nav-sheet';
    sheet.setAttribute('role', 'dialog');
    sheet.setAttribute('aria-modal', 'true');
    document.body.append(sheet);
  }
  sheet.className = 'nav-sheet show';
  sheet.innerHTML = `<div class="nav-sheet-card">
    <button class="nav-sheet-x" type="button" data-close-sheet="1" aria-label="닫기">×</button>
    <span class="eyebrow">MARKET DIRECTIONS</span>
    <h3>시연 쿠폰을 담았습니다</h3>
    <p><b>${safe(c ? c.benefit : '')}</b> · ${safe(s ? s.name : '가락시장')}<br>시연 번호 ${couponSerial(c && c.id)} · 실제 사용 불가</p>
    <p class="data-caution">개별 점포 GPS가 없어 가락시장 공통 주소로 안내합니다. 길찾기만으로 쿠폰이 소모되지 않습니다.</p>
    <div class="nav-sheet-actions">
      <button class="btn btn-primary" type="button" data-route="${safe(s ? s.id : '')}">🧭 이 매장으로 길찾기</button>
      <a class="btn btn-light" href="coupons.html">내 쿠폰 지갑 보기</a>
    </div>
  </div>`;
}
function addDemoCart(slug) {
  const key = 'garak-hansang-demo-cart';
  let list = {};
  try { list = JSON.parse(localStorage.getItem(key) || '{}'); } catch { list = {}; }
  const qty = (Number(list[slug]?.qty) || 0) + 1;
  list[slug] = {slug, qty};
  try { localStorage.setItem(key, JSON.stringify(list)); } catch {}
  document.querySelectorAll('[data-cart-count]').forEach(el => {
    el.textContent = Object.values(list).reduce((a,x)=>a+Math.max(0, Number(x.qty)||0), 0);
  });
  toast('장바구니에 담았습니다. (시연용)');
}
function renderWallet() {
  if (!$('#wallet-list')) return;
  const ids = wallet();
  $('#wallet-count').textContent = ids.length + '장';
  $('#wallet-list').innerHTML = ids.length ? ids.map(id => {
    const c = coupon(id); const s = c && store(c.shopId);
    return c ? `<div class="wallet-item"><small>${safe(s?s.name:'')} · 시연 ${couponSerial(c.id)}</small><b>${safe(c.benefit)}</b>
      <div><button class="btn btn-sm btn-primary" data-route="${safe(s?s.id:'')}" type="button">🧭 길찾기</button>
      <button class="btn btn-sm btn-light" data-remove-coupon="${c.id}" type="button">지갑에서 제외</button></div></div>` : '';
  }).join('') : `<div class="wallet-empty">아직 담은 쿠폰이 없어요.<br>왼쪽에서 시연 쿠폰을 담아보세요.</div>`;
}
function filterShops() {
  if (page !== 'stores') return;
  const q = ($('#store-search').value || '').toLowerCase();
  const cat = $('[data-category].active')?.dataset.category || '전체';
  const fav = $('#favorites-only')?.checked;
  const arr = D.shops.filter(s =>
    (cat === '전체' || s.category === cat) &&
    (!fav || liked().includes(s.id)) &&
    [s.name, s.category, s.intro, s.products.map(p=>p.name).join(' ')].join(' ').toLowerCase().includes(q)
  );
  $('#shop-results').innerHTML = arr.map(s => card(s)).join('');
  $('#shop-empty').classList.toggle('hidden', arr.length > 0);
}

function init() {
  const app = $('#explore-app');
  if (!app) return;
  app.innerHTML = header() + `<main>${(renderers[page] || home)()}</main>` + footer() + lowerNav();
  const w = $('#wallet-qty'); if (w) w.textContent = wallet().length;
  $('#global-search')?.addEventListener('submit', e => {
    e.preventDefault();
    location.href = 'stores.html?q=' + encodeURIComponent($('#search-top').value.trim());
  });
  $('#menu-toggle')?.addEventListener('click', () => {
    const n = $('#primary-nav'); n.classList.toggle('open');
    $('#menu-toggle').setAttribute('aria-expanded', String(n.classList.contains('open')));
  });
  document.body.dataset.brandInit = '1';
  $('#store-search')?.addEventListener('input', filterShops);
  $('#favorites-only')?.addEventListener('change', filterShops);
  $('#reset-search')?.addEventListener('click', () => {
    if ($('#store-search')) $('#store-search').value = '';
    if ($('#favorites-only')) $('#favorites-only').checked = false;
    $$('[data-category]')[0]?.click();
  });
  $('#gift-info')?.addEventListener('click', () => toast('선불 상품권은 금융·가맹 계약과 실결제 연동 전까지 시연으로만 안내합니다.'));
  $('#merchant-demo-form')?.addEventListener('submit', e => {
    e.preventDefault();
    const fd = new FormData(e.target);
    const row = {storeName:String(fd.get('storeName')||'').trim(), category:String(fd.get('category')), contact:String(fd.get('contact')||'').trim(), createdAt:new Date().toISOString()};
    if (!row.storeName || !row.contact) return;
    save('merchantDraft', row);
    $('#merchant-save-result').textContent = '브라우저에 시연 신청서가 임시 저장됐습니다. 서버 전송·정식 입점은 이루어지지 않습니다.';
    toast('시연 신청서 저장 완료'); e.target.reset();
  });
  if (page === 'stores') {
    const q = new URLSearchParams(location.search);
    if ($('#store-search')) $('#store-search').value = q.get('q') || '';
    if ($('#favorites-only')) $('#favorites-only').checked = q.get('favorites') === '1';
    const cat = q.get('category') || '전체';
    const btn = $$('[data-category]').find(x => x.dataset.category === cat) || $$('[data-category]')[0];
    if (btn) btn.classList.add('active');
    filterShops();
  }
  try {
    const cart = JSON.parse(localStorage.getItem('garak-hansang-demo-cart') || '{}');
    const n = Object.values(cart).reduce((a, x) => a + Math.max(0, Number(x.qty) || 0), 0);
    document.querySelectorAll('[data-cart-count]').forEach(el => { el.textContent = n; });
  } catch {}
  renderWallet();
}
function onExploreClick(ev) {
  const raw = ev.target;
  const el = raw && raw.nodeType === 1 ? raw : raw && raw.parentElement;
  if (!el || typeof el.closest !== 'function') return;
  if (raw && raw.id === 'nav-sheet') { $('#nav-sheet')?.classList.remove('show'); return; }
  if (el.closest('[data-close-sheet]')) { $('#nav-sheet')?.classList.remove('show'); return; }
  const claimEl = el.closest('[data-claim]');
  if (claimEl) {
    const c = coupon(claimEl.getAttribute('data-claim')); if (!c) return;
    let wlt = wallet();
    if (wlt.includes(c.id)) toast('이미 내 쿠폰 지갑에 담겨 있습니다.');
    else { wlt.push(c.id); save('wallet', wlt); toast('시연 쿠폰을 지갑에 담았어요!'); }
    if ($('#wallet-qty')) $('#wallet-qty').textContent = wallet().length;
    renderWallet();
    openNavSheet(c);
    return;
  }
  const b = el.closest('button'); if (!b) return;
  if (b.dataset.removeCoupon) {
    save('wallet', wallet().filter(id => id !== b.dataset.removeCoupon));
    renderWallet();
    if ($('#wallet-qty')) $('#wallet-qty').textContent = wallet().length;
    toast('쿠폰을 지갑에서 제외했습니다.');
  }
  if (b.dataset.route) { toast('개별 좌표 미검증: 가락시장 대표 주소로 안내합니다.'); window.open(mapsUrl(), '_blank', 'noopener,noreferrer'); }
  if (b.dataset.like) {
    let l = liked();
    l = l.includes(b.dataset.like) ? l.filter(id => id !== b.dataset.like) : l.concat(b.dataset.like);
    save('likes', l);
    $$(`[data-like="${b.dataset.like}"]`).forEach(x => { x.textContent = l.includes(b.dataset.like) ? '♥' : '♡'; x.classList.toggle('is-liked', l.includes(b.dataset.like)); });
    toast(l.includes(b.dataset.like) ? '찜한 매장에 저장했습니다.' : '관심 매장에서 해제했습니다.');
    if (page === 'stores') filterShops();
  }
  if (b.dataset.addCart) addDemoCart(b.dataset.addCart);
  if (b.dataset.zone) {
    $$('[data-zone]').forEach(x => x.classList.toggle('selected', x === b));
    const cats = ZONE_CATS[b.dataset.zone] || [];
    $('#zone-results').innerHTML = D.shops.filter(s => cats.includes(s.catKey) || s.zone === b.dataset.zone).map(zoneShop).join('')
      || '<p class="data-caution">이 구역의 시연 매장이 없습니다.</p>';
  }
  if (b.dataset.category) { $$('[data-category]').forEach(x => x.classList.toggle('active', x === b)); filterShops(); }
  if (b.dataset.eventFilter) {
    $$('[data-event-filter]').forEach(x => x.classList.toggle('active', x === b));
    $('#event-results').innerHTML = D.events.filter(e => b.dataset.eventFilter === '전체' || e.type === b.dataset.eventFilter).map(eventCard).join('');
  }
}
document.addEventListener('click', onExploreClick, true);
if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', init);
else init();
})();
