/* GARAK HANSANG ORDER | client-side demo, NOT a commercial checkout. */
(() => {
'use strict';
const ROOT = '../assets/images/';
const BRAND = '../assets/brand/'; const RIDER = 'mascot-rider.webp';
const MARKETS = [
 {id:'garak',name:'가락시장',caption:'과일·채소·정육·식자재',icon:'🥬',theme:'가락시장 채소부터 정육까지, 한 장바구니로',delivery:'신선식품 공동배송',min:3900,add:600,cold:1000,flag:'합배송 실증 1순위',types:['채소·과일','정육','수산','반찬']},
 {id:'noryang',name:'노량진수산시장',caption:'활어·회·해산물',icon:'🐟',theme:'횟감 손질하고, 냉장으로 신선하게',delivery:'냉장 포장 · 손질 옵션',min:5200,add:800,cold:1000,flag:'수산물 특화',types:['횟감','수산','갑각류']},
 {id:'nam',name:'남대문시장',caption:'반찬·먹거리·생활잡화',icon:'🍱',theme:'시장 골목의 맛과 생활을 바로 주문',delivery:'반찬·먹거리 근거리 배송',min:3500,add:600,cold:0,flag:'먹거리 & 잡화',types:['반찬','먹거리','잡화']},
 {id:'dong',name:'동대문시장',caption:'원단·부자재·소상공인',icon:'🧵',theme:'원단 한 마부터 도매 주문까지',delivery:'원단 B2B · 퀵배송',min:5200,add:1300,cold:0,flag:'사업자 B2B · 견적',types:['원단','부자재','B2B']},
 {id:'region',name:'지역 명소시장',caption:'전국 특산물·로컬 먹거리',icon:'🏞️',theme:'전국 전통시장의 특산물을 한자리에',delivery:'택배형 주문 · 지역별 별도 배송',min:4500,add:4500,cold:0,flag:'전국 특산품',types:['특산물','먹거리']},
];
const ITEMS = [
 {id:'g1',m:'garak',store:'가락청과 (샘플)',name:'당일 딸기 500g',cat:'채소·과일',price:9900,img:'product-ttalgi.webp',tag:'당일 입고',cold:1},
 {id:'g2',m:'garak',store:'가락정육 (샘플)',name:'한우 등심 300g',cat:'정육',price:29900,img:'product-deungsim.webp',tag:'신선 정육',cold:1},
 {id:'g3',m:'garak',store:'가락수산 (샘플)',name:'손질 광어회 400g',cat:'수산',price:29900,img:'product-gwang-eo.webp',tag:'손질 가능',cold:1,process:1},
 {id:'g4',m:'garak',store:'가락청과 (샘플)',name:'샤인머스캣 1송이',cat:'채소·과일',price:14900,img:'product-shine-muscat.webp',tag:'과일',cold:0},
 {id:'g5',m:'garak',store:'가락반찬 (샘플)',name:'한상 채소 쌈 모둠',cat:'반찬',price:7900,img:'product-ssam-mo-dum.webp',tag:'오늘의 장보기',cold:1},
 {id:'n1',m:'noryang',store:'노량진 OO수산 (샘플)',name:'광어회 400g',cat:'횟감',price:29900,img:'product-gwang-eo.webp',tag:'손질 선택',cold:1,process:1},
 {id:'n2',m:'noryang',store:'노량진 바다상회 (샘플)',name:'국산 전복 5미',cat:'수산',price:23900,img:'product-jeonbok.webp',tag:'냉장 배송',cold:1},
 {id:'n3',m:'noryang',store:'노량진 바다상회 (샘플)',name:'킹크랩 1kg 기준',cat:'갑각류',price:69900,img:'product-king-crab-a.webp',tag:'실중량 정산 필요',cold:1,process:1},
 {id:'n4',m:'noryang',store:'노량진 OO수산 (샘플)',name:'참돔회 350g',cat:'횟감',price:32900,img:'product-chamdom-hoe.webp',tag:'손질 선택',cold:1,process:1},
 {id:'s1',m:'nam',store:'남대문 반찬집 (샘플)',name:'해물 매운탕 밀키트',cat:'반찬',price:12900,img:'product-hoe-maeuntang.webp',tag:'우리 시장 먹거리',cold:1},
 {id:'s2',m:'nam',store:'남대문 분식집 (샘플)',name:'모둠 간식 세트',cat:'먹거리',price:8900,img:'product-corndog-cheese.webp',tag:'시장 먹거리',cold:0},
 {id:'s3',m:'nam',store:'남대문 반찬집 (샘플)',name:'손질 바지락 500g',cat:'반찬',price:8900,img:'product-bajirak.webp',tag:'반찬 재료',cold:1},
 {id:'d1',m:'dong',store:'동대문 원단상회 (샘플)',name:'면 100% 원단 1마',cat:'원단',price:5200,img:'../editorial/merchant.webp',tag:'B2B 견적 가능',cold:0,b2b:1},
 {id:'d2',m:'dong',store:'동대문 원단상회 (샘플)',name:'프리미엄 원단 1마',cat:'원단',price:8900,img:'../editorial/market.webp',tag:'퀵배송',cold:0,b2b:1},
 {id:'d3',m:'dong',store:'동대문 부자재 (샘플)',name:'부자재 꾸러미 1세트',cat:'부자재',price:3900,img:'../editorial/merchant.webp',tag:'소량 주문',cold:0,b2b:1},
 {id:'r1',m:'region',store:'제주 시장 상인 (샘플)',name:'제주 감귤 2kg',cat:'특산물',price:15900,img:'product-gamgyul.webp',tag:'택배형 주문',cold:0},
 {id:'r2',m:'region',store:'지역 청과상 (샘플)',name:'국산 과일 선물 꾸러미',cat:'특산물',price:29900,img:'fruit.webp',tag:'산지 특산물',cold:0},
];
const COUPONS = [
 {id:'welcome',title:'첫 주문 5,000원',sub:'상품금액 30,000원 이상 · 첫 시연 주문',kind:'fixed',amount:5000,min:30000,market:'all',emoji:'🎁'},
 {id:'marketday',title:'시장 장보기 10%',sub:'상품금액 20,000원 이상 · 최대 3,500원',kind:'rate',amount:.1,max:3500,min:20000,market:'garak',emoji:'🥕'},
 {id:'fish',title:'수산 특화 3,000원',sub:'노량진 상품금액 30,000원 이상',kind:'fixed',amount:3000,min:30000,market:'noryang',emoji:'🐟'},
 {id:'bundle',title:'합배송비 지원',sub:'같은 시장 2개 점포 이상 · 30,000원 이상',kind:'ship',amount:2500,min:30000,market:'all',emoji:'🛵'},
];
const $=(sel)=>document.querySelector(sel);
const money=n=>Math.round(n).toLocaleString('ko-KR')+'원';
const safe=s=>String(s).replace(/[&<>"']/g, c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const read=(key,fallback)=>{try{return JSON.parse(localStorage.getItem('gho_'+key))??fallback}catch{return fallback}};
const state={tab:'home',market:read('market','garak'),cat:'전체',cart:read('cart',[]),claimed:read('claimed',[]),orders:read('orders',[]),coupon:read('coupon',''),search:'',wish:read('wish',[]),hasOrdered:read('hasOrdered',false)};
if(!MARKETS.some(x=>x.id===state.market))state.market='garak';
state.cart=state.cart.filter(x=>ITEMS.some(p=>p.id===x.id)&&Number.isInteger(x.qty)&&x.qty>0&&x.qty<=99);
function persist(k,v){try{localStorage.setItem('gho_'+k,JSON.stringify(v))}catch{notify('저장 공간이 부족해 임시 상태만 유지됩니다')}}
const market=id=>MARKETS.find(x=>x.id===id)||MARKETS[0];
const photo=p=>ROOT+p.img;
function setTab(tab){state.tab=tab;render();window.scrollTo({top:0,behavior:'instant'})}
let toastTimer;function notify(msg){let el=$('#toast');el.textContent=msg;el.classList.add('on');clearTimeout(toastTimer);toastTimer=setTimeout(()=>el.classList.remove('on'),3000)}
function saveCart(){persist('cart',state.cart);updateBadges()}
function updateBadges(){const n=state.cart.reduce((a,x)=>a+x.qty,0);$('#cartBadge').textContent=n;$('#cartBadge').hidden=n===0;$('#locationText').textContent=market(state.market).name;document.querySelectorAll('[data-tab]').forEach(b=>{b.classList.toggle('active',b.dataset.tab===state.tab);if(b.dataset.tab===state.tab)b.setAttribute('aria-current','page');else b.removeAttribute('aria-current')})}
function categoryCard(cat,emoji){return `<button class="category" data-category="${safe(cat)}"><span class="emoji">${emoji}</span><span>${safe(cat)}</span></button>`}
function productCard(p){return `<article class="product"><button data-detail="${p.id}" aria-label="${safe(p.name)} 상세 보기" style="border:0;background:transparent;padding:0;width:100%;text-align:left;color:inherit"><img loading="lazy" class="product-img" src="${photo(p)}" alt="${safe(p.name)} 시연 이미지"><div class="product-details"><div class="product-store">${safe(market(p.m).name)} · ${safe(p.store)}</div><h3>${safe(p.name)}</h3><span class="pill ${p.cold?'blue':''}">${p.cold?'❄ 냉장':'✓ '+safe(p.tag)}</span><div class="product-price"><strong>${money(p.price)}</strong><span class="add-mini" aria-hidden="true">＋</span></div></div></button></article>`}
function marketChips(){return `<div class="chip-scroll" aria-label="시장 선택">${MARKETS.map(m=>`<button class="chip ${state.market===m.id?'selected':''}" data-market="${m.id}" aria-pressed="${state.market===m.id}">${m.icon} ${m.name}</button>`).join('')}</div>`}
function marketCards(){return `<div>${MARKETS.map(m=>`<button class="market-card" data-market="${m.id}"><span class="icon">${m.icon}</span><span><span class="flag">${m.flag}</span><h3>${m.name}</h3><p>${m.caption}</p><p>${m.delivery}</p></span><span class="arrow">›</span></button>`).join('')}</div>`}
function catalog(){let all=ITEMS.filter(p=>p.m===state.market);if(state.cat!=='전체')all=all.filter(p=>p.cat===state.cat);return all}
function renderHome(){const m=market(state.market),all=catalog();return `<section class="hero"><div class="hero-copy"><p class="eyebrow">${m.icon} ${m.flag}</p><h1>우리 시장<br><strong>한 장바구니</strong><br>더 알뜰하게!</h1><p>${m.theme}</p><button data-action="explore">시장 상품 보기 ›</button></div><div class="hero-figure"><img src="${RIDER}" alt="가락한상 공식 웃는 시장 상인 마스코트"><span class="rider-decoration" aria-hidden="true">🛵</span></div></section><section class="section"><div class="section-h"><h2>어떤 걸 주문할까요?</h2><span class="minor">전통시장만 모았어요</span></div><div class="category-grid">${categoryCard('전체','🛒')}${categoryCard('채소·과일','🍓')}${categoryCard('수산','🐟')}${categoryCard('정육','🥩')}${categoryCard('반찬','🥗')}${categoryCard('먹거리','🥡')}${categoryCard('원단','🧵')}${categoryCard('특산물','🎁')}</div></section><div class="campaign"><img src="${RIDER}" alt="가락한상 브랜드 캐릭터"><div><strong>시장 상인 응원 쿠폰</strong><p>시연용 쿠폰을 받아보세요</p></div><button data-tab="coupons">받기 ›</button></div><section class="section"><div class="section-h"><h2>전통시장 둘러보기</h2><button class="minor" data-tab="markets" style="border:0;background:none">시장 전체 ›</button></div>${marketChips()}<p class="sub" style="padding:10px 0 0">${m.delivery} · 시연 데이터</p></section><section class="section"><div class="section-h"><h2>${m.name} 추천 상품</h2><span class="minor">${all.length}개 샘플</span></div><div class="products">${all.length?all.map(productCard).join(''):'<p>선택한 카테고리의 상품이 없습니다.</p>'}</div></section><section class="section" style="padding-bottom:20px"><div class="my-card"><h3>🛵 우리 동네 상인과 함께하는 배송</h3><p>같은 시장에서 여러 점포를 선택해도 장바구니에서 시장별 공동배송비를 시뮬레이션합니다. 실제 집하·배송 운영은 입점 계약 후 제공됩니다.</p></div></section>`}
function renderMarkets(){return `<section class="section"><h2>시장 선택</h2><p class="sub">상품 특성과 배송 방식을 고려해 한 시장씩 살펴보세요.</p>${marketCards()}</section><section class="section"><div class="my-card"><h3>왜 전통시장 전용인가요?</h3><p>점포별 묶음 장보기, 수산물 손질과 냉장 포장, 동대문 원단 B2B 견적, 지역 특산물 택배 주문 등 업종에 꼭 맞는 UX를 제공합니다.</p></div></section>`}
function renderCoupons(){return `<section class="section"><h2>🎟️ 가락한상 쿠폰센터</h2><p class="sub">전통시장 상인 응원 혜택 · 모의 쿠폰으로 실제 발급·사용 불가</p>${COUPONS.map(c=>`<div class="coupon"><div class="coupon-icon">${c.emoji}</div><div style="flex:1;min-width:0"><h3>${safe(c.title)}</h3><p>${safe(c.sub)}</p><p>대상 ${c.market==='all'?'전체 시장':market(c.market).name} · 시연 예시</p></div><button class="${state.claimed.includes(c.id)?'claimed':''}" data-claim="${c.id}" ${state.claimed.includes(c.id)?'disabled':''}>${state.claimed.includes(c.id)?'받음':'쿠폰 받기'}</button></div>`).join('')}<div class="my-card"><h3>쿠폰 안내</h3><p>주문 1회에 쿠폰 1장만 적용하며, 상품 조건·시장 조건을 모두 확인합니다. 할인액은 결제 직전 장바구니 합계에 다시 계산합니다. 쿠폰은 실제 할인 권리를 의미하지 않습니다.</p></div></section>`}
function grouped(){const groups=new Map();for(const x of state.cart){const p=ITEMS.find(v=>v.id===x.id);if(!p)continue;const k=p.m;if(!groups.has(k))groups.set(k,[]);groups.get(k).push({...x,p})}return groups}
function priceOf(entry){return entry.p.price + (entry.proc==='sliced'?3000:0)}
function shippingFor(mId,lines){if(!lines.length)return 0;const m=market(mId),stores=new Set(lines.map(x=>x.p.store));const cold=lines.some(x=>x.p.cold) ? m.cold:0;return m.min+(stores.size-1)*m.add+cold}
function shippingSaving(mId,lines){const m=market(mId);const stores=[...new Set(lines.map(x=>x.p.store))];const independent=stores.length*m.min + (lines.some(x=>x.p.cold)?m.cold:0);return mId==='region'?0:Math.max(0,independent-shippingFor(mId,lines))}
function calc(){const groups=grouped();let subtotal=0,shipping=0,savings=0;for(const [id,lines] of groups){subtotal+=lines.reduce((a,x)=>a+priceOf(x)*x.qty,0);shipping+=shippingFor(id,lines);savings+=shippingSaving(id,lines)}return {groups,subtotal,shipping,savings}}
function couponResult(t){
 if(!state.coupon||!state.claimed.includes(state.coupon))return {discount:0,target:null};
 const c=COUPONS.find(c=>c.id===state.coupon);
 if(!c||c.id==='welcome'&&state.hasOrdered)return {discount:0,target:null};
 // A coupon is evaluated on ONE market's order. Never combine subtotals across different markets.
 for(const [mid,ls] of t.groups){
  if(c.market!=='all'&&c.market!==mid)continue;
  const amount=ls.reduce((sum,x)=>sum+priceOf(x)*x.qty,0);
  if(amount<c.min)continue;
  let discount=0;
  if(c.kind==='rate')discount=Math.min(c.max,Math.floor(amount*c.amount));
  else if(c.kind==='ship'){
   if(new Set(ls.map(x=>x.p.store)).size<2)continue;
   discount=Math.min(shippingFor(mid,ls),c.amount);
  }else discount=Math.min(amount,c.amount);
  return {discount,target:mid};
 }
 return {discount:0,target:null};
}
const couponDiscount=t=>couponResult(t).discount;
function renderCart(){const t=calc();if(!state.cart.length)return `<div class="empty"><div class="big">🛵</div><h3>장바구니가 비어 있어요</h3><p>시장 상품을 담고 여러 점포를 한 번에 장보기해 보세요.</p><button class="primary" data-tab="home">시장 상품 둘러보기</button></div>`;
const groups=[...t.groups].map(([id,ls])=>`<div class="cart-group"><h3>${market(id).icon} ${market(id).name} · ${market(id).delivery}</h3>${ls.map(x=>`<div class="cart-item"><img src="${photo(x.p)}" alt=""><div><b>${safe(x.p.name)}</b><p>${safe(x.p.store)}${x.proc==='sliced'?' · 회 슬라이스 (+3,000원)':''}</p><span class="cart-item-price">${money(priceOf(x)*x.qty)}</span></div><div class="stepper"><button data-qty="${x.p.id}" data-proc="${x.proc||''}" data-delta="-1" aria-label="${safe(x.p.name)} 수량 감소">−</button><span>${x.qty}</span><button data-qty="${x.p.id}" data-proc="${x.proc||''}" data-delta="1" aria-label="${safe(x.p.name)} 수량 증가">＋</button></div></div>`).join('')}<div class="total-line" style="padding:12px 14px;margin:0"><span>이 시장 배송비 (예시)</span><b>${money(shippingFor(id,ls))}</b></div></div>`).join('');
const discount=couponDiscount(t);return `<section class="section"><div class="section-h"><h2>🛒 공동장바구니</h2><button class="minor" data-clear-cart style="border:0;background:transparent">전체 비우기</button></div><p class="title-desc">같은 시장 여러 점포는 공동배송비로 계산합니다. 서로 다른 시장은 각각 배송합니다.</p>${groups}</section><section class="section"><div class="section-h"><h2>쿠폰 적용</h2><button class="minor" data-tab="coupons" style="border:0;background:none">쿠폰 받기 ›</button></div><div class="options"><label><span>사용할 시연 쿠폰</span><select id="couponSelect" aria-label="쿠폰 선택"><option value="">사용하지 않음</option>${COUPONS.filter(c=>state.claimed.includes(c.id)).map(c=>`<option value="${c.id}" ${state.coupon===c.id?'selected':''}>${safe(c.title)}</option>`).join('')}</select></label></div></section><div class="totals"><div class="total-line"><span>상품금액</span><b>${money(t.subtotal)}</b></div><div class="total-line"><span>시장별 배송비 (시연)</span><b>${money(t.shipping)}</b></div><div class="total-line"><span>쿠폰 할인</span><b>−${money(discount)}</b></div>${t.savings>0?`<div class="savings">✓ 점포별 개별배송 대비 예상 절약 ${money(t.savings)} (시연 가정)</div>`:''}<div class="total-line strong"><span>합계</span><b>${money(t.subtotal+t.shipping-discount)}</b></div><p class="delivery-note">계산식: 같은 시장 기본 배송비 + 추가 점포비 + 필요시 냉장 포장비. 실제 운영 배송비·묶음 가능 여부는 미정입니다.</p></div><div class="cart-bottom"><button class="primary full" data-checkout>모의 주문하기 · ${money(t.subtotal+t.shipping-discount)}</button></div>`}
function renderMy(){return `<section class="section"><h2>My 가락한상</h2><p class="sub">시연 앱이므로 계정·개인정보·실제 결제 정보는 수집하지 않습니다.</p><div class="my-card"><h3>🛵 전통시장의 신선함을 집까지!</h3><p>가락한상 캐릭터와 함께 우리 동네 시장을 응원하세요.</p></div><div class="my-card"><h3>내 시연 정보</h3><p>받은 쿠폰 ${state.claimed.length}장 · 장바구니 ${state.cart.length}종 · 시연 주문 ${state.orders.length}건</p></div><div class="section-h"><h2>시연 주문 내역</h2></div>${state.orders.length?state.orders.map(o=>`<article class="order-card"><div class="map-badge">접수 시연 · 실제 배송 아님</div><h3>${safe(market(o.market).name)} · ${money(o.total)}</h3><p>${safe(o.date)} · ${o.count}개 상품 · 주문번호 ${safe(o.id)}</p></article>`).join(''):'<div class="empty"><div class="big">📦</div><h3>아직 시연 주문이 없어요</h3><p>상품을 담아 주문 흐름을 테스트해 보세요.</p></div>'}</section>`}
function renderSearch(){const q=state.search.trim().toLowerCase();const arr=q?ITEMS.filter(p=>(p.name+' '+p.store+' '+p.cat+' '+market(p.m).name).toLowerCase().includes(q)):ITEMS.filter(p=>p.m===state.market);return `<section class="section"><h2>검색 ${q?'결과':'추천'}</h2><p class="sub">${q?`‘${safe(state.search)}’ 검색 결과 ${arr.length}건`:'시장에서 인기 있는 상품을 찾아보세요.'}</p>${arr.length?`<div class="products">${arr.map(productCard).join('')}</div>`:`<div class="empty"><div class="big">🔍</div><h3>검색 결과가 없습니다</h3><p>다른 시장이나 검색어를 입력해 주세요.</p></div>`}</section>`}
function render(){updateBadges();const views={home:renderHome,markets:renderMarkets,coupons:renderCoupons,cart:renderCart,my:renderMy,search:renderSearch};$('#mainContent').innerHTML=(views[state.tab]||renderHome)();}
function add(id,proc=''){const p=ITEMS.find(x=>x.id===id);if(!p)return;const found=state.cart.find(x=>x.id===id&&x.proc===proc);if(found){if(found.qty>=99)return notify('상품당 최대 99개입니다');found.qty++}else state.cart.push({id,qty:1,proc});saveCart();render();notify(`${p.name} 장바구니에 담았어요`)}
function qty(id,proc,delta){const entry=state.cart.find(x=>x.id===id&&x.proc===proc);if(!entry)return;entry.qty+=delta;if(entry.qty<=0)state.cart=state.cart.filter(x=>x!==entry);else entry.qty=Math.min(99,entry.qty);saveCart();render()}
function modal(html){$('#modalRoot').innerHTML=`<div class="modal-scrim" id="modalScrim"><section class="modal" role="dialog" aria-modal="true" aria-label="상세 정보">${html}</section></div>`;document.body.style.overflow='hidden';$('#modalRoot .modal button')?.focus()}
function closeModal(){if($('#modalRoot').innerHTML){$('#modalRoot').innerHTML='';document.body.style.overflow=''}}
function showDetail(id){const p=ITEMS.find(x=>x.id===id);if(!p)return;const m=market(p.m);modal(`<div class="modal-title"><h2>${safe(p.name)}</h2><button class="xbtn" data-close aria-label="닫기">×</button></div><img class="modal-photo" src="${photo(p)}" alt="${safe(p.name)} 상품 시연 이미지"><div style="display:flex;justify-content:space-between;gap:8px;margin:12px 0"><span class="pill">${safe(m.name)}</span><b style="color:var(--red)">${money(p.price)}</b></div><div class="chipset"><span class="tag">${safe(p.store)}</span><span class="tag">${p.cold?'❄ 냉장 보관':'📦 일반 배송'}</span><span class="tag">시연용 상품</span></div><p class="detail-note">${m.delivery}. 상품 이미지·가격·재고·출고시간은 실제 상인 데이터가 아닌 UI 검수용 샘플입니다.</p><div class="options">${p.process?`<label><span>손질 방식</span><select id="procChoice"><option value="">기본 · 손질 없음</option><option value="sliced">회 슬라이스 +3,000원</option></select></label>`:''}${p.b2b?'<div class="tag">🧵 원단·부자재는 실제 재고 단위, 폭, 색상, 최소 주문수량 확인 후 주문하도록 상용화합니다.</div>':''}${p.m==='region'?'<div class="tag">🚚 지역별 별도 택배 · 합배송 불가</div>':''}</div><div class="modal-actions"><button class="secondary" data-close>계속 둘러보기</button><button class="primary" data-add-detail="${id}">장바구니 담기</button></div>`)}
function showMarketPicker(){modal(`<div class="modal-title"><h2>시장 선택</h2><button class="xbtn" data-close aria-label="닫기">×</button></div><p class="title-desc">지역·상품군에 맞는 시장을 선택하세요. 운영 점포는 현재 시연 데이터입니다.</p>${marketCards()}`)}
function showHelp(){modal(`<div class="modal-title"><h2>가락한상 오더 안내</h2><button class="xbtn" data-close aria-label="닫기">×</button></div><div class="my-card"><h3>서비스 상태: 디자인·기능 시연</h3><p>실제 가맹점 계약, 주문 접수, 결제, 라이더 배차, 실시간 배송, 할인권 발급, 신선식품 품질 보증이 연결되지 않았습니다. 저장되는 장바구니·시연 주문은 현재 브라우저에만 보관됩니다.</p></div><div class="my-card"><h3>한국 전통시장 특화</h3><p>가락시장 합배송, 노량진 수산물 옵션, 남대문 반찬·먹거리, 동대문 원단 B2B, 전국 특산물 택배를 별도 운영 정책으로 설계했습니다.</p></div><button class="primary full" data-close>확인</button>`)}
function checkout(){
 const t=calc();if(!state.cart.length)return;
 const {discount,target}=couponResult(t),date=new Date().toLocaleString('ko-KR',{timeZone:'Asia/Seoul'}),lines=[...t.groups];
 for(const [mid,ls] of lines){
  const sub=ls.reduce((a,x)=>a+priceOf(x)*x.qty,0),ship=shippingFor(mid,ls);
  state.orders.unshift({id:'DEMO-'+Date.now().toString(36)+'-'+mid,date,market:mid,count:ls.reduce((a,x)=>a+x.qty,0),total:sub+ship-(mid===target?discount:0)});
 }
 state.orders=state.orders.slice(0,30);persist('orders',state.orders);
 state.hasOrdered=true;persist('hasOrdered',true);state.cart=[];saveCart();state.coupon='';persist('coupon','');
 setTab('my');notify(`${lines.length}개 시장별 시연 주문이 저장되었습니다`);
}
function chooseMarket(id){if(!MARKETS.some(x=>x.id===id))return;state.market=id;state.cat='전체';state.search='';persist('market',id);closeModal();setTab('home')}
function clickHandler(event){const target=event.target.closest('button');if(!target)return;if(target.hasAttribute('data-close'))return closeModal();if(target.dataset.market)return chooseMarket(target.dataset.market);if(target.dataset.tab)return closeModal(),setTab(target.dataset.tab);if(target.dataset.category){const c=target.dataset.category;if(c==='전체'||market(state.market).types.includes(c))state.cat=c;else{const found=MARKETS.find(m=>m.types.includes(c));if(found){state.market=found.id;persist('market',state.market);state.cat=c}else state.cat='전체'}render();return}
if(target.dataset.detail)return showDetail(target.dataset.detail);if(target.dataset.addDetail){const proc=$('#procChoice')?.value||'';add(target.dataset.addDetail,proc);return closeModal()}
if(target.dataset.qty)return qty(target.dataset.qty,target.dataset.proc||'',Number(target.dataset.delta));
if(target.dataset.claim){if(!state.claimed.includes(target.dataset.claim)){state.claimed.push(target.dataset.claim);persist('claimed',state.claimed);notify('시연 쿠폰을 받았습니다');render()}return}
if(target.dataset.action==='explore'){document.querySelector('.products')?.scrollIntoView({behavior:'smooth'});return}
if(target.hasAttribute('data-clear-cart')){state.cart=[];saveCart();render();notify('장바구니를 비웠습니다');return}
if(target.hasAttribute('data-checkout'))return checkout();}
document.addEventListener('click',clickHandler);
$('#goHome').addEventListener('click',()=>setTab('home'));
$('#chooseMarket').addEventListener('click',showMarketPicker);
$('#openHelp').addEventListener('click',showHelp);
$('#searchForm').addEventListener('submit',e=>{e.preventDefault();state.search=$('#searchInput').value.slice(0,100);setTab('search')});
document.addEventListener('change',e=>{if(e.target.id==='couponSelect'){state.coupon=e.target.value;persist('coupon',state.coupon);render();if(state.coupon&&couponDiscount(calc())===0)notify('쿠폰 조건이 충족되지 않아 할인이 적용되지 않습니다')}});
document.addEventListener('click',e=>{if(e.target.id==='modalScrim')closeModal()});
document.addEventListener('keydown',e=>{if(e.key==='Escape')closeModal()});
render();
})();