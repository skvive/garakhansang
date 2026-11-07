/* Garak Order laboratory — browser UI for synthetic localhost-only endpoints.
   No secret keys, card collection or actual purchases are executed in the browser. */
"use strict";

const API="/lab/api";
const $=(selector)=>document.querySelector(selector);
const roles={
  customer:{title:"고객 주문",description:"상품 선택부터 배달 진행까지",lead:"검증된 샘플 상품을 살펴보고 테스트 주문을 만드세요.",kicker:"CUSTOMER · ORDER",icon:"🛒"},
  merchant:{title:"입점상인 운영",description:"내 매장 주문과 재고만 관리",lead:"입점 매장으로 들어온 결제 완료 주문을 처리합니다.",kicker:"MERCHANT · FULFILLMENT",icon:"🏬"},
  rider:{title:"라이더 배달",description:"배차부터 전달까지 확인",lead:"검증된 배차 요청을 수락하고 배송 단계를 처리합니다.",kicker:"RIDER · DELIVERY",icon:"🛵"},
  ops:{title:"통합 운영관제",description:"입점·결제·배차·정산 모니터링",lead:"모든 시뮬레이션 거래를 안전하게 검증하는 중앙 관제입니다.",kicker:"ADMIN · OPERATIONS",icon:"📊"},
};
const statusLabel={
  payment_pending:"결제 대기",paid:"결제 확인",merchant_accepted:"상인 접수",
  preparing:"조리 중",ready_for_pickup:"픽업 준비",dispatch_requested:"배차 요청",
  rider_assigned:"라이더 배정",picked_up:"픽업 완료",in_transit:"배달 중",
  delivered:"배송 완료",refund_pending:"환불 처리 대기",refunded:"환불 검증 완료"
};
const notificationLabel={
  new_paid_order:"새 결제 확인 주문",
  merchant_accepted:"상인이 주문을 수락했습니다",
  preparing:"상품 준비 중",
  ready_for_pickup:"픽업 준비 완료",
  job_available:"새로운 배차 요청",
  rider_assigned:"라이더가 배정됐습니다",
  picked_up:"상품 픽업 완료",
  in_transit:"배송 출발",
  delivered:"배송 완료",
  refund_required:"환불 검토 요청",
  refund_completed:"환불 처리 확인"
};
const nextMerchant={
  paid:["merchant_accept","주문 수락"],merchant_accepted:["merchant_prepare","조리 시작"],
  preparing:["merchant_ready","픽업 준비완료"],
  ready_for_pickup:["merchant_request_dispatch","배차 요청"]
};
const nextRider={
  rider_assigned:["rider_pickup","픽업 완료"],
  picked_up:["rider_start_delivery","배송 시작"],
  in_transit:["rider_deliver","배송 완료"]
};
let S={role:null,csrf:"",products:[],orders:[],inbox:[],merchants:[],
  riders:[],dispatch:[],settlements:[],cart:{},section:"primary",
  seen:new Set(),inboxPrimed:false,permission:false};

function node(tag,cl="",value){
  const e=document.createElement(tag);
  if(cl)e.className=cl;
  if(value!==undefined)e.textContent=String(value);
  return e;
}
function add(parent,...items){for(const i of items)if(i)parent.append(i);return parent}
function btn(label,click,kind="outline",disabled=false){
  const b=node("button",kind,label);b.type="button";b.disabled=disabled;
  b.addEventListener("click",async()=>{if(b.disabled)return;
    b.disabled=true;
    try{await click()}catch(e){toast(e.message)}finally{b.disabled=false}
  });return b;
}
function newIdempotencyKey(){
  if(!globalThis.crypto || typeof crypto.getRandomValues!=="function")
    throw Error("안전한 난수 생성 기능이 없는 브라우저에서는 주문할 수 없습니다.");
  if(typeof crypto.randomUUID==="function")
    return crypto.randomUUID().replaceAll("-","")+"-lab";
  const bytes=new Uint8Array(20);
  crypto.getRandomValues(bytes);
  return Array.from(bytes,b=>b.toString(16).padStart(2,"0")).join("")+"-lab";
}
function format(n){return Intl.NumberFormat("ko-KR").format(n||0)+"원"}
function title(parent,t,desc){
  const head=node("div","section-head"),left=node("div");
  add(left,node("h2","",t),node("p","subtitle",desc));
  head.append(left);parent.append(head);return head;
}
function empty(parent,head,body){
  const wrap=node("div","empty");add(wrap,node("strong","",head),node("span","",body));parent.append(wrap)
}
function label(s){return statusLabel[s]||s||"알 수 없음"}
function toast(msg,good=false){const el=$("#toast");el.hidden=false;
  el.className="toast"+(good?" good":"");el.textContent=msg;
  clearTimeout(toast.timer);toast.timer=setTimeout(()=>el.hidden=true,7500)}
