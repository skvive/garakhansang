import {createAuthClient} from '@neondatabase/auth';
const base=import.meta.env.VITE_GHO_NEON_AUTH_BASE_URL;
const out=document.querySelector('#output');const google=document.querySelector('#google');const status=document.querySelector('#status');
if(!base||!base.startsWith('https://')){out.textContent='Neon Auth URL을 설정하세요';google.disabled=true;status.disabled=true;}
else {const auth=createAuthClient(base);
google.onclick=async()=>{try{const r=await auth.signIn.social({provider:'google',callbackURL:location.origin+location.pathname});if(r.error)throw r.error;}catch{out.textContent='OAuth 로그인 시작 실패';}};
status.onclick=async()=>{try{const {data,error}=await auth.getSession();if(error)throw error;out.textContent=data?.user?'로그인 확인됨':'로그인 전';}catch{out.textContent='세션 확인 실패';}};
}
