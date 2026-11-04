/* Source UX adapted from skvive/linkrlive content feed, safe text rendering, tab/pager and detail navigation. No auth/API/transactions. */
(() => {
"use strict";
const items = Array.isArray(window.GARAK_MARKET_LIVE_DATA) ? window.GARAK_MARKET_LIVE_DATA : [];
const esc = value => String(value ?? "").replace(/[&<>"']/g, ch => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[ch]));
const CATEGORIES = [{id:"all",label:"전체"},{id:"market",label:"시장 탐방"},{id:"dining",label:"맛집 탐색"},{id:"shop",label:"수산 점포"},{id:"tips",label:"먹거리 노하우"}];
const state = {category:"all",query:"",page:1};
const PAGE_SIZE = 6;
const detailUrl = article => "market-live-" + article.id + ".html";
const getArticle = id => items.find(article => article.id === id);
const mapsUrl = query => "https://www.google.com/maps/search/?api=1&query="+encodeURIComponent(query);
const imageDisclaimer = "콘텐츠 대표 연출 이미지 · 특정 업체의 실제 촬영 사진이 아닙니다";
function card(article,index) {
  return `<article class="ml-card"><a class="ml-card-image" href="${detailUrl(article)}" aria-label="${esc(article.title)} 상세 보기">
     <img src="${esc(article.image)}" alt="${esc(article.imageAlt)}" loading="${index<3?"eager":"lazy"}" width="700" height="460"><span class="ml-card-tag">${esc(article.catName)}</span></a>
    <div class="ml-card-content"><p class="ml-card-area">📍 ${esc(article.area)}</p><h3><a href="${detailUrl(article)}">${esc(article.title)}</a></h3><p>${esc(article.summary)}</p>
    <div class="ml-card-bottom"><span>가락한상 에디터 선별</span><a href="${detailUrl(article)}" aria-label="${esc(article.title)} 읽기">자세히 보기 <span aria-hidden="true">↗</span></a></div></div></article>`;
}
function listPage() {
  return `<section class="ml-hero"><div class="container ml-hero-inner"><div class="ml-hero-copy">
    <span class="ml-eyebrow">GARAK HANSANG · LOCAL DISCOVERY</span><span class="ml-hero-chip">MARKET JOURNAL / 맛집·시장정보</span>
    <h1>오늘의 가락시장,<br><em>잘 먹고 잘 둘러보는 방법.</em></h1><p>시장 골목과 맛집 정보를 발견하고 상세 가이드까지 읽는 가락한상 로컬 피드입니다. 사람의 시선으로 모은 공개 안내이며 실시간 방송·가격이 아닙니다.</p>
    <div class="ml-hero-actions"><a class="ml-btn ml-btn-primary" href="#ml-discover">콘텐츠 둘러보기 <span aria-hidden="true">↗</span></a><a class="ml-btn ml-btn-outline" href="market-map.html">시장 지도 보기</a></div>
    <div class="ml-hero-info"><span><b>${items.length}</b>개 읽을 거리</span><span>맛집 · 수산 · 청과 · 시장 산책</span><span>2026.11.05 콘텐츠 검토</span></div></div>
    <div class="ml-hero-photo"><img src="assets/editorial/garak-market-dawn-hero.avif" alt="가락시장의 새벽을 표현한 가락한상 대표 이미지" width="740" height="680"><span>가락시장 이야기 · 브랜드 대표 이미지</span></div></div></section>
    <section class="container ml-section ml-page" id="ml-discover"><div class="ml-intro"><div><span class="ml-eyebrow">EDITOR'S PICKS & MARKET GUIDE</span><h2>시장에 가기 전, 읽어두면 좋은 이야기</h2><p>최신 공식 안내와 공개된 식당 정보를 바탕으로 정리했습니다. 가락한상 공식 제휴·예약·라이브 스트리밍을 뜻하지 않습니다.</p></div><a href="market-guide.html" class="ml-subtle-link">가락한상 브랜드 이야기 ↗</a></div>
    <div class="ml-controls"><div class="ml-tabs" role="group" aria-label="콘텐츠 분류">${CATEGORIES.map(c=>`<button type="button" data-ml-category="${c.id}" aria-pressed="${c.id==="all"}" class="${c.id==="all"?"active":""}">${esc(c.label)}</button>`).join("")}</div>
    <label class="ml-search"><span class="sr-only">맛집·시장 콘텐츠 검색</span><span aria-hidden="true">⌕</span><input type="search" data-ml-search placeholder="매장·메뉴·시장 이야기 검색" maxlength="60" autocomplete="off"></label></div>
    <div class="ml-feed-title"><h2>가락의 발견</h2><p id="ml-result-count" role="status" aria-live="polite">콘텐츠 검색 결과</p></div>
    <div id="ml-feed-grid" class="ml-grid" aria-live="polite"></div><nav id="ml-pagination" class="ml-pagination" aria-label="콘텐츠 페이지 이동"></nav>
    <div class="ml-notice"><b>안내</b> 매장명은 공개 정보 탐색용입니다. 방문 전 영업 여부·정확한 위치·메뉴·가격·상차림 조건을 직접 확인하세요. 모든 이미지는 별도 표기가 없으면 브랜드 공용 연출 이미지입니다.</div></section>
    <section class="ml-bottom-banner"><div class="container"><div><span class="ml-eyebrow">FROM CONTENT TO THE MARKET</span><h2>읽은 다음에는, 가락의 골목으로.</h2><p>상점 찾기·시장 지도·제철 식재료 정보로 자연스럽게 이어집니다.</p></div><div class="ml-banner-links"><a class="ml-btn ml-btn-primary" href="stores.html">매장 찾기 ↗</a><a class="ml-btn ml-btn-outline" href="prices.html">시세 안내 보기</a></div></div></section>`;
}
function detailPage() {
  const id = document.body.dataset.liveId || new URLSearchParams(location.search).get("id");
  const article = getArticle(id);
  if(!article) return '<section class="container ml-section"><h1>콘텐츠를 찾을 수 없습니다.</h1><p>주소를 확인하거나 목록에서 다른 이야기를 골라 주세요.</p><a class="ml-btn ml-btn-primary" href="market-live.html">콘텐츠 목록으로</a></section>';
  const related = items.filter(x=>x.id!==id).sort((a,b)=>Number(b.cat===article.cat)-Number(a.cat===article.cat)).slice(0,3);
  return `<section class="ml-detail-top"><div class="container"><a class="ml-back" href="market-live.html">← 맛집·시장정보 목록</a><p class="ml-eyebrow">GARAK LOCAL JOURNAL · ${esc(article.catName)}</p>
    <h1>${esc(article.title)}</h1><p class="ml-detail-deck">${esc(article.summary)}</p><div class="ml-detail-meta"><span>📍 ${esc(article.area)}</span><span>2026.11.05 편집</span><span>가락한상 콘텐츠</span></div></div></section>
    <div class="container ml-detail-layout"><main class="ml-detail-main" id="ml-article" tabindex="-1"><figure class="ml-detail-image"><img src="${esc(article.image)}" alt="${esc(article.imageAlt)}" width="1120" height="620">
      <figcaption>${imageDisclaimer}</figcaption></figure>
      <p class="ml-detail-lead">${esc(article.lead)}</p>
      <div class="ml-facts"><h2>방문 전에 먼저 체크</h2><ul>${article.facts.map(t=>`<li>${esc(t)}</li>`).join("")}</ul></div>
      ${article.sections.map(([heading,text])=>`<section class="ml-article-section"><h2>${esc(heading)}</h2><p>${esc(text)}</p></section>`).join("")}
      <div class="ml-checklist"><h2>체크리스트</h2><ul>${article.tips.map(x=>`<li><span aria-hidden="true">✓</span>${esc(x)}</li>`).join("")}</ul></div>
      <div class="ml-sources"><h2>참고·확인 경로</h2><p>공개 안내 및 지도 정보를 정리한 편집 콘텐츠이며, 당일 운영 상태와 계약·제휴 여부를 보장하지 않습니다.</p>
        <a href="${esc(article.sourceUrl)}" target="_blank" rel="noopener noreferrer">${esc(article.sourceName)} <span aria-hidden="true">↗</span></a></div>
      <div class="ml-post-actions"><button type="button" class="ml-btn ml-btn-primary" data-ml-share>이 글 공유하기 ↗</button><a class="ml-btn ml-btn-outline" href="market-live.html">다른 이야기 보기</a><p id="ml-share-status" role="status" aria-live="polite"></p></div></main>
      <aside class="ml-detail-side" aria-label="관련 방문 안내"><div class="ml-side-box"><span class="ml-eyebrow">PLAN YOUR VISIT</span><h2>시장에 가기 전</h2><p>가락시장 방문은 실제 영업·가격·반입·좌석 조건을 확인하는 것이 우선입니다.</p>
        <a href="${mapsUrl(article.mapQuery)}" target="_blank" rel="noopener noreferrer">지도에서 위치 검색 ↗</a><a href="market-map.html">가락한상 시장 지도 ↗</a><a href="stores.html">가락한상 매장 안내 ↗</a></div>
        <div class="ml-side-brand"><img src="assets/brand/mascot.webp?v=17" alt="가락한상 상인 마스코트" width="140" height="140"><p>좋은 먹거리가<br><strong>만나는 곳, 가락한상</strong></p></div></aside></div>
    <section class="container ml-related ml-section"><div class="ml-intro"><div><span class="ml-eyebrow">KEEP EXPLORING</span><h2>함께 읽으면 좋은 시장 이야기</h2></div></div><div class="ml-grid">${related.map((x,i)=>card(x,i)).join("")}</div></section>`;
}
function pageSlice(list,page,size) {
  const pages=Math.max(1,Math.ceil(list.length/size));
  const current=Math.min(Math.max(1,page),pages);
  return {slice:list.slice((current-1)*size,current*size),page:current,pages};
}
function updateFeed() {
  const grid=document.getElementById("ml-feed-grid");
  if(!grid)return;
  const q=state.query.toLocaleLowerCase("ko-KR");
  const filtered=items.filter(a=>(state.category==="all"||state.category===a.cat)&&(!q||[a.title,a.summary,a.area,a.lead,a.catName].join(" ").toLocaleLowerCase("ko-KR").includes(q)));
  const page=pageSlice(filtered,state.page,PAGE_SIZE);
  state.page=page.page;
  grid.innerHTML=page.slice.length?page.slice.map(card).join(""):'<div class="ml-empty"><h3>검색 결과가 없습니다.</h3><p>다른 분류나 검색어로 다시 찾아보세요.</p><button type="button" data-ml-reset>전체 콘텐츠 보기</button></div>';
  const count=document.getElementById("ml-result-count");if(count)count.textContent="전체 "+filtered.length+"건 · "+page.page+"/"+page.pages+"페이지";
  const pager=document.getElementById("ml-pagination");
  if(pager)pager.innerHTML='<button type="button" data-ml-page="prev" '+(page.page===1?'disabled':'')+'>← 이전</button><span>'+page.page+' / '+page.pages+'</span><button type="button" data-ml-page="next" '+(page.page===page.pages?'disabled':'')+'>다음 →</button>';
}
async function shareArticle() {
  const msg=document.getElementById("ml-share-status"),url=location.href;
  try{
    if(navigator.share){await navigator.share({title:document.title,url});if(msg)msg.textContent="공유 메뉴를 열었습니다.";return;}
    if(navigator.clipboard && navigator.clipboard.writeText){await navigator.clipboard.writeText(url);if(msg)msg.textContent="글 주소를 복사했습니다.";return;}
    if(msg)msg.textContent="브라우저 주소창에서 이 페이지 주소를 복사해 주세요.";
  }catch(error){if(msg)msg.textContent="공유를 취소했거나 주소를 복사할 수 없습니다.";}
}
function init() {
  const page=document.body.dataset.page;
  if(page==="live"){
    const root=document.querySelector(".ml-page");if(!root)return;
    root.addEventListener("click",event=>{
      const button=event.target.closest("button");
      if(!button)return;
      if(button.dataset.mlCategory){state.category=button.dataset.mlCategory;state.page=1;root.querySelectorAll("[data-ml-category]").forEach(b=>{const active=b===button;b.classList.toggle("active",active);b.setAttribute("aria-pressed",String(active));});updateFeed();}
      else if(button.dataset.mlPage){state.page+=button.dataset.mlPage==="next"?1:-1;updateFeed();document.getElementById("ml-discover")?.scrollIntoView({behavior:"smooth",block:"start"});}
      else if(button.hasAttribute("data-ml-reset")){state.category="all";state.query="";state.page=1;root.querySelector("[data-ml-search]").value="";root.querySelectorAll("[data-ml-category]").forEach(b=>{const active=b.dataset.mlCategory==="all";b.classList.toggle("active",active);b.setAttribute("aria-pressed",String(active));});updateFeed();}
    });
    root.querySelector("[data-ml-search]")?.addEventListener("input",event=>{state.query=event.target.value.trim();state.page=1;updateFeed();});
    updateFeed();
  }
  if(page==="liveDetail")document.querySelector("[data-ml-share]")?.addEventListener("click",shareArticle);
}
window.GARAK_MARKET_LIVE=Object.freeze({listPage,detailPage,init});
})();
