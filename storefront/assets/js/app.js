(() => {const key='garak-hansang-demo-cart';let fallback={};function read(){try{return JSON.parse(localStorage.getItem(key)||'{}')}catch{return fallback}}function write(data){fallback=data;try{localStorage.setItem(key,JSON.stringify(data))}catch{}count()}function count(){let n=Object.values(read()).reduce((a,x)=>a+Math.max(0,Number(x.qty)||0),0);document.querySelectorAll('[data-cart-count]').forEach(x=>x.textContent=n)}function toast(msg){let t=document.createElement('div');t.className='js-toast';t.textContent=msg;document.body.append(t);setTimeout(()=>t.remove(),2600)}function add(s,qty){let list=read();let d=window.GARAK_PRODUCTS?.find(x=>x.slug===s);if(!d){toast('상품 정보를 찾을 수 없습니다.');return}
 if(!Number.isSafeInteger(qty)||qty<1||qty>50){toast('담을 수량을 확인해 주세요.');return}
 if(d.status==='hidden'||d.status==='draft'){toast('현재 비공개된 상품입니다.');return}
 if(Number.isFinite(Number(d.stock))&&d.stock!==undefined&&d.stock!==null&&Number(d.stock)<((Number(list[s]?.qty)||0)+qty)){toast('시연 재고가 부족합니다.');return}
 list[s]={slug:s,qty:(Number(list[s]?.qty)||0)+qty};write(list);toast('장바구니에 담았습니다. (시연용)')}
document.addEventListener('click',(e)=>{let btn=e.target.closest('[data-add]');if(btn){e.preventDefault();let qty=Number(document.querySelector('#qty')?.value||'1');add(btn.dataset.add,qty)}let rm=e.target.closest('[data-remove]');if(rm){let list=read();delete list[rm.dataset.remove];write(list);renderCart()}let menu=e.target.closest('[data-menu]');if(menu){document.querySelector('.mobile-menu')?.classList.toggle('open')}});
function renderCart(){let root=document.querySelector('#cart-items');if(!root)return;let cart=read(),all=window.GARAK_PRODUCTS||[],total=0;root.replaceChildren();let found=false;Object.values(cart).forEach(({slug,qty})=>{let p=all.find(x=>x.slug===slug);if(!p)return;found=true;let unavailable=(p.status==='hidden'||p.status==='draft'||(p.stock!==undefined&&p.stock!==null&&Number(p.stock)<Number(qty)));
 if(!unavailable)total+=p.price*qty;let row=document.createElement('div');row.className='cart-line';let im=document.createElement('img');im.src=window.GARAK_ROOT+'assets/images/'+p.image+'.webp';im.alt='연출 이미지';let info=document.createElement('div');info.className='grow';let nm=document.createElement('strong');nm.textContent=p.name;let sub=document.createElement('div');sub.style.color='#60797c';sub.textContent=unavailable?'현재 비공개·품절 또는 재고 부족 · 구매 불가 (장바구니에서 삭제하세요)':qty+'개 · '+(p.price*qty).toLocaleString('ko-KR')+'원 (예시)';info.append(nm,sub);let btn=document.createElement('button');btn.className='btn ghost small';btn.textContent='삭제';btn.dataset.remove=slug;row.append(im,info,btn);root.append(row)});if(!found){let p=document.createElement('p');p.textContent='장바구니가 비어 있습니다. 상품을 둘러보세요.';root.append(p)}document.querySelectorAll('[data-subtotal]').forEach(x=>x.textContent=total.toLocaleString('ko-KR')+'원')}
function doSearch(){let form=document.querySelector('#search-form');if(!form)return;form.addEventListener('submit',e=>{e.preventDefault();let q=(form.querySelector('input').value||'').trim().toLowerCase();let list=(window.GARAK_PRODUCTS||[]).filter(x=>x.name.toLowerCase().includes(q)||x.merchant.toLowerCase().includes(q));let root=document.querySelector('#search-results');root.replaceChildren();for(let p of list){let a=document.createElement('a');a.className='product-card';a.href=window.GARAK_ROOT+'product/'+p.slug+'.html';let img=document.createElement('img');img.src=window.GARAK_ROOT+'assets/images/'+p.image+'.webp';img.alt='연출 이미지';let bd=document.createElement('div');bd.className='product-body';let title=document.createElement('h3');title.textContent=p.name;let pri=document.createElement('strong');pri.className='price';pri.textContent=p.price.toLocaleString('ko-KR')+'원';bd.append(title,pri);a.append(img,bd);root.append(a)};document.querySelector('#result-count').textContent='검색 결과: '+list.length+'개';if(!list.length)root.textContent='일치하는 상품이 없습니다.'})}
function noFakeSubmit(){document.querySelectorAll('[data-demo-form]').forEach(form=>form.addEventListener('submit',e=>{e.preventDefault();toast('시연용 화면입니다. 개인정보는 전송·저장되지 않습니다. 실제 접수는 서버/인증 연결 후 활성화합니다.')}))}
document.addEventListener('garak:catalog-updated',()=>{count();renderCart()});window.addEventListener('DOMContentLoaded',()=>{count();renderCart();doSearch();noFakeSubmit();});})();

if('serviceWorker'in navigator && (location.protocol==='https:'||location.hostname==='localhost'))navigator.serviceWorker.register(window.GARAK_ROOT+'service-worker.js').catch(()=>{});
(function injectLogin(){
  const actions=document.querySelector('.header-actions');
  if(!actions||document.querySelector('[data-garak-login]'))return;
  const a=document.createElement('a');
  a.className='icon-btn';
  a.dataset.garakLogin='1';
  a.href=(window.GARAK_ROOT||'')+'login.html';
  a.textContent='로그인';
  const cart=actions.querySelector('[href*="cart"]');
  actions.insertBefore(a, cart||actions.firstChild);
  const s=document.createElement('script');
  s.type='module';
  s.src=(window.GARAK_ROOT||'')+'auth/chip.mjs';
  document.head.append(s);
})();
(function injectBrand(){
  const s=document.createElement('script');
  s.type='module';
  s.src=(window.GARAK_ROOT||'')+'assets/js/brand.mjs';
  document.head.append(s);
})();
(function injectMap(){
  const href=(window.GARAK_ROOT||'')+'map.html';
  function add(root, label){
    if(!root||root.querySelector('[data-garak-map]'))return;
    const a=document.createElement('a');
    a.dataset.garakMap='1';
    a.href=href;
    a.textContent=label;
    root.append(a);
  }
  add(document.querySelector('.nav'), '시장 지도');
  add(document.querySelector('.story-nav-ribbon-inner'), '가락시장 지도');
  add(document.querySelector('.mobile-menu'), '시장 지도');
})();

