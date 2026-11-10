const money=n=>'₩'+n.toLocaleString('ko-KR');
const model={menu:[],cart:[],category:'all',order:null,busy:false};
const $=id=>document.getElementById(id);
async function api(url,method='GET',data,headers={}){let r=await fetch(url,{method,headers:{...(data?{'Content-Type':'application/json'}:{}),...headers},body:data?JSON.stringify(data):undefined});let j=await r.json();if(!r.ok)throw Error(j.error||'연결 오류');return j;}
function node(tag,cls,text){let e=document.createElement(tag);if(cls)e.className=cls;if(text!==undefined)e.textContent=text;return e;}
function makeButton(label,fn,cls=''){let b=node('button',cls,label);b.type='button';b.addEventListener('click',fn);return b;}
function add(p){let existing=model.cart.find(x=>x.id===p.id&&x.option===(p.category==='bakery'?'기본':'ICED'));if(existing) existing.qty++;else model.cart.push({id:p.id,qty:1,option:p.category==='bakery'?'기본':'ICED'});renderCart();}
function renderMenu(){const e=$('menu');e.replaceChildren();for(let p of model.menu.filter(p=>model.category==='all'||p.category===model.category)){
 let card=node('article','menu-card');let pic=node('div','menu-icon',p.emoji),txt=node('div','menu-card-copy');txt.append(node('div','menu-name',p.name),node('div','menu-en',p.en),node('p','menu-desc',p.description),node('strong','price',money(p.price)));let addBtn=makeButton('+ 담기',()=>add(p),'add-btn');card.append(pic,txt,addBtn);e.append(card);
}}
function renderCart(){let c=$('cart-items');c.replaceChildren();let quantity=0,total=0;if(model.cart.length===0){let em=node('div','empty-cart');em.append(node('div','', '🧺'),node('strong','', '아직 담은 메뉴가 없어요'),node('p','','왼쪽에서 원하는 메뉴를 선택하세요.'));c.append(em);}for(let [i,item] of model.cart.entries()){
 let p=model.menu.find(p=>p.id===item.id);if(!p)continue;quantity+=item.qty;total+=p.price*item.qty;let row=node('div','cart-row'),title=node('div','cart-row-title');title.append(node('strong','',p.name),node('small','',item.option+' · '+money(p.price)));let controls=node('div','qty');controls.append(makeButton('−',()=>modify(i,-1)),node('span','',String(item.qty)),makeButton('+',()=>modify(i,1)));if(p.category!=='bakery'){
 let temp=node('div','cart-options');for(const tempValue of ['HOT','ICED']){
   let b=makeButton(tempValue,()=>{model.cart[i].option=tempValue;renderCart()},item.option===tempValue?'on':'');
   temp.append(b);
 } title.append(temp);
}
row.append(node('div','cart-emoji',p.emoji),title,controls);c.append(row);
} $('item-count').textContent=quantity;$('total').textContent=money(total);$('checkout').disabled=!quantity||model.busy;}
function modify(i,d){model.cart[i].qty+=d;if(model.cart[i].qty<=0)model.cart.splice(i,1);if(model.cart[i]?.qty>20)model.cart[i].qty=20;renderCart();}
function closeDialog(id){let el=$(id);if(el.open)el.close();}
async function cancelOpenOrder(){
 if(model.order?.status==='awaiting_payment'){
   try{await api('/api/orders/cancel','POST',{order_id:model.order.id,payment_key:model.order.payment_key});}
   catch(e){console.warn('미결제 주문 취소 확인 필요',e.message);}
 }
 model.order=null;
}
async function openCheckout(){if(model.busy||!model.cart.length)return;model.busy=true;renderCart();try{let key=crypto.randomUUID().replaceAll('-','')+crypto.randomUUID().slice(0,8);let j=await api('/api/checkout','POST',{items:model.cart},{'Idempotency-Key':key});model.order=j.order;
 $('payment-items').replaceChildren(...j.order.items.map(i=>node('div','payment-line',`${i.name} · ${i.option} × ${i.qty}   ${money(i.unit_price*i.qty)}`)));$('payment-total').textContent=money(j.order.amount);$('payment-dialog').showModal();}catch(e){alert('주문 접수 실패: '+e.message);}finally{model.busy=false;renderCart();}}
async function approveDemo(){if(!model.order)return;let b=$('demo-pay');b.disabled=true;b.textContent='승인 처리 중…';try{let j=await api('/api/demo/approve','POST',{order_id:model.order.id});model.order=j.order;closeDialog('payment-dialog');$('queue-num').textContent=String(j.order.queue_number).padStart(3,'0');$('done-order-id').textContent='주문번호 '+j.order.id.slice(0,8).toUpperCase();$('done-dialog').showModal();model.cart=[];renderCart();}catch(e){alert('승인 실패: '+e.message);}finally{b.disabled=false;b.textContent='테스트 카드 결제 승인';}}
async function newOrder(){await cancelOpenOrder();closeDialog('payment-dialog');closeDialog('done-dialog');model.cart=[];renderCart();window.scrollTo({top:0,behavior:'smooth'});}
(async()=>{try{model.menu=(await api('/api/menu')).items;renderMenu();}catch(e){$('menu').textContent='메뉴 서버 연결 실패: '+e.message;}renderCart();})();
$('filters').querySelectorAll('button').forEach(b=>b.addEventListener('click',()=>{model.category=b.dataset.category;$('filters').querySelectorAll('button').forEach(x=>x.classList.toggle('active',x===b));renderMenu();}));
$('clear-cart').addEventListener('click',()=>{model.cart=[];renderCart();});$('start-over').addEventListener('click',newOrder);$('checkout').addEventListener('click',openCheckout);$('demo-pay').addEventListener('click',approveDemo);$('close-dialog').addEventListener('click',async()=>{await cancelOpenOrder();closeDialog('payment-dialog');});$('new-order').addEventListener('click',newOrder);$('print-receipt').addEventListener('click',()=>{if(model.order){window.open('/receipt?id='+encodeURIComponent(model.order.id),'_blank','noopener');}});

$('payment-dialog').addEventListener('cancel',()=>{void cancelOpenOrder();});
