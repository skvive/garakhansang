import {getAuthClient,getSession} from '../../auth/client.mjs';
const $=s=>document.querySelector(s);
const el=(tag,text)=>{const x=document.createElement(tag);if(text!==undefined)x.textContent=String(text);return x};
const login='/login.html?next='+encodeURIComponent(location.pathname.slice(1));
let user=null,category='all';
async function token(){
 const auth=await getAuthClient();
 let r=typeof auth.getJWTToken==='function'?await auth.getJWTToken():await auth.token();
 let v=typeof r==='string'?r:(r?.data?.token||r?.data?.access_token||r?.token);
 if(!v)v=(await auth.getSession())?.data?.session?.access_token;
 if(typeof v!=='string'||v.split('.').length!==3)throw Error('다시 로그인해 주세요.');
 return v;
}
async function request(url,method='GET',data=null,secure=false){
 const headers={Accept:'application/json'};
 if(data)headers['Content-Type']='application/json';
 if(secure)headers.Authorization='Bearer '+await token();
 const response=await fetch(url,{method,headers,body:data?JSON.stringify(data):undefined,cache:'no-store',credentials:'same-origin'});
 const value=await response.json().catch(()=>({}));
 if(!response.ok)throw Error(value.error||'서버 오류 '+response.status);
 return value;
}
function text(selector,value){const e=$(selector);if(e)e.textContent=value}
function notice(){
 const parent=$('.extra-form-panel');if(parent){const p=el('p',user?'로그인: '+(user.name||user.email||'회원'):'회원 로그인 후 접수할 수 있습니다. ');p.className='member-status';parent.insertBefore(p,parent.querySelector('form'));if(!user){const a=el('a','로그인 / 가입 →');a.href=login;p.append(a)}}
 text('.prep-sign small','현장 사진을 사용한 5개 매장은 입점 준비 샘플입니다. 신규 신청·게시글·댓글은 로그인 후 DB에 저장되며 운영자 검토 전에는 정식 입점이나 공개 게시를 의미하지 않습니다.');
 text('.footer-legal','현재 각 입점 업소는 입점을 준비 중이며 본 페이지는 샘플 페이지입니다. 신규 신청 및 커뮤니티 글은 승인 전까지 검토 대기 상태입니다.');
}
async function applications(){
 if(!$('#merchant-apply-form')||!user)return;
 let pane=$('#my-applications');if(!pane){pane=el('section');pane.id='my-applications';$('#merchant-apply-form').after(pane)}
 try{const result=await request('/api/merchant-applications','GET',null,true);pane.replaceChildren(el('h3','내 신청 현황'));for(const a of result.items||[])pane.append(el('p','#'+a.id+' '+a.shop_name+' · '+(a.status==='pending'?'검토 대기':a.status==='reviewed'?'검토 완료':'반려')));if(!result.items?.length)pane.append(el('p','접수된 내역이 없습니다.'))}catch(e){pane.textContent=e.message}
}
const apply=$('#merchant-apply-form');
if(apply){text('.form-help','로그인 후 실제 접수됩니다. 제출 정보는 Neon DB에 저장되며 심사 완료 전에는 정식 입점이 아닙니다.');text('.extra-info p','신청 내역은 실제로 저장되지만 입점 승인·계약·결제는 별도입니다.');text('#merchant-apply-form .extra-submit','입점 신청 접수하기');
 apply.addEventListener('submit',async e=>{e.preventDefault();if(!apply.reportValidity())return;const status=$('#apply-feedback');if(!user){status.textContent='회원 로그인 후 신청하세요.';return;}
 const fd=new FormData(apply),data={};for(const k of ['shopName','contactName','phone','email','category','location','description'])data[k]=String(fd.get(k)||'');data.consent=fd.has('consent');
 const button=apply.querySelector('[type=submit]');button.disabled=true;status.textContent='접수 중…';
 try{const result=await request('/api/merchant-applications','POST',data,true);status.textContent='접수 완료 #'+result.id+' · 운영자 검토 대기';apply.reset();await applications()}catch(err){status.textContent='접수 실패: '+err.message}finally{button.disabled=false}
 });
}
async function showComments(id,container){
 container.replaceChildren(el('p','불러오는 중…'));
 try{const result=await request('/api/community/comments?postId='+id);container.replaceChildren();
 for(const c of result.items||[]){const line=el('div');line.className='live-comment';line.append(el('strong',c.author_label),el('p',c.body));container.append(line)}
 if(!result.items?.length)container.append(el('p','아직 승인된 댓글이 없습니다.'));
 if(!user){const a=el('a','로그인 후 댓글 작성 →');a.href=login;container.append(a);return}
 const form=el('form'),input=el('textarea'),button=el('button','댓글 등록'),status=el('p');
 input.required=true;input.minLength=2;input.maxLength=800;input.placeholder='운영자 승인 후 댓글이 공개됩니다.';button.type='submit';button.className='extra-submit';status.setAttribute('role','status');form.append(input,button,status);
 form.addEventListener('submit',async e=>{e.preventDefault();if(!form.reportValidity())return;button.disabled=true;try{const r=await request('/api/community/comments','POST',{postId:id,content:input.value},true);status.textContent='댓글 #'+r.id+' 접수 완료 · 검토 대기';input.value=''}catch(x){status.textContent=x.message}finally{button.disabled=false}});
 container.append(form);
 }catch(err){container.textContent='댓글 오류: '+err.message}
}
function card(post,own){
 const article=el('article');article.className='live-post';
 const small=el('small',post.category+' · '+post.author_label+(own&&post.status!=='approved'?' · 승인 대기':''));article.append(small,el('h3',post.title),el('p',post.body));
 if(post.status==='approved'){const b=el('button','댓글 보기/쓰기'),box=el('div');b.type='button';b.className='extra-submit';box.hidden=true;b.addEventListener('click',async()=>{box.hidden=!box.hidden;if(!box.hidden)await showComments(post.id,box)});article.append(b,box)}
 return article;
}
async function posts(){
 const box=$('#live-posts');if(!box)return;box.replaceChildren(el('p','회원 게시글 불러오는 중…'));
 try{const publicRows=(await request('/api/community/posts?category='+encodeURIComponent(category))).items||[];
 const mine=user?(await request('/api/community/posts?mine=1&category='+encodeURIComponent(category),'GET',null,true)).items||[]:[];
 const seen=new Set();box.replaceChildren(el('h3','회원 게시글'));
 for(const p of [...mine,...publicRows]){if(seen.has(p.id))continue;seen.add(p.id);box.append(card(p,mine.some(x=>x.id===p.id)))}
 if(!seen.size)box.append(el('p','현재 공개된 게시글이 없습니다. 아래 글은 샘플 콘텐츠입니다.'));
 }catch(err){box.textContent='게시판 연결 오류: '+err.message}
}
const story=$('#story-draft-form');
if(story){text('.extra-hero p','상인 이야기 커뮤니티입니다. 기존 예시 글은 샘플이며, 회원 글은 운영자 승인 후 공개됩니다.');text('.community-bottom .extra-form-panel > p','로그인 후 게시글을 접수하면 실제 DB에 저장됩니다.');text('#story-draft-form .extra-submit','게시글 접수하기');
 const sel=el('select');sel.name='category';for(const [k,v] of Object.entries({notice:'입점 안내',season:'제철 이야기',story:'상인 이야기',question:'질문'})){const o=el('option',v);o.value=k;sel.append(o)}const label=el('label','게시판 분류');label.append(sel);story.prepend(label);
 const root=el('section');root.id='live-posts';root.className='live-community';$('#community-board').before(root);
 story.addEventListener('submit',async e=>{e.preventDefault();if(!story.reportValidity())return;const status=$('#story-feedback');if(!user){status.textContent='로그인 후 게시할 수 있습니다.';return}
 const fd=new FormData(story),b=story.querySelector('[type=submit]');b.disabled=true;try{const out=await request('/api/community/posts','POST',{category:fd.get('category'),title:fd.get('title'),content:fd.get('content')},true);status.textContent='게시글 #'+out.id+' 저장 완료 · 승인 대기';story.reset();await posts()}catch(x){status.textContent='등록 실패: '+x.message}finally{b.disabled=false}});
 const buttons=[...document.querySelectorAll('[data-board-filter]')],examples=[...document.querySelectorAll('#community-board [data-board-cat]')];
 for(const button of buttons)button.addEventListener('click',()=>{category=button.dataset.boardFilter||'all';for(const b of buttons){const active=b===button;b.classList.toggle('active',active);b.setAttribute('aria-pressed',String(active))}
 let count=0;for(const item of examples){item.hidden=category!=='all'&&item.dataset.boardCat!==category;if(!item.hidden)count++}const empty=$('.community-empty');if(empty)empty.hidden=count!==0;posts()});
}
try{user=(await getSession())?.user||null}catch{user=null}notice();await Promise.all([applications(),posts()]);
