import { getAuthClient, getSession, signOut, signInWithGoogle } from './client.mjs';

const form = document.getElementById('authForm');
const logged = document.getElementById('loggedPanel');
const msg = document.getElementById('authMsg');
const userEmail = document.getElementById('userEmail');
const googleBtn = document.getElementById('googleBtn');

function setMsg(text, kind = '') {
  msg.textContent = text;
  msg.className = 'auth-msg' + (kind ? ` ${kind}` : '');
}

function showLogged(user) {
  form.hidden = true;
  googleBtn.hidden = true;
  logged.hidden = false;
  userEmail.textContent = user.email || user.name || '로그인됨';
}

async function refresh() {
  const data = await getSession();
  if (data?.user) showLogged(data.user);
}

document.getElementById('signOutBtn')?.addEventListener('click', async () => {
  await signOut();
  form.hidden = false;
  googleBtn.hidden = false;
  logged.hidden = true;
  setMsg('로그아웃했습니다.', 'ok');
});

googleBtn?.addEventListener('click', async () => {
  setMsg('Google 계정으로 이동 중…');
  const result = await signInWithGoogle();
  if (result?.error) setMsg(result.error.message || 'Google 로그인에 실패했습니다.', 'error');
});

form?.addEventListener('submit', async (e) => {
  e.preventDefault();
  setMsg('처리 중…');
  const email = form.email.value.trim();
  const password = form.password.value;
  const auth = await getAuthClient();
  const result = await auth.signIn.email({ email, password });
  if (result.error) {
    const created = await auth.signUp.email({ name: email.split('@')[0] || '손님', email, password });
    if (created.error) {
      setMsg(created.error.message || result.error.message || '인증에 실패했습니다.', 'error');
      return;
    }
  }
  const session = await getSession();
  if (session?.user) {
    setMsg('환영합니다.', 'ok');
    showLogged(session.user);
    return;
  }
  setMsg('로그인되었습니다. 이메일 확인이 필요할 수 있습니다.', 'ok');
});

refresh().catch(() => setMsg(''));
