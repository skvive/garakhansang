/* Local-only operations console. This is NOT a production admin authentication model. */
(()=>{'use strict';
const API='./api/v1';const money=n=>Number(n||0).toLocaleString('ko-KR')+'원';
const esc=x=>String(x??'').replace(/[&<>"']/g,ch=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[ch]));
const $=s=>document.querySelector(s);
const cfg={panel:'overview',merchant:'',market:'',data:null,busy:false,adminToken:''};
const panels={overview:['운영 대시보드','시장별 주문과 입점 현황을 한눈에 살펴보세요.'],merchants:['상인 입점·상품 관리','시장 상인의 등록 승인과 상품 재고를 모의 운영합니다.'],fulfillment:['점포별 주문 접수','상인별 주문 수락과 포장 완료를 상태에 맞춰 처리합니다.'],dispatch:['공동집하·기사 배차','여러 점포의 준비 완료 후 공동집하와 라이더 시연 배차를 진행합니다.'],campaigns:['쿠폰·브랜드 캠페인','레드 A 마스코트와 전통시장별 마케팅 캠페인 기준안입니다.']};
let toastTimer;
function toast(s){const el=$('#toast');el.textContent=s;el.classList.add('open');clearTimeout(toastTimer);toastTimer=setTimeout(()=>el.classList.remove('open'),3700)}
async function api(path,method='GET',body=null,role='admin'){
 const opts={method,headers:{'Authorization':'Bearer '+cfg.adminToken}};
 if(body!==null){opts.headers['Content-Type']='application/json';opts.body=JSON.stringify(body)}
 if(method==='POST'&&path==='/orders'){opts.headers['Idempotency-Key']='ops-seed-'+(crypto.randomUUID?.()||Date.now().toString(36)+Math.random().toString(36).slice(2))}
 const res=await fetch(API+path,opts),data=await res.json();
 if(!res.ok)throw Error(data.error||'시연 서버 오류 '+res.status);
 return data;
}
async function reload(){
 if(!cfg.adminToken){$('#apiState').textContent='관리자 토큰 필요';$('#panelContent').innerHTML='<div class="empty">로컬 서버 터미널에 출력된 관리자 토큰을 입력하세요. 이 토큰은 서버에 저장하지 않습니다.</div>';return}
 if(cfg.busy)return;cfg.busy=true;$('#reload').disabled=true;
 try{
  const [health,markets,merchants,products,orders,dashboard]=await Promise.all([
   api('/health'),api('/markets'),api('/merchants'),api('/products'),api('/orders'),api('/dashboard')]);
  cfg.data={health,markets,merchants,products,orders,dashboard};
  $('#apiState').classList.add('ok');$('#apiState').textContent='API 연결됨 · MOCK';
  if(!cfg.merchant)cfg.merchant=merchants.find(x=>x.market_id==='garak')?.id||merchants[0]?.id||'';
  render();
 }catch(e){$('#apiState').textContent='로컬 API 미연결';$('#apiState').classList.remove('ok');$('#panelContent').innerHTML=`<div class="empty"><h2>로컬 시연 서버가 필요합니다.</h2><p>압축파일 루트에서 <code>python backend/server.py</code> 실행 후 이 페이지에 접속하세요.</p><p class="muted">${esc(e.message)}</p></div>`}
 finally{cfg.busy=false;$('#reload').disabled=false}
}
function render(){
 if(!cfg.data)return;
 const [heading,desc]=panels[cfg.panel];$('#pageHeading').textContent=heading;$('#pageDescription').textContent=desc;
 document.querySelectorAll('[data-panel]').forEach(b=>b.classList.toggle('selected',b.dataset.panel===cfg.panel));
 const views={overview,merchants:merchantsView,fulfillment,dispatch,campaigns};
 $('#panelContent').innerHTML=views[cfg.panel]();
}
const statusLabel={awaiting_mock_payment:'모의 결제 대기',paid_mock:'모의 결제 완료',assembling:'점포 준비 중',ready_for_dispatch:'공동집하 완료',assigned:'기사 배정',picked_up:'픽업 완료',delivered:'배송완료 시연',cancelled:'모의 취소'};
const statusTag=s=>`<span class="pill ${s==='delivered'||s==='ready'?'green':s==='awaiting_mock_payment'?'red':'blue'}">${esc(statusLabel[s]||s)}</span>`;
const marketName=id=>cfg.data.markets.find(x=>x.id===id)?.name||id;
const merchantName=id=>cfg.data.merchants.find(x=>x.id===id)?.name||id;
function overview(){const {dashboard:d,orders,merchants}=cfg.data;
 const pending=d.merchants_pending,delivered=orders.filter(x=>x.status==='delivered').length,waiting=orders.filter(x=>x.status==='awaiting_mock_payment').length;
 return `<div class="stats"><div class="stat"><span>데모 주문 누적</span><b>${orders.length}</b><small>실제 매출 0원</small></div><div class="stat"><span>상인 입점 샘플</span><b>${merchants.length}</b><small>승인 대기 ${pending}건</small></div><div class="stat"><span>모의 결제 대기</span><b>${waiting}</b><small>실제 PG 미연결</small></div><div class="stat"><span>배송완료 시연</span><b>${delivered}</b><small>실배송 데이터 없음</small></div></div>
 <div class="cards2"><section class="card"><h2>🛵 주문 진행 현황</h2>${d.orders_by_status.length?d.orders_by_status.map(x=>`<div class="line"><span>${statusLabel[x.status]||esc(x.status)}</span><strong>${x.count}건</strong></div>`).join(''):'<div class="empty">아직 시연 주문이 없습니다.</div>'}<button class="button" id="seedOrder" style="margin-top:16px">가락시장 샘플 주문 생성</button><p class="muted">테스트 상품 2개를 서버 가격으로 주문하고 모의 결제합니다. 실제 고객이나 상인에게 전달되지 않습니다.</p></section>
 <section class="card"><h2>📦 시장별 운영 정책</h2>${cfg.data.markets.map(x=>`<div class="line"><span>${esc(x.name)}</span><span class="pill">기본 ${money(x.base_fee)} (예시)</span></div>`).join('')}<p class="muted">수산물 냉장배송과 지역별 택배는 별도의 실제 운송 계약이 필요합니다.</p></section></div>
 <div class="cards2"><section class="card"><h2>최근 시연 주문</h2>${orders.length?orders.slice(0,5).map(o=>`<div class="line"><div><span class="order-id">${esc(o.id)}</span><div class="muted">${esc(marketName(o.market_id))} · ${money(o.total)}</div></div>${statusTag(o.status)}</div>`).join(''):'<p>기록 없음</p>'}</section><section class="card"><h2>출시 전 필수 보완</h2><div class="list"><span>✓ 데모 주문 중복 방지·서버 가격 검증</span><span>⚠ 상인 실명/사업자등록 인증 미구현</span><span>⚠ PG 결제·환불·정산 미연결</span><span>⚠ 실제 라이더 GPS·온도기록 미연결</span><span>⚠ Neon 운영 DB 이관·인증 미완료</span></div></section></div>`;
}
function merchantsView(){const {merchants,products,markets}=cfg.data;
 const pending=merchants.filter(m=>m.status==='pending');
 return `<div class="callout"><strong>상인 직접 입점형 서비스</strong> · 동일 시장 내 점포들의 상품을 공동집하하고 신선·상온 물류 요건을 별도로 검사합니다. 시연 입점은 실제 계약·인증을 의미하지 않습니다.</div>
 <div class="card"><h2>신규 상인 입점 시연</h2><form id="applyMerchant" class="toolbar"><select name="market_id" class="select" required>${markets.map(m=>`<option value="${esc(m.id)}">${esc(m.name)}</option>`).join('')}</select><input class="select" name="name" placeholder="상호 예: 가락새싹상회 (시연)" minlength="2" maxlength="70" required><button class="button" type="submit">입점 신청 시연</button></form><p class="muted">사업자등록번호, 연락처 등 민감한 실제 상인 정보는 입력하지 마세요.</p></div>
 <div class="cards2"><div class="card"><h2>승인 대기 (${pending.length})</h2>${pending.length?pending.map(m=>`<div class="line"><div><b>${esc(m.name)}</b><div class="muted">${esc(marketName(m.market_id))}</div></div><button class="button small" data-approve="${esc(m.id)}">승인 시연</button></div>`).join(''):'<p class="muted">입점 대기 없음</p>'}</div><div class="card"><h2>샘플 재고 변경</h2><form id="updateStock" class="toolbar"><select class="select" name="product_id">${products.map(p=>`<option value="${esc(p.id)}">${esc(p.name)} (${p.stock}개)</option>`).join('')}</select><input class="select" name="stock" type="number" min="0" max="100000" value="30" required style="width:105px"><button class="button" type="submit">재고 적용</button></form><p class="muted">재고는 로컬 SQLite 시연 DB에 저장됩니다.</p></div></div>
 <div class="card" style="margin-top:16px"><h2>시장별 상인 현황</h2><div class="merchant-grid">${merchants.map(m=>`<div class="merchant-head"><div class="store-emoji">🏪</div><div><h3>${esc(m.name)}</h3><p>${esc(marketName(m.market_id))}</p><div class="meta-row"><span class="pill ${m.status==='approved'?'green':'red'}">${m.status==='approved'?'시연 승인':'심사 대기'}</span><span class="pill">상품 ${products.filter(p=>p.merchant_id===m.id).length}개</span></div></div></div>`).join('')}</div></div>`;
}
function fulfillment(){const {merchants,orders}=cfg.data,mid=cfg.merchant;const belongs=orders.filter(o=>o.fulfillment.some(f=>f.merchant_id===mid));const store=merchants.find(m=>m.id===mid);
 return `<div class="callout">상인별 권한 시연: <strong>선택 상점의 상품만</strong> 접수·포장 준비할 수 있도록 상태를 분리했습니다. 실제 로그인·점포 권한 검증은 상용 버전에 별도로 필요합니다.</div><div class="toolbar"><label for="merchantSelect">시연 점포</label><select id="merchantSelect" class="select">${merchants.filter(m=>m.status==='approved').map(m=>`<option value="${esc(m.id)}" ${m.id===mid?'selected':''}>${esc(marketName(m.market_id))} / ${esc(m.name)}</option>`).join('')}</select></div>
 ${belongs.length?`<div class="order-grid">${belongs.map(o=>{const f=o.fulfillment.find(f=>f.merchant_id===mid),lines=o.lines.filter(l=>l.merchant_id===mid);return `<article class="card"><div class="line"><b class="order-id">${esc(o.id)}</b>${statusTag(o.status)}</div><h2>${esc(store?.name||'상점 주문')}</h2><p class="muted">${esc(marketName(o.market_id))} · ${lines.reduce((sum,l)=>sum+l.qty,0)}개 수량</p>${lines.map(l=>`<div class="line"><span>${esc(l.name_snapshot)} × ${l.qty}</span><b>${money(l.qty*l.unit_price)}</b></div>`).join('')}<div class="meta-row"><span class="pill ${f.status==='ready'?'green':'blue'}">점포 상태: ${esc(f.status)}</span></div><div class="toolbar"><button class="button" data-fulfill="${esc(o.id)}" data-store="${esc(mid)}" data-next="accepted" ${f.status!=='pending'||o.status!=='paid_mock'?'disabled':''}>① 주문 수락</button><button class="button green" data-fulfill="${esc(o.id)}" data-store="${esc(mid)}" data-next="ready" ${f.status!=='accepted'?'disabled':''}>② 포장 완료</button></div></article>`}).join('')}</div>`:'<div class="empty">이 점포에 들어온 시연 주문이 없습니다. 운영 현황에서 샘플 주문을 생성하세요.</div>'}`;
}
function dispatch(){const orders=cfg.data.orders.filter(o=>o.status!=='cancelled');return `<div class="callout"><strong>시장별 공동집하</strong>: 가락시장 주문은 가락시장 내부에서만 묶습니다. 노량진·동대문 등 서로 다른 시장의 주문은 합배송하지 않습니다. 냉장·상온 분리 및 실제 라이더 위치 확인은 미구현입니다.</div>
 ${orders.length?`<div class="order-grid">${orders.map(o=>{const ready=o.fulfillment.length&&o.fulfillment.every(f=>f.status==='ready');const job=o.dispatch[0];return `<article class="card"><div class="line"><b class="order-id">${esc(o.id)}</b>${statusTag(o.status)}</div><h2>${esc(marketName(o.market_id))}</h2><p class="muted">상품 ${money(o.subtotal)} + 배송 ${money(o.shipping)} − 할인 ${money(o.discount)}</p><div class="steps">${o.fulfillment.map(f=>`<span class="step ${f.status==='ready'?'done':''}">${esc(f.name)}: ${esc(f.status)}</span>`).join('')}</div><div class="toolbar">${o.status==='awaiting_mock_payment'?`<button class="button" data-pay="${esc(o.id)}">모의 결제 완료</button>`:''}${o.status==='assembling'&&ready?`<button class="button green" data-collect="${esc(o.id)}">공동집하 인수</button>`:''}${job&&job.status==='waiting'?`<button class="button" data-assign="${esc(job.id)}">🛵 기사 배정</button>`:''}${job&&job.status==='assigned'?`<button class="button" data-job="${esc(job.id)}" data-next="pick-up">픽업 완료</button>`:''}${job&&job.status==='picked_up'?`<button class="button green" data-job="${esc(job.id)}" data-next="deliver">배송완료 시연</button>`:''}${o.status==='delivered'?'<span class="pill green">배송완료 시연</span>':''}</div></article>`}).join('')}</div>`:'<div class="empty">아직 시연 주문이 없습니다.</div>'}`;
}
function campaigns(){return `<div class="coupon-preview"><span class="tiny">GARAK HANSANG ORDER / OFFICIAL CHARACTER RED A</span><strong>시장 상인 응원 혜택</strong><p>앱으로 시장 장보고, 같은 시장 여러 점포를 한 번에!</p><img src="mascot-rider.webp" alt="오토바이를 타는 가락한상 오더 캐릭터"></div><div class="coupon-grid">${[['첫 주문 체험','5,000원','30,000원 이상 첫 주문','전체 전통시장'],['가락시장 공동장보기','최대 3,500원','20,000원 이상 10%','가락시장'],['노량진 신선배송','3,000원','30,000원 이상','노량진수산시장'],['여러 점포 합배송','최대 2,500원','같은 시장 2점포·30,000원 이상','전체 시장']].map(c=>`<section class="card"><span class="pill red">${esc(c[3])}</span><h2 style="margin-top:14px">${esc(c[0])}</h2><strong style="font-size:26px;color:var(--red)">${esc(c[1])}</strong><p>${esc(c[2])}</p><span class="muted">시연 혜택 · 실제 발행 불가</span></section>`).join('')}</div><div class="cards2"><section class="card"><h2>시장 특화 마케팅 전략</h2><div class="list">🥬 가락시장 — 식당 정기장보기·배송비 절약 캠페인<br>🐟 노량진 — 회 손질·냉장배송 콘텐츠<br>🍱 남대문 — 점심·퇴근길 반찬 큐레이션<br>🧵 동대문 — 원단 도매 견적·빠른 퀵배송<br>🏞️ 지역시장 — 로컬 특산물 선물 기획전</div></section><section class="card"><h2>쿠폰 운영 안전장치</h2><p>단일 주문당 1장, 시장별 최소 주문금액 검증, 전체 시장 합산 조건 금지, 서버 재계산, 예산 한도·중복 발급·광고 수신 동의 검증을 상용 출시 전 반드시 구현합니다.</p></section></div>`}
async function runAction(target){if(cfg.busy)return;
 try{
  if(target.id==='seedOrder'){
   const x=await api('/orders','POST',{lines:[{id:'g1',qty:2,proc:''},{id:'g2',qty:1,proc:''}],coupon_id:'marketday'});
   for(const o of x.orders)await api('/orders/'+o.id+'/mock-pay','POST',{},'admin');toast('가락시장 다점포 모의 주문을 생성·모의 결제했습니다');
  }else if(target.dataset.approve) {await api('/merchants/'+encodeURIComponent(target.dataset.approve)+'/approve','POST',{});toast('시연 상인 승인 완료')}
  else if(target.dataset.fulfill){await api('/orders/'+encodeURIComponent(target.dataset.fulfill)+'/merchants/'+encodeURIComponent(target.dataset.store)+'/status','POST',{status:target.dataset.next},'merchant');toast('점포 상태를 변경했습니다')}
  else if(target.dataset.collect){await api('/orders/'+encodeURIComponent(target.dataset.collect)+'/hub-collect','POST',{},'hub');toast('공동집하 시연 완료')}
  else if(target.dataset.assign){await api('/dispatch/'+encodeURIComponent(target.dataset.assign)+'/assign','POST',{rider_alias:'가락한상 데모라이더'},'hub');toast('시연 라이더 배정')}
  else if(target.dataset.job){await api('/dispatch/'+encodeURIComponent(target.dataset.job)+'/'+target.dataset.next,'POST',{},'rider');toast('라이더 상태 변경 완료')}
  else if(target.dataset.pay){await api('/orders/'+encodeURIComponent(target.dataset.pay)+'/mock-pay','POST',{});toast('모의 결제 완료')}
  else return;
  await reload();
 }catch(e){toast('처리 불가: '+e.message)}
}
document.querySelector('#adminLogin').addEventListener('submit',e=>{e.preventDefault();cfg.adminToken=document.querySelector('#demoAdminToken').value.trim();document.querySelector('#demoAdminToken').value='';reload()});
document.addEventListener('click',e=>{const nav=e.target.closest('[data-panel]');if(nav){cfg.panel=nav.dataset.panel;render();return}const btn=e.target.closest('button');if(btn)runAction(btn)});
$('#reload').addEventListener('click',reload);
document.addEventListener('change',e=>{if(e.target.id==='merchantSelect'){cfg.merchant=e.target.value;render()}});
document.addEventListener('submit',async e=>{if(!['applyMerchant','updateStock'].includes(e.target.id))return;e.preventDefault();const f=e.target,data=Object.fromEntries(new FormData(f));try{
 if(f.id==='applyMerchant'){await api('/merchants/apply','POST',{market_id:data.market_id,name:data.name},'merchant');toast('시연 입점 신청 완료')}
 else {const p=cfg.data.products.find(x=>x.id===data.product_id);await api('/merchants/'+p.merchant_id+'/products/'+p.id+'/stock','POST',{stock:Number(data.stock)},'merchant');toast('시연 재고 변경 완료')}
 await reload();}catch(err){toast('처리 불가: '+err.message)}});
reload();
})();
