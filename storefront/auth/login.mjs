import { getAuthClient, getSession, signOut, signInWithGoogle } from './client.mjs';

const form=document.getElementById('authForm'), logged=document.getElementById('loggedPanel');
const msg=document.getElementById('authMsg'),userEmail=document.getElementById('userEmail');
const googleBtn=document.getElementById('googleBtn'),toggle=document.getElementById('signupToggle');
const submit=document.getElementById('emailSubmit'),nameGroup=document.getElementById('signupNameGroup');
let mode='signin',busy=false;
const destination=()=>{
 const next=new URLSearchParams(location.search).get('next');
 return ['merchant-showcase/apply.html','merchant-showcase/community.html'].includes(next)?'/'+next:'/mypage.html';
};
function status(text,kind=''){msg.textContent=text;msg.className='auth-msg'+(kind?' '+kind:'');}
function showLogged(user){
 form.hidden=true;googleBtn.hidden=true;logged.hidden=false;
 userEmail.textContent=user.email||user.name||'로그인됨';
}
function showSignIn(){
 form.hidden=false;googleBtn.hidden=false;logged.hidden=true;
}
function setMode(next){
 mode=next;
 document.querySelector('#authForm h1').textContent=mode==='signup'?'가락한상 회원가입':'가락한상 로그인';
 nameGroup.hidden=mode!=='signup';
 submit.textContent=mode==='signup'?'새 계정으로 회원가입':'이메일로 로그인';
 toggle.textContent=mode==='signup'?'이미 계정이 있나요? 로그인':'처음이신가요? 회원가입';
 form.elements.password.autocomplete=mode==='signup'?'new-password':'current-password';
 status('');
}
function setBusy(value){
 busy=value;submit.disabled=value;toggle.disabled=value;googleBtn.disabled=value;
}
toggle.addEventListener('click',()=>setMode(mode==='signin'?'signup':'signin'));
document.getElementById('signOutBtn')?.addEventListener('click',async()=>{
 try{await signOut();showSignIn();status('로그아웃했습니다.','ok');}
 catch{status('로그아웃에 실패했습니다. 다시 시도해 주세요.','error');}
});
googleBtn.addEventListener('click',async()=>{
 if(busy)return;
 setBusy(true);status('Google 로그인 창으로 이동합니다…');
 try{
   const result=await signInWithGoogle(destination());
   if(result?.error)throw new Error(result.error.message||'Google 로그인 실패');
 }catch(error){status('Google 로그인 연결에 실패했습니다. 다시 시도해 주세요.','error');}
 finally{setBusy(false);}
});
form.addEventListener('submit',async e=>{
 e.preventDefault();if(busy)return;
 const email=String(form.elements.email.value||'').trim(),password=String(form.elements.password.value||'');
 const name=String(document.getElementById('signupName').value||'').trim();
 if(!email.includes('@')||password.length<8){status('이메일과 8자 이상의 비밀번호를 확인해 주세요.','error');return;}
 if(mode==='signup'&&(name.length<2||name.length>50)){status('회원 이름은 2~50자로 입력해 주세요.','error');return;}
 setBusy(true);status('Neon 계정으로 연결하는 중…');
 try{
  const auth=await getAuthClient();
  const result=mode==='signup'?
    await auth.signUp.email({name,email,password}):
    await auth.signIn.email({email,password});
  if(result?.error)throw new Error(result.error.message||'인증에 실패했습니다.');
  const session=await getSession();
  if(session?.user){
    status('인증되었습니다. 내 계정으로 이동합니다.','ok');
    location.assign(destination());return;
  }
  if(mode==='signup'){
    status('계정 생성 요청이 접수됐습니다. 이메일 인증이 필요한 경우 먼저 인증을 완료한 다음 로그인하세요.','ok');
    setMode('signin');status('회원가입 후 인증 이메일을 확인하고 로그인해 주세요.','ok');
  } else {
    status('로그인 후 세션을 확인하지 못했습니다. 다시 로그인해 주세요.','error');
  }
 }catch(error){status(error?.message||'인증 서버 연결에 실패했습니다.','error');}
 finally{setBusy(false);}
});
(async()=>{
 try{
  const session=await getSession();
  if(session?.user){const target=destination();if(target!=='/mypage.html'){location.replace(target);return;}showLogged(session.user);}
 }catch{
  // Show the form without falsely declaring a signed-in state.
 }
})();