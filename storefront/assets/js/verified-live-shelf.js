/* Dynamic public releases only. Never displays unverified product drafts. */
(()=>{
 "use strict";
 const root=document.getElementById("garak-verified-shelf");
 if(!root)return;
 const ENDPOINT="/api/mobile/v1/catalog";
 let items=[],revision="",filter="",busy=false,dialog=null;
 const el=(tag,cls,text)=>{
   const node=document.createElement(tag);
   if(cls)node.className=cls;
   if(text!==undefined)node.textContent=text;
   return node;
 };
 const shell=el("div","gv-shell"),head=el("div","gv-head"),lead=el("div"),filters=el("div","gv-filters"),
       grid=el("div","gv-grid"),note=el("p","gv-note","승인된 실제 상품 정보만 표시합니다. 실주문·배달은 판매자별 결제 및 배송 검증 후 제공됩니다.");
 root.append(shell);
 shell.append(head,filters,grid,note);
 lead.append(el("span","gv-overline","GARAKHANSANG · VERIFIED STORES"),el("h2","","공식 입점 새상품"),el("p","gv-desc","홈페이지와 네이티브 앱에서 동일한 승인 상품을 확인하세요."));
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
   root.hidden=items.length===0;
   if(root.hidden)return;
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
     const info=el("div","gv-info"),detail=el("button","gv-detail","상품 상세 보기");
     detail.type="button";detail.addEventListener("click",()=>openDetail(p));
     info.append(el("span","gv-merchant",p.merchant_name),el("span","gv-name",p.name),
                 el("span","gv-price",money(p.price_krw)),detail);
     card.append(img,info);grid.append(card);
   }
 }
 async function update(){
   if(busy||document.visibilityState==="hidden")return;
   busy=true;refresh.disabled=true;
   try{
     const r=await fetch(ENDPOINT,{cache:"no-store",credentials:"omit",headers:{"Accept":"application/json"}});
     if(!r.ok)throw Error("catalog unavailable");
     const body=await r.json();
     if(body.schema_version!==1||!Array.isArray(body.items))throw Error("catalog format");
     const next=body.items.filter(p=>p&&typeof p.sku==="string"&&
             typeof p.price_krw==="number"&&Number.isInteger(p.price_krw)&&p.price_krw>0&&
             typeof p.image_url==="string"&&p.image_url.startsWith("https://")&&p.merchant_verified===true);
     const signature=r.headers.get("ETag")||JSON.stringify(next.map(p=>[p.sku,p.price_krw,p.stock]));
     if(signature!==revision){items=next;revision=signature;if(filter&&!items.some(p=>p.merchant_name===filter))filter="";paint();}
   }catch(_error){
     // Fail closed: do not render stale merchant availability as current.
     items=[];revision="";root.hidden=true;
   }finally{busy=false;refresh.disabled=false}
 }
 refresh.addEventListener("keydown",()=>{});
 update();
 document.addEventListener("visibilitychange",()=>{if(!document.hidden)update()});
 window.addEventListener("focus",update);
 setInterval(update,30000);
})();
