(()=>{'use strict';
const $=s=>document.querySelector(s), all=s=>[...document.querySelectorAll(s)];
const el=(tag,text,cls)=>{const n=document.createElement(tag);if(text!==undefined&&text!==null)n.textContent=String(text);if(cls)n.className=cls;return n;};
const formApply=$('#merchant-apply-form'), formPost=$('#story-draft-form');
let user=null, getSession=null, getAuthClient=null, filter='all';
const login='/login.html?next='+encodeURIComponent(location.pathname.slice(1));
const cats={notice:'입점 안내',season:'제철 이야기',story:'상인 이야기',question:'질문'};
function show(target,text){if(target)target.textContent=text;}
async function token(){
 if(!getSession)throw Error('회원 인증 서버를 사용할 수 없습니다.');
 const state=await getSession();
 let jwt=state?.session?.access_token;
 if((!jwt||jwt.split('.').length!==3) && getAuthClient){
   const auth=await getAuthClient();
   if(typeof auth.token==='function'){
     const r=await auth.token();
     jwt=typeof r==='string'?r:(r?.data?.token||r?.token);
   }
 }
 if(typeof jwt!=='string'||jwt.split('.').length!==3)throw Error('로그인이 만료되었습니다. 다시 로그인해 주세요.');
 return jwt;
}
async function request(url,options={}){
 const headers={'Accept':'application/json'};
 if(options.data!==undefined)headers['Content-Type']='application/json';
 if(options.member)headers.Authorization='Bearer '+await token();
 const r=await fetch(url,{method:options.data===undefined?'GET':'POST',credentials:'same-origin',
   headers,body:options.data===undefined?undefined:JSON.stringify(options.data),cache:'no-store'});
 const data=await r.json().catch(()=>({}));
 if(!r.ok)throw Error(data.error||'서버 오류 ('+r.status+')');
 return data;
}
function updateLabels(){
 const notice=$('.prep-sign small');
 if(notice)notice.textContent='사진 속 매장은 입점을 준비 중인 샘플 업체입니다. 신규 신청서는 회원 인증 후 별도 접수되며 실제 계약·입점 승인과 다릅니다.';
 const footer=$('.footer-legal');
 if(footer)footer.textContent='현재 각 입점 업소는 입점을 준비 중이며, 본 페이지는 샘플 페이지입니다. 입점 신청·게시글·댓글은 운영자 검토를 거칩니다.';
 const helper=$('.form-help');
 if(helper)helper.textContent='입점 신청서를 제출하면 Neon DB에 실제 저장되며 검토 대기 상태로 접수됩니다. 신청은 정식 계약이 아닙니다.';
 const aside=$('.extra-info p');
 if(aside)aside.textContent='연락처 등 신청 정보는 담당자 검토 및 회신에 사용됩니다. 개인정보 처리 안내를 확인한 후 제출하세요.';
 const p=$('.community-bottom .extra-form-panel > p');
 if(p)p.textContent='회원 게시글은 검토 대기로 저장되고 운영자 승인 후 공개됩니다.';
 const intro=$('.extra-hero p');
 if(intro&&formPost)intro.textContent='상인 소식과 제철 이야기를 공유합니다. 아래 예시 게시글은 샘플이며 실제 회원 작성글은 승인 후 표시됩니다.';
 if(formApply){
  const submit=formApply.querySelector('[type=submit]');if(submit)submit.textContent='입점 신청 접수하기';
  const consent=formApply.querySelector('label.consent span');
  if(consent)consent.textContent='입점 신청 검토·회신을 위한 담당자 이름, 전화, 이메일 및 매장 정보의 수집·이용에 동의합니다. 제출 후 운영자에게 삭제를 요청할 수 있습니다. *';
  const privacy=el('p',null,'form-help');
  const a=el('a','개인정보 처리방침 확인 →');a.href='../legal/privacy.html';privacy.append(a);
  formApply.querySelector('label.consent')?.before(privacy);
 }
 if(formPost){const submit=formPost.querySelector('[type=submit]');if(submit)submit.textContent='게시글 접수하기';}
}
function memberStatus(){
 const panel=$('.extra-form-panel');if(!panel)return;
 const status=el('div',null,'member-status');status.id='merchant-member-status';status.setAttribute('role','status');
 if(user){status.append(el('strong',(user.name||'회원')+'님 로그인됨'));}
 else{status.append(el('span','실제 접수·게시·댓글을 작성하려면 회원 로그인이 필요합니다. '));
  const link=el('a','로그인 / 회원가입 →');link.href=login;status.append(link);}
 panel.querySelector('form')?.before(status);
}
async function applications(){
 if(!formApply||!user)return;
 let box=$('#application-history');
 if(!box){box=el('section',null,'application-history');box.id='application-history';formApply.after(box);}
 try{
  const data=await request('/api/merchant-applications',{member:true});
  box.replaceChildren(el('h3','내 입점 신청 내역'));
  if(!data.items?.length)box.append(el('p','접수 내역이 없습니다.'));
  for(const app of data.items||[]){
   const s=app.status==='pending'?'검토 대기':app.status==='reviewed'?'검토 완료':'반려';
   box.append(el('p','#'+app.id+' · '+app.shop_name+' · '+s));
  }
 }catch(e){show(box,'신청 내역 조회 실패: '+e.message);}
}
function bindApply(){
 if(!formApply)return;
 formApply.addEventListener('submit',async e=>{
  e.preventDefault();const result=$('#apply-feedback');
  if(!formApply.reportValidity())return;
  if(!user){show(result,'회원 로그인 후 신청할 수 있습니다.');return;}
  const f=new FormData(formApply);
  const data=Object.fromEntries(['shopName','contactName','phone','email','category','location','description'].map(k=>[k,String(f.get(k)||'')]));
  data.consent=f.has('consent');
  const button=formApply.querySelector('[type=submit]');button.disabled=true;show(result,'신청서를 전송하는 중입니다…');
  try{const res=await request('/api/merchant-applications',{data,member:true});
    show(result,'입점 신청 #'+res.id+' 접수 완료 · 운영자 검토 대기');formApply.reset();await applications();}
  catch(err){show(result,'접수 실패: '+err.message+' (입력 내용은 그대로 유지됩니다.)');}
  finally{button.disabled=false;}
 });
}
function panel(post,mine){
 const article=el('article',null,'live-post');article.dataset.boardCat=post.category;
 const label=cats[post.category]||'회원 글';
 const st=post.status==='pending'?'검토 대기':post.status==='rejected'?'반려':'공개';
 article.append(el('span',label+' · '+(mine?st:'회원 게시글'),'sample-tag'),el('h3',post.title),el('p',post.body));
 if(post.status==='approved'){
  const toggle=el('button','댓글 보기 / 작성','extra-submit');toggle.type='button';
  const comments=el('div',null,'live-comments');comments.hidden=true;
  toggle.addEventListener('click',async()=>{comments.hidden=!comments.hidden;if(!comments.hidden)await loadComments(post.id,comments);});
  article.append(toggle,comments);
 }
 return article;
}
async function loadComments(id,box){
 box.replaceChildren(el('p','댓글을 불러오는 중입니다…'));
 try{
  const data=await request('/api/community/comments?postId='+encodeURIComponent(id));
  box.replaceChildren();
  for(const comment of data.items||[]){
   const item=el('div',null,'live-comment');
   item.append(el('b',comment.author_label||'회원'),el('p',comment.body));box.append(item);
  }
  if(!data.items?.length)box.append(el('p','승인된 댓글이 없습니다.'));
  if(!user){const link=el('a','댓글은 로그인 후 등록할 수 있습니다 →');link.href=login;box.append(link);return;}
  const form=el('form',null,'live-comment-form');
  const input=el('textarea');input.required=true;input.minLength=2;input.maxLength=800;input.placeholder='승인 후 공개되는 댓글을 작성해 주세요.';
  const button=el('button','댓글 접수','extra-submit');button.type='submit';
  const feedback=el('p',null,'apply-feedback');feedback.setAttribute('role','status');
  form.append(input,button,feedback);
  form.addEventListener('submit',async e=>{e.preventDefault();if(!form.reportValidity())return;
   button.disabled=true;
   try{const result=await request('/api/community/comments',{data:{postId:id,content:input.value},member:true});show(feedback,result.message||'댓글 검토 대기');input.value='';}
   catch(err){show(feedback,'댓글 접수 실패: '+err.message);}finally{button.disabled=false;}
  });box.append(form);
 }catch(err){show(box,'댓글 조회 실패: '+err.message);}
}
async function posts(){
 const box=$('#live-community-list');if(!box)return;box.replaceChildren(el('p','게시글을 불러오는 중입니다…'));
 try{
  const data=await request('/api/community/posts?category='+encodeURIComponent(filter));
  let mine=[];if(user){const d=await request('/api/community/posts?mine=1&category='+encodeURIComponent(filter),{member:true});mine=d.items||[];}
  box.replaceChildren(el('h3','실제 회원 게시글'));
  const ids=new Set();
  for(const p of [...mine,...(data.items||[])]){if(ids.has(p.id))continue;ids.add(p.id);box.append(panel(p,mine.some(m=>m.id===p.id)));}
  if(!ids.size)box.append(el('p','현재 게시글이 없습니다. 아래의 예시 게시글은 샘플입니다.'));
 }catch(err){show(box,'게시글 조회 실패: '+err.message);}
}
function bindCommunity(){
 if(!formPost)return;
 const box=el('section',null,'live-community');box.id='live-community-list';$('#community-board')?.before(box);
 const label=el('label','게시판 분류');const sel=el('select');sel.name='category';sel.required=true;
 for(const [key,name] of Object.entries(cats)){const opt=el('option',name);opt.value=key;sel.append(opt);}label.append(sel);
 formPost.prepend(label);
 formPost.addEventListener('submit',async e=>{e.preventDefault();const feedback=$('#story-feedback');
   if(!formPost.reportValidity())return;if(!user){show(feedback,'회원 로그인 후 게시할 수 있습니다.');return;}
   const f=new FormData(formPost),btn=formPost.querySelector('[type=submit]');
   btn.disabled=true;show(feedback,'게시글을 전송하는 중입니다…');
   try{const res=await request('/api/community/posts',{data:{category:f.get('category'),title:f.get('title'),content:f.get('content')},member:true});
    show(feedback,'게시글 #'+res.id+' 접수 완료 · 운영자 승인 대기');formPost.reset();await posts();}
   catch(err){show(feedback,'게시글 접수 실패: '+err.message);}finally{btn.disabled=false;}
 });
 for(const btn of all('[data-board-filter]'))btn.addEventListener('click',()=>{
  filter=btn.dataset.boardFilter||'all';
  for(const b of all('[data-board-filter]')){b.classList.toggle('active',b===btn);b.setAttribute('aria-pressed',String(b===btn));}
  let count=0;
  for(const sample of all('#community-board [data-board-cat]')){sample.hidden=filter!=='all'&&sample.dataset.boardCat!==filter;if(!sample.hidden)count++;}
  const empty=$('.community-empty');if(empty)empty.hidden=Boolean(count);
  posts();
 });
}
async function main(){
 updateLabels();bindApply();bindCommunity();
 try{
  const auth=await import('../../auth/client.mjs');getSession=auth.getSession;getAuthClient=auth.getAuthClient;
  const session=await getSession();user=session?.user||null;
 }catch(err){user=null;}
 memberStatus();await Promise.all([applications(),posts()]);
}
main();
})();