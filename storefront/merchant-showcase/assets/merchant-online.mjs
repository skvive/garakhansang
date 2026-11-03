import {getSession} from '../../auth/client.mjs';

const $=selector=>document.querySelector(selector);
const make=(tag,value,className)=>{
  const node=document.createElement(tag);
  if(value!==undefined&&value!==null)node.textContent=String(value);
  if(className)node.className=className;
  return node;
};
const loginUrl='/login.html?next='+encodeURIComponent(location.pathname.slice(1));
const categories={notice:'입점 안내',season:'제철 이야기',story:'상인 이야기',question:'질문'};
let currentUser=null,filter='all';

async function bearer(){
  const config=await fetch('/auth/config.public.json',{cache:'no-store'}).then(r=>{
    if(!r.ok)throw Error('회원 인증 설정을 불러오지 못했습니다.');
    return r.json();
  });
  if(typeof config.authUrl!=='string'||!config.authUrl.startsWith('https://'))throw Error('인증 서버 설정 오류');
  // Managed Neon Auth issues short-lived JWTs using the current secure session cookie.
  const response=await fetch(config.authUrl.replace(/\/$/,'')+'/token',{
    credentials:'include',cache:'no-store',signal:AbortSignal.timeout(10000)
  });
  if(!response.ok)throw Error('회원 인증이 만료되었습니다. 다시 로그인해 주세요.');
  const result=await response.json();
  const token=result?.token||result?.data?.token||result?.access_token;
  if(typeof token!=='string'||token.split('.').length!==3)throw Error('로그인 토큰 발급 실패');
  return token;
}

async function request(url,{method='GET',body,auth=false}={}){
  const headers={Accept:'application/json'};
  if(body!==undefined)headers['Content-Type']='application/json';
  if(auth)headers.Authorization='Bearer '+await bearer();
  const r=await fetch(url,{method,headers,credentials:'same-origin',cache:'no-store',
    body:body===undefined?undefined:JSON.stringify(body)});
  const data=await r.json().catch(()=>({}));
  if(!r.ok)throw Error(data.error||'요청 처리 실패 ('+r.status+')');
  return data;
}

async function start(){
  const oldText=$('.prep-sign small');
  if(oldText)oldText.textContent='매장 5곳은 샘플로 표시됩니다. 새 신청·글·댓글은 회원 로그인 후 실제 접수되며 운영자 승인이 필요합니다. 정식 입점·계약과는 별개입니다.';
  const foot=$('.footer-legal');
  if(foot)foot.textContent='현재 각 입점 업소는 입점을 준비 중이며, 본 페이지는 샘플 페이지입니다. 신규 게시물 및 신청은 검토 후 처리됩니다.';
  const applyHelp=$('.form-help');
  if(applyHelp)applyHelp.textContent='회원 로그인 후 제출하면 Neon DB에 검토 대기로 접수됩니다. 계약 및 판매 승인은 별도입니다.';
  const note=$('.extra-info p');
  if(note)note.textContent='업체·담당자 연락처는 심사 안내 용도로만 저장됩니다. 개인정보 열람·삭제 요청은 운영자에게 문의하세요.';
  const title=$('#story-draft-form .extra-submit');
  if(title)title.textContent='게시글 접수하기';
  const applyButton=$('#merchant-apply-form .extra-submit');
  if(applyButton)applyButton.textContent='입점 신청 접수하기';
  const p=$('.community-bottom .extra-form-panel > p');
  if(p)p.textContent='작성한 글은 실제 저장되지만, 운영자 승인 전에는 공개되지 않습니다.';
  const panel=$('.extra-form-panel');
  const member=make('p',null,'member-status');
  member.id='member-status';member.setAttribute('role','status');
  panel?.insertBefore(member,panel.querySelector('form'));
  try{
    const session=await getSession();
    currentUser=session?.user||null;
  }catch{currentUser=null;}
  if(currentUser)member.textContent=(currentUser.name||currentUser.email||'회원')+'님 로그인됨';
  else{
    member.append(make('span','입점 신청과 게시글·댓글 작성에는 로그인이 필요합니다. '));
    const link=make('a','로그인 / 회원가입 →');link.href=loginUrl;member.append(link);
  }
  bindApply();
  bindCommunity();
}

