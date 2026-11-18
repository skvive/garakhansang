/* Dynamic public releases only. Never displays unverified product drafts. */
(()=>{
 "use strict";
 const root=document.getElementById("garak-verified-shelf");
 if(!root)return;
 const ENDPOINT="/api/mobile/v1/catalog";
 let items=[],revision="",filter="",busy=false,dialog=null,connection="loading",lastChecked="";
 const el=(tag,cls,text)=>{
   const node=document.createElement(tag);
   if(cls)node.className=cls;
   if(text!==undefined)node.textContent=text;
   return node;
 };
 const shell=el("div","gv-shell"),head=el("div","gv-head"),lead=el("div"),filters=el("div","gv-filters"),
       grid=el("div","gv-grid"),note=el("p","gv-note","승인된 실제 상품 정보만 표시합니다. 실주문·배달은 판매자별 결제 및 배송 검증 후 제공됩니다.");
 root.append(shell);
 const status=el("p","gv-status","승인 상품 데이터 연결 확인 중…");
 status.setAttribute("role","status");status.setAttribute("aria-live","polite");
 shell.append(head,status,filters,grid,note);
 root.hidden=false;root.setAttribute("aria-busy","true");
 lead.append(el("span","gv-overline","GARAKHANSANG · VERIFIED MARKET"),el("h2","","가락시장의 검증된 먹거리"),el("p","gv-desc","판매자 승인 절차를 통과한 상품만 보여드립니다. 웹과 앱이 같은 서버의 상품 정보를 사용합니다."));
 head.append(lead);
 const refresh=el("button","gv-refresh","새로고침");
 refresh.type="button";refresh.addEventListener("click",()=>update());
 head.append(refresh);
 const makeDialog=()=>{
   if(dialog)return dialog;
   dialog=document.createElement("dialog");dialog.id="garak-verified-dialog";document.body.append(dialog);
   dialog.addEventListener("click",e=>{if(e.target===dialog)dialog.close()});
   return dialog;
 };
 const money=price=>new Intl.NumberFormat("ko-KR").format(price)+"원";
 function openDetail(p){
   const d=makeDialog(),inner=el("div","gv-dialog-inner");d.replaceChildren(inner);
   const u=new URL(p.image_url,location.href);
   if(u.protocol==="https:"){
     const img=el("img");img.src=u.href;img.alt=p.name;img.loading="lazy";inner.append(img);
   }
   inner.append(el("span","gv-overline","공식 검증 상품"),el("h3","",p.name),el("p","gv-merchant",p.merchant_name),
                el("p","gv-price",money(p.price_krw)),el("p","",p.description||"판매자에게 상품 구성을 확인해 주세요."),
                el("p","gv-note","수량 및 최종 가격은 결제 직전 서버에서 재검증합니다. 현재 앱 내 실주문은 비활성 상태입니다."));
   const close=el("button","gv-close","닫기");close.type="button";close.addEventListener("click",()=>d.close());inner.append(close);
   if(typeof d.showModal==="function")d.showModal();
 };
 function paint(){
   root.hidden=false;root.dataset.state=connection;
   if(connection==="error")status.textContent="상품 정보를 확인할 수 없습니다. 연결 상태를 확인한 뒤 다시 시도해 주세요.";
   else if(connection==="loading")status.textContent="승인된 상품 데이터를 조회하는 중입니다.";
   else status.textContent=items.length?
     "승인 상품 "+items.length+"개 확인 · 마지막 조회 "+lastChecked:
     "현재 공개된 승인 상품이 없습니다 · 마지막 조회 "+lastChecked;
   if(connection!=="ready"||!items.length){
     filters.replaceChildren();
     grid.replaceChildren(el("div","gv-empty",connection==="error"?
       "서버 연결 실패로 상품 목록을 표시하지 않습니다. 시연 상품을 대신 보여주지 않습니다.":
       connection==="loading"?"안전하게 승인 상품만 확인하고 있습니다.":
       "입점 심사와 상품 검증이 완료되면 이곳에 자동으로 표시됩니다."));
     return;
   }
   const names=[...new Set(items.map(p=>p.merchant_name))];
   filters.replaceChildren();
   for(const name of ["전체 매장",...names]){
     const key=name==="전체 매장"?"":name,b=el("button","gv-filter",name);
     b.type="button";b.setAttribute("aria-pressed",String(key===filter));
     b.addEventListener("click",()=>{filter=key;paint()});
     filters.append(b);
   }
   grid.replaceChildren();
   for(const p of items.filter(p=>!filter||p.merchant_name===filter)){
     const card=el("article","gv-card"),img=el("img","gv-image");
     img.src=p.image_url;img.alt=p.name;img.loading="lazy";img.decoding="async";
     img.addEventListener("error",()=>{
       const fallback=el("div","gv-image-missing","상품 사진 확인 중");
       fallback.setAttribute("role","img");fallback.setAttribute("aria-label",p.name+" 상품 이미지 확인 중");
       img.replaceWith(fallback);
     },{once:true});
     const info=el("div","gv-info"),detail=el("button","gv-detail","상품 상세 보기");
     detail.type="button";detail.addEventListener("click",()=>openDetail(p));
     info.append(el("span","gv-merchant",p.merchant_name),el("span","gv-name",p.name),
                 el("span","gv-price",money(p.price_krw)),detail);
     card.append(img,info);grid.append(card);
   }
 }
 async function update(){
   if(busy||document.visibilityState==="hidden")return;
   busy=true;refresh.disabled=true;root.setAttribute("aria-busy","true");
   try{
     const requestHeaders={"Accept":"application/json"};
     if(revision.startsWith('"'))requestHeaders["If-None-Match"]=revision;
     const r=await fetch(ENDPOINT,{cache:"no-store",credentials:"omit",headers:requestHeaders});
     if(r.status===304){
       connection="ready";lastChecked=new Date().toLocaleTimeString("ko-KR",{hour:"2-digit",minute:"2-digit"});
       paint();return;
     }
     if(!r.ok)throw Error("catalog unavailable");
     const body=await r.json();
     if(body.schema_version!==1||body.source!=="verified_neon_release_ready"||
        body.order_service_ready!==false||body.delivery_tracking_ready!==false||
        !Array.isArray(body.items))throw Error("catalog contract");
     const next=body.items.filter(p=>p&&typeof p.sku==="string"&&
             typeof p.name==="string"&&typeof p.merchant_name==="string"&&
             typeof p.price_krw==="number"&&Number.isInteger(p.price_krw)&&p.price_krw>0&&
             Number.isInteger(p.stock)&&p.stock>0&&
             typeof p.image_url==="string"&&p.image_url.startsWith("https://")&&
             p.merchant_verified===true);
     const signature=r.headers.get("ETag")||JSON.stringify(next.map(p=>[p.sku,p.price_krw,p.stock]));
     if(signature!==revision){
       items=next;revision=signature;
       if(filter&&!items.some(p=>p.merchant_name===filter))filter="";
     }
     connection="ready";lastChecked=new Date().toLocaleTimeString("ko-KR",{hour:"2-digit",minute:"2-digit"});
     paint();
   }catch(_error){
     // Fail closed: no cached or demo products may masquerade as approved inventory.
     items=[];revision="";connection="error";lastChecked="";filter="";paint();
   }finally{busy=false;refresh.disabled=false;root.setAttribute("aria-busy","false")}
 }
 update();
 document.addEventListener("visibilitychange",()=>{if(!document.hidden)update()});
 window.addEventListener("focus",update);
 setInterval(update,30000);
})();
