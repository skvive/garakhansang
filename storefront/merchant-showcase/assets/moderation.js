(()=>{
'use strict';
const notice=document.querySelector('#moderation-status');
const root=document.querySelector('#moderation-items');
const node=(tag,value)=>{const n=document.createElement(tag);if(value!==undefined)n.textContent=String(value);return n;};
let csrf='';
async function api(path,options={}){
  const r=await fetch(path,{credentials:'same-origin',cache:'no-store',...options});
  const v=await r.json().catch(()=>({}));
  if(!r.ok)throw Error(v.error||'서버 응답 오류 '+r.status);
  return v;
}
async function refresh(){
  try{
    const account=await api('/api/auth/me');
    if(!account.authenticated||!['superadmin','ops','content'].includes(account.user?.role))
      throw Error('운영자 권한이 필요합니다. 관리자 로그인 후 접속하세요.');
    csrf=account.csrf;
    const list=await api('/api/community/moderation');
    root.replaceChildren();
    let count=0;
    const defs=[['applications','입점 신청'],['posts','게시글'],['comments','댓글']];
    for(const [kind,title] of defs){
      root.append(node('h2',title));
      const rows=list[kind]||[];
      if(!rows.length)root.append(node('p','검수 대기 항목 없음'));
      for(const row of rows){
        count++;
        const card=node('article');
        card.append(node('h3','#'+row.id+' · '+(row.shop_name||row.title||'댓글')));
        const fields=kind==='applications'?['contact_name','phone','email','category','shop_location','description']:
          kind==='posts'?['category','author_label','body']:['post_id','author_label','body'];
        for(const field of fields)card.append(node('p',field+': '+String(row[field]??'')));
        for(const [state,label] of [['approved',kind==='applications'?'검토 완료':'공개 승인'],['rejected','반려']]){
          const button=node('button',label);button.type='button';
          if(state==='rejected')button.className='reject';
          button.addEventListener('click',async()=>{
            button.disabled=true;
            try{
              const done=await api('/api/community/moderation',{method:'POST',
                headers:{'Content-Type':'application/json','X-Garak-CSRF':csrf},
                body:JSON.stringify({kind,id:row.id,status:state})});
              notice.textContent='#'+done.id+' 상태 변경 완료: '+done.status;
              await refresh();
            }catch(e){notice.textContent='검수 오류: '+e.message;button.disabled=false;}
          });
          card.append(button);
        }
        root.append(card);
      }
    }
    notice.textContent=count?'검수 대기 총 '+count+'건':'검수 대기 항목이 없습니다.';
  }catch(e){notice.textContent=e.message;root.replaceChildren();}
}
refresh();
})();