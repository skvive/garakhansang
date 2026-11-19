/* Garak Hansang cross-page brand enhancement. No commerce state changes. */
(function(){'use strict';
 function init(){
  if(document.documentElement.dataset.garakV10Done)return;
  document.documentElement.dataset.garakV10Done='true';
  const root=typeof window.GARAK_ROOT==='string'?window.GARAK_ROOT:'';
  const brandRoot=root||((location.pathname.startsWith('/merchant-showcase/')||location.pathname.startsWith('/ir/'))?'../':'');
  const asset=(file)=>brandRoot+'assets/brand/'+file;
  document.body.classList.add('garak-brand-v10');
  const isHome=location.pathname==='/'||location.pathname==='/index.html'||document.querySelector('.story-hero')!==null;
  if(isHome)document.body.classList.add('brand-home');
  const applyLogo=()=>{
    document.querySelectorAll('.header a.logo, .header a.brand-lockup, .site-header a.logo, a.auth-brand').forEach((a)=>{
      a.setAttribute('aria-label','가락한상 홈');
      a.classList.add('garak-v10-logo');
      if(a.querySelector('img[src*="wordmark"]'))return;
      const img=document.createElement('img');img.src=asset('wordmark.png');img.alt='가락한상';img.width=215;img.height=58;
      a.replaceChildren(img);
    });
  };
  applyLogo();
  setTimeout(applyLogo,120);
  const hero=document.querySelector('.story-hero');
  if(hero){
    const inner=hero.querySelector('.story-hero-inner')||hero;
    if(!inner.querySelector('.brand-v10-hero-mascot,.hero-mascot')){
      let img=document.createElement('img');img.src=asset('mascot.webp')+'?v=17';img.alt='';img.setAttribute('aria-hidden','true');img.className='brand-v10-hero-mascot';img.loading='eager';inner.append(img);
      let bubble=document.createElement('p');bubble.className='brand-v10-speech';bubble.textContent='오늘도 좋은 먹거리, 가락한상에서 만나요!';inner.append(bubble);
    }
    if(!document.querySelector('.brand-v10-promo')){
      let promo=document.createElement('section');promo.className='brand-v10-promo';promo.setAttribute('aria-label','시장 바로가기');
      promo.innerHTML=`<div class="container brand-v10-promo-grid">
        <a href="${root}category/seafood.html"><span class="symbol" aria-hidden="true">🐟</span><span><strong>제철 상품 둘러보기</strong><small>수산·축산·농산을 한곳에서</small></span><span class="arrow" aria-hidden="true">↗</span></a>
        <a href="${root}recipes/index.html"><span class="symbol" aria-hidden="true">🍲</span><span><strong>뚝딱 요리 레시피</strong><small>장보기부터 조리법까지</small></span><span class="arrow" aria-hidden="true">↗</span></a>
        <a href="${root}community/index.html"><span class="symbol" aria-hidden="true">🏪</span><span><strong>시장 사람들의 이야기</strong><small>상인·요리사·협회 소식</small></span><span class="arrow" aria-hidden="true">↗</span></a>
      </div>`;
      hero.insertAdjacentElement('afterend',promo);
    }
  }else{
    const pageHero=document.querySelector('.page-hero');
    if(pageHero){const container=pageHero.querySelector('.container')||pageHero;
      if(!pageHero.querySelector('.brand-v10-page-mascot,.page-mascot,.mascot')){
       const img=document.createElement('img');img.src=asset('mascot.webp')+'?v=17';img.alt='';img.setAttribute('aria-hidden','true');img.loading='lazy';img.className='brand-v10-page-mascot';container.append(img);
      }
    }
  }
  const footer=document.querySelector('.footer .container .footer-top > div');
  if(footer && !footer.querySelector('.brand-v10-footer-sign')){
    const el=document.createElement('div');el.className='brand-v10-footer-sign';
    const stamp=document.createElement('img');stamp.src=asset('seal.png');stamp.alt='가락한상 브랜드 인장';
    const span=document.createElement('span');span.textContent='시장과 식탁을 잇는 정겨운 동네 장터 · 신선한 먹거리의 이야기';el.append(stamp,span);footer.append(el);
  }

  /* Keep the legacy upper header, login and shopping controls. Share the same
     pinned category/service ribbon across all public page variants. */
  const menuLinks=[
    ['전체상품','/category/seafood.html'],
    ['오늘의 가격','/prices.html'],
    ['제철 수산','/category/seafood.html'],
    ['한상 세트','/category/sets.html'],
    ['132가지 레시피','/recipes/index.html'],
    ['요리사·쇼츠','/chefs/index.html'],
    ['업체·협회','/community/index.html'],
    ['쿠팡·배민 입점','/channels/index.html'],
    ['가락시장 지도','/map.html'],
    ['매장 찾기','/stores.html'],
    ['쿠폰','/coupons.html'],
    ['이벤트','/events.html'],
    ['탐험 지도','/market-map.html'],
    ['자료실','/ir/index.html']
  ];
  function syncGlobalNavigation(){
    const pathname=location.pathname;
    if(pathname.startsWith('/admin/')||pathname.startsWith('/auth/')||
       pathname==='/merchant-showcase/moderation.html')return;
    const header=document.querySelector('header.header,header.site-header,header.top');
    if(!header)return;
    header.classList.add('gh-sticky-header');
    let ribbon=header.querySelector('.story-nav-ribbon')||
               document.querySelector('.story-nav-ribbon');
    if(!ribbon){
      ribbon=document.createElement('div');
      ribbon.className='story-nav-ribbon';
    }
    ribbon.classList.add('gh-global-ribbon');
    let navigation=ribbon.querySelector('nav');
    if(!navigation){
      navigation=document.createElement('nav');
      ribbon.appendChild(navigation);
    }
    navigation.className='gh-global-links';
    navigation.setAttribute('aria-label','가락한상 전체 서비스 메뉴');
    navigation.replaceChildren();
    for(const [title,href] of menuLinks){
      const anchor=document.createElement('a');
      anchor.href=href;
      anchor.textContent=title;
      if(pathname===href)anchor.setAttribute('aria-current','page');
      navigation.appendChild(anchor);
    }
    // Previously this element sat OUTSIDE the sticky header, so it vanished
    // after scrolling; keep it IN the header, including on Google Maps pages.
    if(ribbon.parentElement!==header)header.appendChild(ribbon);
    document.documentElement.classList.add('gh-global-nav-ready');
  }
  syncGlobalNavigation();
  const nav=document.querySelector('[data-menu]');const mobile=document.querySelector('.mobile-menu');
  if(nav && mobile){nav.setAttribute('aria-controls',mobile.id||'garak-mobile-menu');
    nav.addEventListener('keydown',e=>{if((e.key==='Enter'||e.key===' ') && nav.tagName!=='BUTTON'){e.preventDefault();nav.click()}});
  }
 }
 if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',init,{once:true});else init();
})();
