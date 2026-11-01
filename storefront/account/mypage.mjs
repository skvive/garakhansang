import {getAuthClient, getSession, signOut} from '../auth/client.mjs';

const $=(s)=>document.querySelector(s);
const panel=$('#view-panel');
const cartKey='garak-hansang-demo-cart';
const couponKey='garak-brand-wallet';
const validViews=new Set(['overview','cart','orders','shipping','coupons','profile']);
let signedInUser=null;

function safeString(s){return String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));}
function localValue(key,empty){try{const value=JSON.parse(localStorage.getItem(key)||'null');return value??empty;}catch{return empty;}}
function currency(value){return Number(value||0).toLocaleString('ko-KR')+'원';}
function cartItems(){
 const raw=localValue(cartKey,{});
 if(!raw || typeof raw!=='object' || Array.isArray(raw))return [];
 return Object.values(raw).filter(x=>x && typeof x.slug==='string'&&/^[a-z0-9-]{1,120}$/i.test(x.slug)&&Number.isInteger(Number(x.qty))&&Number(x.qty)>0&&Number(x.qty)<101).map(x=>({slug:x.slug,qty:Number(x.qty)}));
}
function coupons(){
 const a=localValue(couponKey,[]);
 return Array.isArray(a)?a.filter(x=>typeof x==='string'&&/^c-[a-z0-9-]{1,70}$/i.test(x)).slice(0,80):[];
}
function catalog(){return Array.isArray(window.GARAK_PRODUCTS)?window.GARAK_PRODUCTS:[];}
function cartStats(){return cartItems().reduce((n,i)=>n+i.qty,0);}
function section(title,description){return '<div class="section-title"><div><h2>'+title+'</h2><p>'+description+'</p></div></div>';}
function empty(title,description,buttonText='',url=''){
 return '<div class="empty"><strong>'+title+'</strong><p>'+description+'</p>'+
 (url?'<a class="button pale" href="'+url+'">'+buttonText+'</a>':'')+'</div>';
}
function renderOverview(){
 panel.innerHTML=section('나의 쇼핑 현황','회원 계정과 이 브라우저의 시연 장바구니를 분리해 표시합니다.')+
 '<div class="stats"><div class="stat"><b>'+cartStats()+'</b><small>이 기기 장바구니 상품 수</small></div>'+
 '<div class="stat"><b>0</b><small>확인된 실제 주문</small></div><div class="stat"><b>0</b><small>확인된 실제 배송</small></div>'+
 '<div class="stat"><b>0</b><small>발급 확인된 실제 쿠폰</small></div></div>'+
 '<div class="tiles"><a class="tile" href="#cart">🛒 내 장바구니 <span>↗</span></a>'+
 '<a class="tile" href="#orders">▤ 주문내역 조회 <span>↗</span></a>'+
 '<a class="tile" href="#shipping">📦 배송 상태 <span>↗</span></a>'+
 '<a class="tile" href="#coupons">🎟️ 쿠폰함 <span>↗</span></a>'+
 '<a class="tile" href="#profile">♙ 기본정보 관리 <span>↗</span></a>'+
 '<a class="tile" href="stores.html">🏪 매장 둘러보기 <span>↗</span></a></div>'+
 '<div class="notice">현재 장바구니와 체험 쿠폰은 브라우저의 시연 정보이며, Neon 계정에 서버 동기화된 데이터가 아닙니다. 주문·배송은 실제 고객 연결이 검증되기 전까지 다른 회원의 자료를 조회하지 않습니다.</div>';
}
function renderCart(){
 const rows=cartItems(),index=new Map(catalog().map(x=>[x.slug,x])),known=rows.map(x=>({...x,product:index.get(x.slug)}));
 const total=known.reduce((v,x)=>v+(x.product&&Number.isFinite(Number(x.product.price))?Number(x.product.price)*x.qty:0),0);
 panel.innerHTML=section('내 장바구니','현재 기기에만 저장된 시연 상품입니다. 구매·재고 차감은 지원하지 않습니다.')+
 (known.length?known.map(x=>{
 const p=x.product;
 const title=p?safeString(p.name):safeString(x.slug);
 const photo=p&&/^[a-z0-9-]+$/i.test(p.image||'')?'assets/images/'+p.image+'.webp':'assets/editorial/seafood.webp';
 return '<div class="line"><img src="'+photo+'" alt="상품 참고 이미지" loading="lazy"><div class="info"><b>'+title+'</b><p>'+x.qty+'개 · '+(p?currency(x.qty*Number(p.price))+' (예시 가격)':'상품 정보 확인 필요')+'</p></div><button type="button" data-remove-cart="'+safeString(x.slug)+'">삭제</button></div>';
 }).join('')+'<p class="total">상품가 합계(예시) '+currency(total)+'</p>':
 empty('장바구니가 비어 있습니다.','상품을 둘러보고 마음에 드는 상품을 담아보세요.','매장 보기','stores.html'))+
 '<div class="notice">이 목록은 이 기기에 저장된 쇼핑 시연 정보입니다. 계정별 서버 장바구니나 실제 결제 가능 상태를 뜻하지 않습니다.</div>';
 panel.querySelectorAll('[data-remove-cart]').forEach(btn=>btn.addEventListener('click',()=>{
   const slug=btn.getAttribute('data-remove-cart'),raw=localValue(cartKey,{});
   if(raw && typeof raw==='object'&&!Array.isArray(raw)){delete raw[slug];try{localStorage.setItem(cartKey,JSON.stringify(raw));}catch{}}
   renderCart();
 }));
}
function renderOrders(){
 panel.innerHTML=section('주문 조회','내 계정에 연결된 주문만 안전하게 표시합니다.')+
 empty('조회 가능한 실제 주문이 없습니다.','현재는 인증 사용자 ID와 연결된 주문 조회 기능이 활성화되지 않았습니다. 기존 관리자 시연 주문은 개인정보 보호를 위해 노출하지 않습니다.')+
 '<div class="notice">향후 주문·결제 시스템을 검증해 연결하면 주문일, 주문번호, 상품·결제내역을 이곳에 표시할 수 있습니다.</div>';
}
function renderShipping(){
 panel.innerHTML=section('배송 조회','주문에 연결된 운송장과 택배사 정보가 확인된 경우에만 배송을 표시합니다.')+
 empty('조회 가능한 배송 정보가 없습니다.','실제 주문·운송장 API가 연결되지 않아 가상의 배송 상태나 운송장번호를 표시하지 않습니다.')+
 '<div class="notice">배송 준비 → 발송 → 배송 중 → 배송 완료 단계는 실제 택배사 이벤트가 연결된 후 활성화됩니다.</div>';
}
function renderCoupons(){
 const items=coupons();
 panel.innerHTML=section('내 쿠폰함','실제 발급 쿠폰과 시연 쿠폰을 명확하게 구분합니다.')+
 '<div class="stats" style="grid-template-columns:repeat(2,minmax(0,1fr))"><div class="stat"><b>0</b><small>계정 발급 검증된 쿠폰</small></div><div class="stat"><b>'+items.length+'</b><small>이 기기의 체험 쿠폰</small></div></div>'+
 (items.length?items.map(x=>'<div class="line"><span aria-hidden="true" style="font-size:25px">🎟️</span><div class="info"><b>'+safeString(x.replace(/^c-/,''))+' 체험 쿠폰</b><p>개발용 시연 · 결제 할인에 적용되지 않습니다.</p></div></div>').join(''):
 empty('발급된 쿠폰이 없습니다.','실제 사용 가능한 쿠폰은 발급·유효기간·사용 조건이 검증된 후 표시됩니다.'))+
 '<div class="notice">체험 쿠폰은 브라우저에만 남아 있으며, 계정 간 공유되거나 다른 기기에서 복원되는 쿠폰이 아닙니다.</div>'+
 '<a class="button pale" href="coupons.html">쿠폰 안내 페이지 ↗</a>';
}
function renderProfile(){
 panel.innerHTML=section('내 기본정보','Neon Auth에 저장된 회원 표시 이름을 변경할 수 있습니다.')+
 '<form id="profile-form" class="profile-form"><label for="profile-name">표시 이름</label>'+
 '<input id="profile-name" name="name" maxlength="50" required autocomplete="name">'+
 '<label for="profile-email">로그인 이메일</label>'+
 '<input id="profile-email" type="email" readonly autocomplete="email">'+
 '<p class="small">이메일 주소는 로그인 계정의 정보이며 여기서는 임의로 변경하지 않습니다. 연락처·주소는 안전한 계정별 서버 저장 기능이 준비되면 제공됩니다.</p>'+
 '<button class="button primary" type="submit">이름 변경 저장</button>'+
 '<p id="account-message" role="status"></p></form>'+
 '<div class="notice">회원 정보는 Neon Auth에서 확인됩니다. 주소·전화번호와 같은 추가 개인정보는 브라우저에 임시 저장하지 않습니다.</div>';
 $('#profile-name').value=signedInUser.name||'';
 $('#profile-email').value=signedInUser.email||'';
 $('#profile-form').addEventListener('submit',async event=>{
  event.preventDefault();
  const name=$('#profile-name').value.trim();
  const msg=$('#account-message'),button=event.target.querySelector('button[type=submit]');
  if(name.length<2 || name.length>50){msg.textContent='이름은 2~50자로 입력해 주세요.';return;}
  button.disabled=true;msg.textContent='Neon 계정 정보를 변경하는 중입니다…';
  try{
   const client=await getAuthClient(),result=await client.updateUser({name});
   if(result?.error)throw new Error(result.error.message||'저장 실패');
   const current=await getSession();
   if(!current?.user)throw new Error('저장 후 세션을 확인할 수 없습니다.');
   signedInUser=current.user;
   $('#display-name').textContent=(current.user.name||'회원')+'님, 반갑습니다.';
   msg.textContent='Neon 계정 표시 이름을 저장했습니다.';
  }catch(error){msg.textContent='저장에 실패했습니다. 로그인 상태를 확인하고 다시 시도해 주세요.';}
  finally{button.disabled=false;}
 });
}
const views={overview:renderOverview,cart:renderCart,orders:renderOrders,shipping:renderShipping,coupons:renderCoupons,profile:renderProfile};
function show(view){
 const name=validViews.has(view)?view:'overview';
 document.querySelectorAll('[data-view]').forEach(link=>{
  const active=link.dataset.view===name;link.classList.toggle('active',active);
  if(active)link.setAttribute('aria-current','page');else link.removeAttribute('aria-current');
 });
 views[name]();
}
window.addEventListener('hashchange',()=>{if(signedInUser)show(location.hash.slice(1));});
window.addEventListener('storage',(event)=>{if(signedInUser&&[cartKey,couponKey].includes(event.key))show(location.hash.slice(1));});
$('#logout').addEventListener('click',async()=>{
 try{await signOut();location.replace('login.html?next=mypage.html');}
 catch{alert('로그아웃할 수 없습니다. 인터넷 연결을 확인해 주세요.');}
});
async function start(){
 try{
  const session=await getSession();
  $('#auth-loading').hidden=true;
  if(!session?.user?.id){$('#guest').hidden=false;return;}
  signedInUser=session.user;
  $('#account').hidden=false;$('#logout').hidden=false;
  $('#display-name').textContent=(session.user.name||'회원')+'님, 반갑습니다.';
  $('#email-address').textContent=session.user.email||'이메일 미확인';
  $('#avatar').textContent=(session.user.name||'손').slice(0,1);
  show(location.hash.slice(1));
 }catch(error){
  $('#auth-loading').hidden=true;
  $('#guest').hidden=false;
  $('#guest').querySelector('p').textContent='인증 서버 연결을 확인할 수 없습니다. 새로고침하거나 다시 로그인해 주세요.';
 }
}
start();