async function api(path,method="GET",body){
  const res=await fetch(API+path,{method,credentials:"same-origin",
    headers:{"Content-Type":"application/json",...(method==="POST"?{"X-Lab-CSRF":S.csrf}:{})},
    ...(body!==undefined?{body:JSON.stringify(body)}:{})});
  let json;
  try{json=await res.json()}catch{throw Error("서버 응답을 읽을 수 없습니다.")}
  if(!res.ok)throw Error("요청 실패 ("+res.status+"): "+(json.error||"다시 시도해 주세요."));
  return json;
}
async function load(notify=false){
  if(!S.role)return;
  const targets=[["orders","/orders"],["inbox","/inbox"]];
  if(S.role==="customer"||S.role==="merchant")targets.push(["products","/products"]);
  if(S.role==="ops")targets.push(["merchants","/merchants"],["riders","/riders"],["settlements","/settlements"]);
  if(S.role==="merchant")targets.push(["settlements","/settlements"]);
  if(S.role==="rider")targets.push(["dispatch","/dispatch"]);
  const data=await Promise.all(targets.map(async ([name,path])=>({name,data:await api(path)})));
  for(const obj of data)S[obj.name]=obj.data.items||[];
  if(notify&&S.inboxPrimed&&"Notification" in window&&Notification.permission==="granted"){
    for(const e of S.inbox){
      const key=[e.order_id,e.event,e.created_at].join(":");
      if(!S.seen.has(key))new Notification("가락한상 테스트 알림",{body:notificationLabel[e.event]||label(e.event)});
    }
  }
  for(const e of S.inbox)S.seen.add([e.order_id,e.event,e.created_at].join(":"));
  S.inboxPrimed=true;
  render();
}
async function mutate(path,data,success){
  await api(path,"POST",data);toast(success||"테스트 기록이 갱신되었습니다.",true);await load();
}
function roleText(){
  const r=roles[S.role];
  $("#who").textContent=r.icon+" "+r.title;
  $("#role-title").textContent=r.title;
  $("#role-description").textContent=r.description;
  $("#page-title").textContent=r.title+" 대시보드";
  $("#page-lead").textContent=r.lead;
  $("#section-eyebrow").textContent=r.kicker;
}
function metric(parent,labelText,value,extra){
  const e=node("div","metric");
  add(e,node("span","metric-label",labelText),node("strong","metric-value",value),
      node("span","metric-sub",extra));parent.append(e)
}
function renderMetrics(){
  const e=$("#metrics");e.replaceChildren();
  metric(e,"확인 가능한 주문",S.orders.length,"샌드박스 주문 원장");
  metric(e,S.role==="rider"?"배차 후보":"처리 대기",
    S.role==="rider"?S.dispatch.length:
    S.orders.filter(x=>["payment_pending","paid","dispatch_requested","refund_pending"].includes(x.state)).length,
    "역할별 처리 조건 적용");
  metric(e,"완료된 테스트 배송",S.orders.filter(o=>o.state==="delivered").length,"실배송 아님");
  metric(e,"알림 기록",S.inbox.length,"현재 역할만 조회");
}
function buttonRow(card){
  const div=node("div","actions");card.append(div);return div
}
function renderOrders(){
  const root=$("#orders");root.replaceChildren();
  title(root,"주문 타임라인","주문 상태는 서버 원장에 저장되고 역할별 권한에 따라 변경됩니다.");
  if(!S.orders.length){
    const help={
      customer:"상품을 장바구니에 담고 테스트 주문을 생성하세요.",
      merchant:"해당 상점의 결제 완료 테스트 주문을 기다리고 있습니다.",
      rider:"배차를 수락하면 이곳에서 배송 상태를 변경할 수 있습니다.",
      ops:"고객 주문을 만든 뒤 운영자 결제 검증을 진행하세요."
    };
    empty(root,"아직 주문이 없습니다.",help[S.role]||"");return
  }
  const container=node("div","stack");
  for(const o of S.orders){
    const card=node("article","order-card"),head=node("div","order-head"),labelBox=node("div");
    const tag=node("span","tag "+o.state,label(o.state));
    add(labelBox,node("strong","",o.id),node("div","order-meta",
      "상인 #"+o.merchant_id+" · 주문금액 "+format(o.total_krw)+" · 상태 버전 "+o.version));
    add(head,labelBox,tag);card.append(head);
    const actions=buttonRow(card);
    if(S.role==="merchant"&&nextMerchant[o.state]){
      const [event,name]=nextMerchant[o.state];
      actions.append(btn(name,()=>mutate("/order/"+o.id+"/transition",{event,version:o.version},name+" 처리 완료"),"primary small"));
    }
    if(S.role==="merchant"&&o.state==="paid")
      actions.append(btn("접수 거절·환불 요청",()=>mutate("/order/"+o.id+"/transition",
        {event:"merchant_reject",version:o.version},"환불 검토에 등록했습니다."),"danger"));
    if(S.role==="customer"&&o.state==="paid")
      actions.append(btn("주문 취소 신청",()=>mutate("/order/"+o.id+"/transition",
        {event:"customer_cancel",version:o.version},"환불 검토에 등록했습니다."),"danger"));
    if(S.role==="rider"&&nextRider[o.state]){
      const [event,name]=nextRider[o.state];
      actions.append(btn(name,()=>mutate("/order/"+o.id+"/transition",
       {event,version:o.version},name+" 처리 완료"),"primary small"));
    }
    if(S.role==="ops"&&o.state==="payment_pending"){
      actions.append(btn("모의 Stripe 결제 검증",()=>mutate("/order/"+o.id+"/simulate-paid",{},
      "가상 서명 이벤트로 결제 상태를 검증했습니다."),"primary small"));
    }
    if(S.role==="ops"&&o.state==="refund_pending"){
      actions.append(btn("모의 환불 완료 검증",()=>mutate("/order/"+o.id+"/simulate-refund",{},
      "가상 환불 처리 기록을 완료했습니다."),"danger"));
    }
    if(!actions.childNodes.length)actions.append(node("span","micro","현재 역할에서 처리할 다음 작업이 없습니다."));
    container.append(card);
  }
  root.append(container);
}
function productIcon(c){return {seafood:"🐟",meat:"🥩",produce:"🥬",sets:"🍱",extras:"🍤"}[c]||"🍽️"}
function productImage(p){
  const wrap=node("div","product-photo");
  if(typeof p.image==="string"&&/^assets\/images\/[a-z0-9_./-]+\.webp$/i.test(p.image)&&!p.image.includes("..")){
    const image=node("img");image.src="/"+p.image;image.loading="lazy";image.alt=p.name||"상품 사진";
    image.addEventListener("error",()=>image.classList.add("is-missing"));
    wrap.append(image);
  }
  wrap.append(node("span","",productIcon(p.category)));
  return wrap;
}
function detail(p){
  const modal=node("dialog","detail-dialog");
  modal.style.cssText="border:1px solid #ded6cc;border-radius:20px;max-width:480px;width:calc(100% - 32px);padding:24px;box-shadow:0 14px 50px #2224";
  modal.append(productImage(p));
  add(modal,node("h2","",p.name),node("p","micro","판매자: "+p.merchant+" · 원산지: "+(p.origin||"판매 검증 필요")),
      node("p","micro","알레르기 정보·상품옵션·배송권역은 운영 검증 전입니다."),
      node("strong","product-price",format(p.price_krw)));
  modal.append(btn("확인 후 닫기",()=>modal.close(),"primary"));
  modal.addEventListener("close",()=>modal.remove());
  document.body.append(modal);modal.showModal();
}
function renderCustomer(){
  const root=$("#primary");root.replaceChildren();
  const grid=node("div","grid-two"),productsSide=node("div"),cartSide=node("div","sub-panel tint");
  title(productsSide,"상품 상세 · 장바구니","기존 승인 샘플 상품을 서버 가격으로 표시합니다. 결제는 로컬 시뮬레이션입니다.");
  const cardGrid=node("div","cards");
  for(const p of S.products){
    const card=node("article","product"),body=node("div","product-body");
    add(body,node("span","micro",p.merchant),
        node("strong","product-name",p.name),
        node("span","product-meta","샘플 재고 "+p.stock+" · "+(p.origin||"원산지 미확정")),
        node("strong","product-price",format(p.price_krw)));
    const actions=node("div","actions product-action");
    actions.append(btn("상세",()=>detail(p),"outline small"));
    actions.append(btn("＋ 담기",async()=>{
      const qty=S.cart[p.slug]||0;
      if(qty>=p.stock||qty>=99){toast("테스트 재고를 초과했습니다.");return}
      S.cart[p.slug]=qty+1;render();
    },"primary small",p.stock<1));
    body.append(actions);add(card,productImage(p),body);cardGrid.append(card);
  }
  if(!S.products.length)empty(productsSide,"승인 상품이 없습니다.","관리자가 테스트 매장을 승인하면 상품이 표시됩니다.");
  else productsSide.append(cardGrid);
  title(cartSide,"내 장바구니","단일 입점상인 단위 테스트 주문만 허용합니다.");
  const cartItems=Object.entries(S.cart).filter(([,n])=>n>0);
  let total=0;
  if(!cartItems.length)empty(cartSide,"장바구니가 비었습니다.","상품 카드의 담기 버튼을 누르세요.");
  for(const [slug,qty] of cartItems){
    const p=S.products.find(i=>i.slug===slug);
    if(!p)continue;
    const line=node("div","line"),left=node("div"),count=node("div","qty");
    add(left,node("strong","",p.name),node("small","",format(p.price_krw)+" × "+qty));
    add(count,btn("−",async()=>{S.cart[slug]=Math.max(0,qty-1);render()}),
        node("span","",qty),btn("+",async()=>{if(qty<p.stock){S.cart[slug]=qty+1;render()}}));
    add(line,left,count);cartSide.append(line);total+=p.price_krw*qty;
  }
  if(cartItems.length){
    const details=node("div");
    add(details,
      add(node("div","price-line"),node("span","","상품 소계"),node("strong","",format(total))),
      add(node("div","price-line"),node("span","","실배송비"),node("span","","미검증")),
      add(node("div","price-line"),node("span","","합성 테스트 배송료"),node("strong","",format(2000))),
      add(node("div","price-line total"),node("span","","테스트 합계"),node("strong","",format(total+2000))));
    cartSide.append(details);
    cartSide.append(btn("테스트 주문 생성",async()=>{
      const items=cartItems.map(([slug,qty])=>({slug,qty}));
      await mutate("/order/draft",{items,idempotency_key:newIdempotencyKey()},
        "테스트 주문이 생성되었습니다. 운영자 화면에서 모의 결제 검증이 필요합니다.");
      S.cart={};render();
    },"primary full"));
    cartSide.append(node("p","micro","카드 결제나 실제 주문 접수는 진행되지 않습니다."));
  }
  add(grid,productsSide,cartSide);root.append(grid);
}
function renderMerchant(){
  const root=$("#primary");root.replaceChildren();
  title(root,"내 매장 운영·재고","현재 로그인된 상인에게 승인된 상품만 표시합니다. 타 상점 접근은 서버가 거부합니다.");
  if(!S.products.length){empty(root,"운영할 상품이 없습니다.","입점 확인 및 관리자 승인이 필요합니다.");return}
  const table=node("div","table-scroll"),tbl=node("table","data-table");
  const th=node("tr");for(const text of ["상품명","테스트 가격","현재 재고","재고 수정"])th.append(node("th","",text));
  const thead=node("thead");thead.append(th);tbl.append(thead);const tbody=node("tbody");
  for(const p of S.products){
    const row=node("tr"),input=node("input","field");input.type="number";input.min="0";input.max="10000";input.value=p.stock;input.setAttribute("aria-label",p.name+" 재고");
    for(const v of [p.name,format(p.price_krw),p.stock])row.append(add(node("td"),node("span","",v)));
    const form=node("div","inline-form");form.append(input);
    form.append(btn("저장",()=>mutate("/products/stock",{slug:p.slug,stock:Number(input.value)},"재고가 업데이트되었습니다."),"primary small"));
    row.append(add(node("td"),form));tbody.append(row);
  }
  tbl.append(tbody);table.append(tbl);root.append(table);
  root.append(node("p","micro","영업시간, 프로모션, 실제 계약/정산계좌는 별도 운영 승인 전입니다."));
}
function renderRider(){
  const root=$("#primary");root.replaceChildren();
  const head=title(root,"배차 신청함","승인·근무 중인 라이더에게만 배차 후보를 제공합니다. 고객 주소는 배정 전 공개하지 않습니다.");
  head.append(btn("근무 시작",()=>mutate("/rider/duty",{on_duty:true},"테스트 근무 상태를 시작했습니다."),"outline small"));
  head.append(btn("근무 종료",()=>mutate("/rider/duty",{on_duty:false},"테스트 근무 상태를 종료했습니다."),"outline small"));
  if(!S.dispatch.length){empty(root,"현재 배차 가능한 주문이 없습니다.","상인이 결제된 주문의 픽업 준비를 마친 뒤 배차 요청을 생성하세요.");return}
  const offers=node("div","stack");
  for(const o of S.dispatch){
    const card=node("div","order-card");
    add(card,node("strong","",o.id),node("p","micro","상점 #"+o.merchant_id+" · 테스트 배달비 "+format(o.delivery_fee_krw)));
    card.append(btn("배차 수락",()=>mutate("/order/"+o.id+"/transition",
      {event:"rider_accept",version:o.version},"테스트 배차를 수락했습니다."),"primary small"));
    offers.append(card);
  }
  root.append(offers);
}
function renderAdmin(){
  const root=$("#primary");root.replaceChildren();
  title(root,"입점·라이더 승인 관제","상품 승인, 라이더 근무권한과 테스트 정산액을 한곳에서 관리합니다.");
  const dual=node("div","grid-two"),left=node("div","sub-panel"),right=node("div","sub-panel");
  left.append(node("h3","","입점상인 관리"));
  for(const m of S.merchants){
    const line=node("div","line"),desc=node("div");
    add(desc,node("strong","",m.name),node("small","",m.status+" · 심사 "+(m.verified?"완료":"대기")));
    add(line,desc,btn(m.verified?"승인 완료":"매장 승인",()=>mutate("/merchants/approve",{id:m.id},"테스트 입점승인이 완료되었습니다."),
      "primary small",!!m.verified));left.append(line);
  }
  right.append(node("h3","","라이더 승인"));
  for(const r of S.riders){
    const line=node("div","line"),desc=node("div");
    add(desc,node("strong","",r.subject),node("small","",(r.approved?"승인":"심사대기")+" · "+(r.on_duty?"근무 중":"미근무")));
    add(line,desc,btn(r.approved?"승인 해제":"라이더 승인",
      ()=>mutate("/riders/approve",{sub:r.subject,approved:!r.approved},"라이더 승인 상태를 변경했습니다."),
      r.approved?"danger":"primary small"));right.append(line);
  }
  add(dual,left,right);root.append(dual);
  const settling=node("div","sub-panel");settling.style.marginTop="18px";
  title(settling,"테스트 정산 예상액","배송 완료 주문 기준의 단순 수수료 계산이며 지급·PG 정산과 무관합니다.");
  if(!S.settlements.length)empty(settling,"정산 가능한 주문 없음","라이더가 배송 완료 처리를 한 뒤 계산합니다.");
  else for(const s of S.settlements){
    const line=node("div","line"),left=node("div");
    add(left,node("strong","",s.order_id),node("small","","상점 #"+s.merchant_id+" · 수수료 "+format(s.commission_krw)));
    add(line,left,node("strong","",format(s.merchant_due_krw)));settling.append(line);
  }
  root.append(settling);
}
function renderInbox(){
  const root=$("#inbox");root.replaceChildren();const head=title(root,"역할별 알림함","단일 주문 원장에서 기록된 알림입니다. 운영 FCM 전송이 아닌 로컬 기록/폴링 검증입니다.");
  if("Notification" in window){
    head.append(btn("브라우저 알림 허용",async()=>{
      const result=await Notification.requestPermission();
      toast(result==="granted"?"현재 열린 브라우저에서 테스트 알림을 표시합니다.":"알림이 허용되지 않았습니다.",result==="granted");
    },"outline small"));
  }
  if(!S.inbox.length){empty(root,"새 알림이 없습니다.","주문 상태가 전환되면 이 역할에 해당하는 알림이 표시됩니다.");return}
  const lines=node("div","stack");
  for(const notice of S.inbox){
    const item=node("div","inbox-line"),desc=node("div");
    add(desc,node("strong","",notificationLabel[notice.event]||label(notice.event)),node("small","",notice.order_id));
    add(item,desc,node("span","micro","TEST EVENT"));
    lines.append(item);
  }
  root.append(lines);
}
function render(){
  if(!S.role)return;
  roleText();renderMetrics();renderOrders();renderInbox();
  if(S.role==="customer")renderCustomer();
  else if(S.role==="merchant")renderMerchant();
  else if(S.role==="rider")renderRider();
  else renderAdmin();
  document.querySelectorAll(".nav-item").forEach(el=>{
    el.classList.toggle("active",el.dataset.target===S.section);
  });
}
function workspace(){
  $("#login-screen").hidden=true;$("#workspace").hidden=false;$("#logout").hidden=false;
  render();window.scrollTo(0,0);
}
$("#login-form").addEventListener("submit",async e=>{
  e.preventDefault();$("#auth-message").textContent="";
  try{
    const role=$("#username").value;
    const result=await api("/login","POST",{username:role,password:$("#password").value});
    S.role=result.role;S.csrf=result.csrf;S.cart={};
    S.inboxPrimed=false;S.seen=new Set();
    $("#password").value="";
    workspace();await load();
  }catch(err){$("#auth-message").textContent=err.message}
});
$("#logout").addEventListener("click",async()=>{
  try{await api("/logout","POST",{})}catch{}
  S.role=null;S.csrf="";S.products=[];S.orders=[];S.inbox=[];
  S.seen=new Set();S.inboxPrimed=false;
  $("#workspace").hidden=true;$("#login-screen").hidden=false;$("#logout").hidden=true;$("#who").textContent="미로그인";
});
$("#refresh").addEventListener("click",()=>load().catch(e=>toast(e.message)));
document.querySelectorAll(".nav-item").forEach(el=>el.addEventListener("click",()=>{
  S.section=el.dataset.target;render();
  document.getElementById(S.section).scrollIntoView({behavior:"smooth",block:"start"});
}));
(async()=>{try{
  const me=await api("/me");
  if(me.authenticated&&me.principal){
    S.role=me.principal.role;S.csrf=me.principal.csrf;
    workspace();await load();
  }
}catch(err){console.warn("Local lab unavailable",err)}})();
setInterval(()=>{if(S.role&&!document.hidden)load(true).catch(()=>{})},15000);
if("serviceWorker" in navigator && location.hostname==="127.0.0.1"){
  navigator.serviceWorker.register("/order-lab/sw.js",{scope:"/order-lab/"})
    .catch(()=>{/* Never block orders or auth for offline-shell caching. */});
}
