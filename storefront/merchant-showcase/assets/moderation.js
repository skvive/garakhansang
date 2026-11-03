(()=>{'use strict';
const root=document.querySelector('#moderation-items'),status=document.querySelector('#moderation-status');
const el=(tag,v)=>{const x=document.createElement(tag);if(v!==undefined)x.textContent=String(v);return x;};
let csrf='';
async function api(path,options={}){
 const r=await fetch(path,{credentials:'same-origin',cache:'no-store',...options});
 const d=await r.json().catch(()=>({}));
 if(!r.ok)throw Error(d.error||'서버 오류 ('+r.status+')');
 return d;
}
async function refresh(){
 root.replaceChildren();
 try{
  const s=await api('/api/auth/me');
  if(!s.authenticated||!['superadmin','ops','content'].includes(s.user?.role))
    throw Error('게시판 운영자 계정으로 먼저 로그인하세요.');
  csrf=s.csrf;
  const rows=await api('/api/community/moderation');
  let count=0;
  for(const [kind,label,fields] of [
   ['applications','입점 신청',['contact_name','phone','email','category','shop_location','description']],
   ['posts','게시글',['category','author_label','body']],
   ['comments','댓글',['post_id','author_label','body']]]){
   root.append(el('h2',label));
   const items=rows[kind]||[];
   if(!items.length)root.append(el('p','대기 중인 항목이 없습니다.'));
   for(const item of items){
    count++;const article=el('article');article.className='moderation-entry';
    article.append(el('h3','#'+item.id+' · '+(item.shop_name||item.title||'댓글')));
    for(const key of fields)article.append(el('p',key+': '+String(item[key]??'')));
    for(const [decision,caption] of [['approved',kind==='applications'?'검토 완료':'승인'],['rejected','반려']]){
      const button=el('button',caption);button.type='button';
      if(decision==='rejected')button.className='reject';
      button.addEventListener('click',async()=>{
       button.disabled=true;
       try{const result=await api('/api/community/moderation',{
        method:'POST',headers:{'Content-Type':'application/json','X-Garak-CSRF':csrf},
        body:JSON.stringify({kind,id:item.id,status:decision})
       });status.textContent='#'+result.id+' 처리 결과: '+result.status;await refresh();}
       catch(err){status.textContent='검수 실패: '+err.message;button.disabled=false;}
      });
      article.append(button);
    }root.append(article);
   }
  }
  status.textContent=count?'검토 대기 '+count+'건':'모든 검수 항목 처리 완료';
 }catch(err){root.replaceChildren();status.textContent='연결 실패: '+err.message;}
}
refresh();
})();