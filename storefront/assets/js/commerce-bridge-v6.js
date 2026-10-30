/* Garak V6 beta bridge. Local same-origin API; no real checkout. */
(async()=>{
 const esc=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));
 const send=(event)=>fetch('/api/public/events',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({event,path:location.pathname})}).catch(()=>{});
 try{
  let page=window.GARAK_TEST_PATH||location.pathname,productPage=page.match(/\/product\/([a-z0-9-]+)\.html$/),recipePage=/\/recipes\/recipe-/.test(page);
  send(productPage?'view_product':recipePage?'view_recipe':'page_view');
  const response=await fetch('/api/public/products',{cache:'no-store'});
  if(!response.ok)return;
  const data=await response.json(),map=new Map(data.items.map(p=>[p.slug,p]));
  if(Array.isArray(window.GARAK_PRODUCTS)){
   for(const p of window.GARAK_PRODUCTS){let live=map.get(p.slug);if(live){p.price=live.price;p.stock=live.stock;p.status=live.status;}else {p.stock=0;p.status='hidden';}}
  }
  document.dispatchEvent(new Event('garak:catalog-updated'));
  // Listed product cards now react to approved status and test inventory.
  for(const link of document.querySelectorAll('a[href*="product/"]')){
   const slug=(link.getAttribute('href')||'').match(/product\/([a-z0-9-]+)\.html/);if(!slug)continue;
   const live=map.get(slug[1]);
   if(!live){link.setAttribute('aria-disabled','true');link.style.opacity='.48';link.title='현재 관리자에서 비공개 처리한 상품입니다';link.querySelectorAll('[data-add]').forEach(b=>{b.disabled=true;b.textContent='비공개 상품'});continue;}
   const price=link.querySelector('.price');if(price)price.textContent=Number(live.price).toLocaleString('ko-KR')+'원';
   if(live.stock===0){link.style.opacity='.55';link.title='테스트 재고 소진';link.querySelectorAll('[data-add]').forEach(b=>{b.disabled=true;b.textContent='품절'});}
  }
  if(productPage){
    let live=map.get(productPage[1]);let detail=document.querySelector('.details-box');
    if(detail){let box=document.createElement('div');box.setAttribute('role','status');box.style.cssText='border:1px solid #b6d8da;border-radius:9px;background:#f4fafa;padding:12px;margin-top:12px;color:#164b5a;font-size:13px;line-height:1.7';
     box.textContent=live?`운영 DB 연동(베타): ${live.price.toLocaleString('ko-KR')}원 · 테스트 재고 ${live.stock}개 · 실제 판매 금액 및 실재고 아님`:'운영 DB에서 비공개된 상품입니다.';
     detail.append(box);
     if(live){const price=detail.querySelector('.price');if(price)price.textContent=Number(live.price).toLocaleString('ko-KR')+'원'}
     if(!live || live.stock===0){document.querySelectorAll('[data-add]').forEach(b=>{b.disabled=true;b.textContent='현재 시연 구매 불가'});}
    }
  }
  document.addEventListener('click',e=>{if(e.target.closest('[data-add]'))send('add_to_cart_demo')});
  if(page==='/' || page.endsWith('/index.html') && page.split('/').filter(Boolean).length===1){
   let [r,p]=await Promise.all([fetch('/api/public/recipes').then(x=>x.json()),fetch('/api/public/posts').then(x=>x.json())]);
   let insert=document.createElement('section');insert.className='section';insert.style.background='#eff6f5';
   insert.innerHTML=`<div class="container"><div class="section-head"><div><p class="kicker">ADMIN APPROVED · BETA</p><h2>운영자가 검수한 최신 콘텐츠</h2><p class="sub">승인 전 레시피·상인 광고는 게시하지 않습니다.</p></div><a class="more" href="admin/">운영센터</a></div><div class="story-shortcut-row" style="padding:15px 0;flex-wrap:wrap;justify-content:start;gap:15px">${r.items.slice(0,3).map(x=>`<a href="recipes/${esc(x.source_id)}.html">🍳 ${esc(x.title)}</a>`).join('')||'<span>현재 승인된 레시피가 없습니다.</span>'}${p.items.slice(0,2).map(x=>`<span>📣 ${esc(x.organization)} · ${esc(x.title)}${x.is_ad?' (광고)':''}</span>`).join('')||'<span>현재 승인된 홍보 게시물이 없습니다.</span>'}</div></div>`;
   document.querySelector('.story-shortcuts')?.after(insert);
  }
 }catch(e){/* Offline static preview remains readable with built-in sample data. */}
})();
