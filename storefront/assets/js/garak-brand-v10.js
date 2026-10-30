/* Garak Hansang cross-page brand enhancement. No commerce state changes. */
(function(){'use strict';
 function init(){
  if(document.documentElement.dataset.garakV10Done)return;
  document.documentElement.dataset.garakV10Done='true';
  const root=typeof window.GARAK_ROOT==='string'?window.GARAK_ROOT:'';
  const asset=(file)=>root+'assets/brand/'+file;
  document.body.classList.add('garak-brand-v10');
  const isHome=location.pathname==='/'||/\/(?:index\.html)?$/.test(location.pathname)&&!location.pathname.includes('/admin/')||document.querySelector('.story-hero')!==null;
  if(isHome)document.body.classList.add('brand-home');
  document.querySelectorAll('.header a.logo, .header a.brand-lockup').forEach((a)=>{
    a.setAttribute('aria-label','가락한상 홈');
    a.classList.add('garak-v10-logo');
    const img=document.createElement('img');img.src=asset('wordmark.png');img.alt='가락한상';img.width=215;img.height=58;
    a.replaceChildren(img);
  });
  const hero=document.querySelector('.story-hero');
  if(hero){
    const inner=hero.querySelector('.story-hero-inner')||hero;
    if(!inner.querySelector('.brand-v10-hero-mascot')){
      let img=document.createElement('img');img.src=asset('mascot.webp');img.alt='';img.setAttribute('aria-hidden','true');img.className='brand-v10-hero-mascot';img.loading='eager';inner.append(img);
      let bubble=document.createElement('p');bubble.className='brand-v10-speech';bubble.textContent='오늘도 좋은 먹거리, 가락한상에서 만나보세요!';inner.append(bubble);
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
      if(!container.querySelector('.brand-v10-page-mascot')){
       const img=document.createElement('img');img.src=asset('mascot.webp');img.alt='';img.setAttribute('aria-hidden','true');img.loading='lazy';img.className='brand-v10-page-mascot';container.append(img);
      }
    }
  }
  const footer=document.querySelector('.footer .container .footer-top > div');
  if(footer && !footer.querySelector('.brand-v10-footer-sign')){
    const el=document.createElement('div');el.className='brand-v10-footer-sign';
    const stamp=document.createElement('img');stamp.src=asset('seal.png');stamp.alt='가락한상 브랜드 인장';
    const span=document.createElement('span');span.textContent='시장과 식탁을 잇는 정겨운 동네 장터 · 신선한 먹거리의 이야기';el.append(stamp,span);footer.append(el);
  }
  const nav=document.querySelector('[data-menu]');const mobile=document.querySelector('.mobile-menu');
  if(nav && mobile){nav.setAttribute('aria-controls',mobile.id||'garak-mobile-menu');
    nav.addEventListener('keydown',e=>{if((e.key==='Enter'||e.key===' ') && nav.tagName!=='BUTTON'){e.preventDefault();nav.click()}});
  }
 }
 if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',init,{once:true});else init();
})();