function bindApply(){
  const form=$('#merchant-apply-form');
  if(!form)return;
  const privacy=make('p','수집항목: 담당자·연락처·매장정보 | 목적: 입점 심사 및 연락 | 입점 미확정. 개인정보 열람·삭제는 운영자에게 요청할 수 있습니다.','form-help');
  const link=make('a','개인정보 처리 안내');
  link.href='../legal/privacy.html';privacy.append(' · ',link);
  form.querySelector('button[type=submit]')?.before(privacy);
  form.addEventListener('submit',async event=>{
    event.preventDefault();
    const feedback=$('#apply-feedback');
    if(!form.reportValidity())return;
    if(!currentUser){feedback.textContent='로그인 후 접수할 수 있습니다.';return;}
    const f=new FormData(form);
    const data=Object.fromEntries(['shopName','contactName','phone','email','category','location','description']
      .map(key=>[key,String(f.get(key)||'')]));
    data.consent=f.has('consent');
    const button=form.querySelector('[type=submit]');
    button.disabled=true;feedback.textContent='신청 중…';
    try{
      const result=await request('/api/merchant-applications',{method:'POST',auth:true,body:data});
      feedback.textContent='입점 신청 #'+result.id+' 접수 완료 · 검토 대기 (계약 완료 아님)';
      form.reset();
      await listApplications(form);
    }catch(error){feedback.textContent='접수하지 못했습니다: '+error.message+' 입력 내용은 유지됩니다.';}
    finally{button.disabled=false;}
  });
  if(currentUser)listApplications(form);
}

async function listApplications(form){
  let holder=$('#application-history');
  if(!holder){holder=make('section');holder.id='application-history';form.parentElement.append(holder);}
  try{
    const data=await request('/api/merchant-applications',{auth:true});
    holder.replaceChildren(make('h3','내 입점 신청 내역'));
    if(!data.items?.length)holder.append(make('p','접수한 신청이 없습니다.'));
    for(const entry of data.items||[]){
      const state=entry.status==='reviewed'?'검토 완료':entry.status==='rejected'?'반려':'검토 대기';
      holder.append(make('p','#'+entry.id+' · '+entry.shop_name+' · '+state));
    }
  }catch(error){holder.textContent='신청 내역을 불러오지 못했습니다: '+error.message;}
}

function card(post,mine){
  const item=make('article',null,'live-post');
  item.dataset.boardCat=post.category;
  const text=categories[post.category]||post.category;
  const pending=mine&&post.status!=='approved';
  item.append(make('span',text+' · '+(post.author_label||'회원')+(pending?' · 검토 대기':' · 회원 게시글'),'sample-tag'),
    make('h3',post.title),make('p',post.body));
  if(post.status==='approved'){
    const button=make('button','댓글 보기 / 작성','extra-submit');button.type='button';
    const comments=make('div',null,'live-comments');comments.hidden=true;
    button.addEventListener('click',async()=>{
      comments.hidden=!comments.hidden;if(!comments.hidden)await loadComments(post.id,comments);
    });
    item.append(button,comments);
  }
  return item;
}

