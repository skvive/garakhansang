(() => {
'use strict';
const state = {menus: [], options: [], category: '전체', query: '', selected: new Set()};
const $ = (s, root = document) => root.querySelector(s);
const money = n => new Intl.NumberFormat('ko-KR').format(Number(n || 0)) + '원';
const escapeHTML = v => String(v == null ? '' : v).replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const src = menu => String(menu.representativeImage || 'assets/editorial/seafood.webp');
const byId = id => state.menus.find(m => m.id === id);
const relevant = () => state.menus.filter(m =>
  (state.category === '전체' || m.category === state.category) &&
  [m.name, m.category, m.description].join(' ').toLowerCase().includes(state.query.toLowerCase())
);
function filters() {
  const categories = ['전체','인기','1인 회','프리미엄 회','겨울 방어','제철 회','여름 제철','갑각류','계절 해산물','추가 메뉴'];
  $('#iw-filters').innerHTML = categories.map(c =>
    '<button type="button" class="iw-filter '+(state.category===c?'is-active':'')+'" data-category="'+escapeHTML(c)+'" aria-pressed="'+(state.category===c?'true':'false')+'">'+escapeHTML(c)+'</button>'
  ).join('');
}
function picks(){
  const rows=[...state.selected].map(byId).filter(Boolean);
  $('#iw-picks').innerHTML = rows.length ? rows.map(m =>
    '<div class="iw-pick-row"><span>'+escapeHTML(m.name)+'</span><strong>'+money(m.price)+'</strong><button type="button" data-remove="'+escapeHTML(m.id)+'" aria-label="'+escapeHTML(m.name)+' 선택 해제">×</button></div>'
  ).join('')+'<div class="iw-pick-total"><b>참고가 합계</b><strong>'+money(rows.reduce((sum,m)=>sum+m.price,0))+'</strong></div>'
  : '<p class="iw-muted">선택한 메뉴가 없습니다.</p>';
  $('#iw-copy').disabled = rows.length === 0;
}
function row(m) {
  const chosen=state.selected.has(m.id);
  const image=src(m);
  return '<article class="iw-menu-item" data-menu-row="'+escapeHTML(m.id)+'">' +
    '<div class="iw-menu-thumb"><img src="'+escapeHTML(image)+'" alt="유사 수산 대표 이미지" loading="lazy" onerror="this.onerror=null;this.src=\'assets/editorial/seafood.webp\'"></div>' +
    '<div class="iw-menu-details"><small>'+escapeHTML(m.category)+(m.flag==='seasonal'?' · 시즌 메뉴':'')+'</small><h3>'+escapeHTML(m.name)+'</h3><p>'+escapeHTML(m.description)+'</p></div>' +
    '<div class="iw-menu-price"><strong>'+money(m.price)+'</strong><small>캡처 참고가</small><button type="button" class="iw-mini-btn" data-select="'+escapeHTML(m.id)+'" aria-pressed="'+String(chosen)+'">'+(chosen?'선택됨 ✓':'문의 목록 +')+'</button></div>' +
  '</article>';
}
function render(){
  filters();
  const filtered=relevant();
  $('#iw-menu-list').innerHTML=filtered.map(row).join('');
  $('#iw-empty').hidden=filtered.length>0;
  $('#menu-result-count').textContent=filtered.length+'가지 메뉴';
  picks();
}
function featured() {
  const featuredIds=['premium-mix','solo-mix','yellowtail-large'];
  const menus=featuredIds.map(byId).filter(Boolean);
  $('#featured-menus').innerHTML=menus.map(m=>
    '<article class="iw-feature-card"><div class="iw-feature-image"><img src="'+escapeHTML(src(m))+'" alt="대표 수산 메뉴 분위기 이미지. 일월수산 실상품 사진 아님" loading="lazy"><span class="iw-img-tag">대표 수산 이미지 · 예시</span></div>'+
    '<div class="iw-feature-body"><small>'+escapeHTML(m.category)+' · 참고 메뉴</small><h3>'+escapeHTML(m.name)+'</h3><div class="iw-feature-line"><strong>'+money(m.price)+'</strong><a class="iw-mini-btn" href="#menus" data-focus-menu="'+escapeHTML(m.id)+'">메뉴 찾기 ↗</a></div></div></article>'
  ).join('');
}
function renderOptions(){
  const rows=state.options || [];
  $('#iw-option-list').innerHTML=rows.map(o=>
    '<div class="iw-option-row"><span>'+escapeHTML(o.name)+' <small>('+escapeHTML(o.group)+')</small></span><strong>+'+money(o.additionalPrice)+'</strong></div>'
  ).join('') || '<p>표시할 옵션이 없습니다.</p>';
}
function copyFallback(text){
  const area=document.createElement('textarea');
  area.value=text; area.style.position='fixed'; area.style.opacity='0';area.style.left='0';area.style.top='0';
  document.body.append(area);area.select();
  let ok=false;try{ok=document.execCommand('copy')}catch{}
  area.remove();return ok;
}
async function copySelected(){
 const menus=[...state.selected].map(byId).filter(Boolean);
 if(!menus.length) return;
 const text=['[일월수산 메뉴 문의 목록]','가락몰 판매동 1층 수산 C-15호',...menus.map((m,i)=>(i+1)+'. '+m.name+' — '+money(m.price)), '합계 참고가: '+money(menus.reduce((a,m)=>a+m.price,0)), '※ 이미지 확인 당시 가격입니다. 실제 판매/주문/예약/결제 아님. 매장에 가격과 가능 여부를 확인해 주세요.'].join('\n');
 let ok=false;
 try{if(navigator.clipboard&&window.isSecureContext){await navigator.clipboard.writeText(text);ok=true;} else ok=copyFallback(text);}
 catch{ok=copyFallback(text)}
 $('#iw-copy-status').textContent=ok?'문의용 목록을 복사했습니다. 실제 주문이 접수된 것은 아닙니다.':'복사가 제한되었습니다. 보안 설정을 확인해 주세요.';
}
document.addEventListener('click', ev=>{
 const button=ev.target.closest('button');
 const a=ev.target.closest('[data-focus-menu]');
 if(a){const m=byId(a.dataset.focusMenu);if(m){state.category='전체';state.query=m.name;$('#iw-search').value=m.name;render();}}
 if(!button)return;
 if(button.dataset.category){state.category=button.dataset.category;render();}
 if(button.dataset.select){const id=button.dataset.select;state.selected.has(id)?state.selected.delete(id):state.selected.add(id);render();}
 if(button.dataset.remove){state.selected.delete(button.dataset.remove);render();}
});
$('#iw-search').addEventListener('input',ev=>{state.query=ev.target.value.trim();render();});
$('#iw-reset').addEventListener('click',()=>{state.query='';state.category='전체';$('#iw-search').value='';render();$('#iw-search').focus();});
$('#iw-copy').addEventListener('click',copySelected);
fetch('merchant/ilwol-susan.json',{cache:'no-cache'})
 .then(r=>{if(!r.ok)throw Error('HTTP '+r.status);return r.json()})
 .then(d=>{
   if(!Array.isArray(d.menus)||d.menus.length===0)throw Error('메뉴 데이터 없음');
   state.menus=d.menus;state.options=d.options||[];
   $('#menu-total').textContent=d.menus.length+'개 참고 메뉴';
   featured();render();renderOptions();
 })
 .catch(err=>{
   console.error('일월수산 메뉴 데이터',err);
   $('#iw-menu-list').innerHTML='<p class="iw-empty" role="alert">메뉴를 불러오지 못했습니다. 새로고침 후 다시 확인하거나 매장에 문의해 주세요.</p>';
   $('#featured-menus').innerHTML='<p class="iw-loading">대표 메뉴 데이터를 확인할 수 없습니다.</p>';
   $('#iw-option-list').textContent='옵션을 불러오지 못했습니다.';
 });
})();
