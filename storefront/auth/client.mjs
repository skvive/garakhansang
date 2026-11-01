import { createAuthClient } from 'https://esm.sh/@neondatabase/neon-js@1/auth';

let clientPromise;

export async function getAuthClient() {
  if (!clientPromise) {
    const root = window.GARAK_ROOT || '';
    clientPromise = fetch(`${root}auth/config.public.json`, { cache: 'no-store' })
      .then((r) => r.json())
      .then((cfg) => createAuthClient(cfg.authUrl));
  }
  return clientPromise;
}

export async function getSession() {
  const auth = await getAuthClient();
  const result = await auth.getSession();
  return result.data ?? null;
}

export async function signOut() {
  const auth = await getAuthClient();
  await auth.signOut();
}

export async function signInWithGoogle() {
  const auth = await getAuthClient();
  return auth.signIn.social({
    provider: 'google',
    callbackURL: window.location.origin + (window.GARAK_ROOT || '') + 'mypage.html',
  });
}