async function loadComments(id,container){
  container.replaceChildren(make('p','댓글을 불러오는 중…'));
  try{
    const entries=(await request('/api/community/comments?postId='+encodeURIComponent(id))).items||[];
    container.replaceChildren();
    for(const entry of entries){
      const item=make('div',null,'live-comment');
      item.append(make('b',entry.author_label||'회원'),make('p',entry.body));container.append(item);
    }
    if(!entries.length)container.append(make('p','승인된 댓글이 없습니다.'));
    if(!currentUser){
      const link=make('a','댓글 작성은 로그인 후 가능합니다 →');link.href=loginUrl;
      container.append(link);return;
    }
    const form=make('form',null,'live-comment-form');
    const input=make('textarea');
    input.maxLength=800;input.minLength=2;input.required=true;input.placeholder='댓글 (승인 후 공개)';
    const button=make('button','댓글 접수','extra-submit');button.type='submit';
    const status=make('p',null,'apply-feedback');status.setAttribute('role','status');
    form.append(input,button,status);container.append(form);
    form.addEventListener('submit',async event=>{
      event.preventDefault();if(!form.reportValidity())return;
      button.disabled=true;
      try{
        const result=await request('/api/community/comments',{method:'POST',auth:true,
          body:{postId:id,content:input.value}});
        status.textContent=result.message;input.value='';
      }catch(error){status.textContent='댓글 오류: '+error.message;}
      finally{button.disabled=false;}
    });
  }catch(error){container.textContent='댓글을 불러오지 못했습니다: '+error.message;}
}

async function loadPosts(){
  const root=$('#live-community-list');
  if(!root)return;
  root.replaceChildren(make('p','실제 게시글을 불러오는 중…'));
  try{
    const publicPosts=(await request('/api/community/posts?category='+filter)).items||[];
    const mine=currentUser?
      (await request('/api/community/posts?mine=1&category='+filter,{auth:true})).items||[]:[];
    const seen=new Set();
    root.replaceChildren(make('h3','회원 게시글'));
    for(const entry of [...mine,...publicPosts]){
      if(seen.has(entry.id))continue;
      seen.add(entry.id);root.append(card(entry,mine.some(row=>row.id===entry.id)));
    }
    if(!seen.size)root.append(make('p','아직 공개된 회원 게시글이 없습니다. 아래는 샘플입니다.'));
  }catch(error){root.replaceChildren(make('p','게시글 연결 오류: '+error.message));}
}

function bindCommunity(){
  const form=$('#story-draft-form');
  if(!form)return;
  const board=$('#community-board');
  const root=make('section',null,'live-community');
  root.id='live-community-list';board.before(root);
  const select=make('select');select.name='category';select.required=true;
  for(const [key,title] of Object.entries(categories)){
    const option=make('option',title);option.value=key;select.append(option);
  }
  const label=make('label','게시판 분류');label.append(select);
  form.insertBefore(label,form.firstElementChild);
  form.addEventListener('submit',async event=>{
    event.preventDefault();
    const feedback=$('#story-feedback');
    if(!form.reportValidity())return;
    if(!currentUser){feedback.textContent='회원 로그인 후 게시할 수 있습니다.';return;}
    const data=new FormData(form);
    const button=form.querySelector('[type=submit]');button.disabled=true;
    try{
      const result=await request('/api/community/posts',{method:'POST',auth:true,body:{
        category:data.get('category'),title:data.get('title'),content:data.get('content')}});
      feedback.textContent='게시글 #'+result.id+' 접수 완료 · 운영자 승인 대기';
      form.reset();await loadPosts();
    }catch(error){feedback.textContent='게시글 접수 오류: '+error.message;}
    finally{button.disabled=false;}
  });
  const buttons=[...document.querySelectorAll('[data-board-filter]')];
  for(const btn of buttons)btn.addEventListener('click',()=>{
    filter=btn.dataset.boardFilter||'all';
    for(const b of buttons){
      b.classList.toggle('active',b===btn);b.setAttribute('aria-pressed',String(b===btn));
    }
    let shown=0;
    for(const sample of document.querySelectorAll('#community-board [data-board-cat]')){
      const visible=filter==='all'||sample.dataset.boardCat===filter;
      sample.hidden=!visible;if(visible)shown++;
    }
    const empty=$('.community-empty');if(empty)empty.hidden=shown!==0;
    loadPosts();
  });
  loadPosts();
}

start();
