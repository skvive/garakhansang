import { getAuthClient, getSession } from '../../auth/client.mjs';

const $=s=>document.querySelector(s);
const make=(tag,value,cls)=>{const e=document.createElement(tag);if(value!==undefined&&value!==null)e.textContent=String(value);if(cls)e.className=cls;return e;};
const labels={notice:'입점 안내',season:'제철 이야기',story:'상인 이야기',question:'질문'};
const login='/login.html?next='+encodeURIComponent(location.pathname.replace(/^\//,''));
let user=null,category='all';

async function token(){
  const auth=await getAuthClient();
  const r=await auth.getJWTToken();
  const t=typeof r==='string'?r:(r?.data?.token||r?.data?.access_token||r?.token);
  if(!t||typeof t!=='string'||t.split('.').length!==3)throw Error('로그인 토큰을 가져오지 못했습니다. 다시 로그인하세요.');
  return t;
}
async function api(path,{method='GET',body,member=false}={}){
 const headers={Accept:'application/json'};
 if(body!==undefined)headers['Content-Type']='application/json';
 if(member)headers.Authorization='Bearer '+await token();
 const r=await fetch(path,{method,headers,credentials:'same-origin',cache:'no-store',body:body===undefined?undefined:JSON.stringify(body)});
 const value=await r.json().catch(()=>({}));
 if(!r.ok)throw Error(value.error||'요청 실패 ('+r.status+')');
 return value;
}
function copyUpdate(){
 const small=$('.prep-sign small');if(small)small.textContent='매장 사진과 메뉴는 검토용 샘플입니다. 회원 입점 신청은 Neon DB에 접수되지만 정식 입점·계약을 의미하지 않습니다.';
 const foot=$('.footer-legal');if(foot)foot.textContent='현재 각 입점 업소는 입점을 준비 중이며, 본 페이지는 샘플 페이지입니다. 신규 접수는 운영자 검토 후 처리됩니다.';
 const help=$('.form-help');if(help)help.textContent='회원 로그인 후 신청서를 제출하면 운영자 검토 대기로 저장됩니다. 승인 여부는 내 신청 내역에서 확인하세요.';
 const side=$('.extra-info p');if(side)side.textContent='담당자 연락처는 운영자 검토에만 사용됩니다. 결제와 정식 입점은 별도 승인 절차가 필요합니다.';
 const p=$('.community-bottom .extra-form-panel > p');if(p)p.textContent='회원 로그인 후 글을 제출하면 운영자 승인 전까지 공개되지 않습니다.';
 const hero=$('.extra-hero p');if(hero&&$('#story-draft-form'))hero.textContent='상인 소식과 제철 이야기를 공유하는 회원 게시판입니다. 예시 콘텐츠와 회원 글을 구분해 표시합니다.';
 const submitApply=$('#merchant-apply-form [type="submit"]');if(submitApply)submitApply.textContent='입점 신청 접수하기';
 const submitPost=$('#story-draft-form [type="submit"]');if(submitPost)submitPost.textContent='게시글 접수하기';
}
function loginBanner(){
 const container=$('.extra-form-panel');if(!container)return;
 const box=make('div',null,'member-status');box.id='member-status';box.setAttribute('aria-live','polite');
 container.insertBefore(box,container.querySelector('form'));
 box.textContent=user?(user.name||user.email||'회원')+'님 로그인됨':'신청·글 작성에는 로그인이 필요합니다. ';
 if(!user){const a=make('a','로그인 / 회원가입 →');a.href=login;box.append(a);}
}
async function applications(){
 const form=$('#merchant-apply-form');if(!form||!user)return;
 let box=$('#application-history');if(!box){box=make('section',null,'application-history');box.id='application-history';form.after(box);}
 try{
  const r=await api('/api/merchant-applications',{member:true});box.replaceChildren(make('h3','내 신청 내역'));
  if(!r.items?.length)box.append(make('p','접수된 신청이 없습니다.'));
  for(const a of r.items||[])box.append(make('p','#'+a.id+' · '+a.shop_name+' · '+(a.status==='pending'?'검토 대기':a.status==='reviewed'?'검토 완료':'반려')));
 }catch(e){box.textContent='신청 내역 오류: '+e.message;}
}
function apply(){
 const form=$('#merchant-apply-form');if(!form)return;
 form.addEventListener('submit',async e=>{
  e.preventDefault();const msg=$('#apply-feedback');if(!form.reportValidity())return;
  if(!user){msg.textContent='로그인 후 신청할 수 있습니다.';return;}
  const fd=new FormData(form);const keys=['shopName','contactName','phone','email','category','location','description'];
  const data=Object.fromEntries(keys.map(k=>[k,String(fd.get(k)||'')]));data.consent=fd.has('consent');
  const button=form.querySelector('[type="submit"]');button.disabled=true;msg.textContent='접수 중…';
  try{const r=await api('/api/merchant-applications',{method:'POST',body:data,member:true});msg.textContent='접수번호 #'+r.id+' · 운영자 검토 대기';form.reset();await applications();}
  catch(err){msg.textContent='접수 실패: '+err.message+' (내용은 유지됩니다)';}finally{button.disabled=false;}
 });
}
function article(p,isMine=false){
 const node=make('article',null,'live-post');node.dataset.boardCat=p.category;
 node.append(make('span',(labels[p.category]||'커뮤니티')+' · '+(p.author_label||'회원')+' · '+(isMine&&p.status!=='approved'?'검토 대기':'회원 글'),'sample-tag'),make('h3',p.title),make('p',p.body));
 if(p.status==='approved'){
  const button=make('button','댓글 보기 / 작성','extra-submit'),holder=make('div',null,'live-comments');button.type='button';holder.hidden=true;
  button.addEventListener('click',async()=>{holder.hidden=!holder.hidden;if(!holder.hidden)await comments(p.id,holder);});
  node.append(button,holder);
 }
 return node;
}
async function comments(postId,root){
 root.replaceChildren(make('p','댓글을 불러오는 중…'));
 try{
  const r=await api('/api/community/comments?postId='+encodeURIComponent(postId));root.replaceChildren();
  for(const c of r.items||[]){const item=make('div',null,'live-comment');item.append(make('strong',c.author_label||'회원'),make('p',c.body));root.append(item);}
  if(!r.items?.length)root.append(make('p','아직 공개된 댓글이 없습니다.'));
  if(!user){const a=make('a','댓글 쓰기는 로그인 후 가능합니다 →');a.href=login;root.append(a);return;}
  const form=make('form',null,'live-comment-form'),input=make('textarea'),send=make('button','댓글 접수','extra-submit'),result=make('p',null,'apply-feedback');
  input.required=true;input.minLength=2;input.maxLength=800;input.placeholder='승인 후 공개됩니다';send.type='submit';result.setAttribute('role','status');
  form.append(input,send,result);root.append(form);
  form.addEventListener('submit',async e=>{e.preventDefault();if(!form.reportValidity())return;send.disabled=true;
   try{const r=await api('/api/community/comments',{method:'POST',body:{postId,content:input.value},member:true});result.textContent=r.message;input.value='';}
   catch(err){result.textContent='접수 실패: '+err.message;}finally{send.disabled=false;}
  });
 }catch(err){root.textContent='댓글 조회 오류: '+err.message;}
}
async function community(){
 const box=$('#live-community-list');if(!box)return;
 box.replaceChildren(make('p','게시글을 불러오는 중…'));
 try{
  const publicRows=(await api('/api/community/posts?category='+encodeURIComponent(category))).items||[];
  const privateRows=user?(await api('/api/community/posts?mine=1&category='+encodeURIComponent(category),{member:true})).items||[]:[];
  box.replaceChildren(make('h3','회원 게시글'));
  const ids=new Set();for(const p of [...privateRows,...publicRows]){if(ids.has(p.id))continue;ids.add(p.id);box.append(article(p,privateRows.some(x=>x.id===p.id)));}
  if(!ids.size)box.append(make('p','등록된 회원 글이 없습니다. 아래 샘플 콘텐츠를 참고하세요.'));
 }catch(err){box.replaceChildren(make('p','게시글 조회 오류: '+err.message));}
}
function post(){
 const form=$('#story-draft-form');if(!form)return;
 const list=make('section',null,'live-community');list.id='live-community-list';$('#community-board').before(list);
 const select=make('select');select.name='category';select.required=true;
 for(const [id,name]of Object.entries(labels)){const option=make('option',name);option.value=id;select.append(option);}
 const label=make('label','게시판 분류 ');label.append(select);form.prepend(label);
 form.addEventListener('submit',async e=>{e.preventDefault();const msg=$('#story-feedback');if(!form.reportValidity())return;
  if(!user){msg.textContent='로그인 후 게시할 수 있습니다.';return;}
  const data=new FormData(form),button=form.querySelector('[type="submit"]');button.disabled=true;msg.textContent='접수 중…';
  try{const r=await api('/api/community/posts',{method:'POST',body:{category:data.get('category'),title:data.get('title'),content:data.get('content')},member:true});msg.textContent='게시글 #'+r.id+' 접수 · 검토 대기';form.reset();await community();}
  catch(err){msg.textContent='접수 실패: '+err.message;}finally{button.disabled=false;}
 });
 const buttons=[...document.querySelectorAll('[data-board-filter]')],samples=[...document.querySelectorAll('#community-board [data-board-cat]')];
 buttons.forEach(b=>b.addEventListener('click',()=>{
  category=b.dataset.boardFilter||'all';
  for(const other of buttons){const active=other===b;other.classList.toggle('active',active);other.setAttribute('aria-pressed',String(active));}
  let count=0;for(const s of samples){const show=category==='all'||s.dataset.boardCat===category;s.hidden=!show;if(show)count++;}
  const empty=$('.community-empty');if(empty)empty.hidden=count>0;
  community();
 }));
}
copyUpdate();
try{const session=await getSession();user=session?.user||null;}catch(e){user=null;}
loginBanner();apply();post();await Promise.all([applications(),community()]);
