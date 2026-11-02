// Neon Auth: pin a verified browser-compatible SDK, retry on CDN/network failure.
const PRIMARY_SDK = 'https://esm.sh/@neondatabase/auth@0.7.0-beta?bundle';
const BACKUP_SDK = 'https://cdn.jsdelivr.net/npm/@neondatabase/auth@0.7.0-beta/+esm';
let clientPromise;

async function initializeClient() {
  const [sdk, cfg] = await Promise.all([
    import(PRIMARY_SDK).catch(() => import(BACKUP_SDK)),
    fetch((window.GARAK_ROOT || '') + 'auth/config.public.json', { cache: 'no-store' })
      .then(r => {
        if (!r.ok) throw new Error('Neon Auth configuration unavailable');
        return r.json();
      }),
  ]);
  if (typeof sdk.createAuthClient !== 'function' ||
      !cfg || typeof cfg.authUrl !== 'string' ||
      !/^https:\/\//i.test(cfg.authUrl)) {
    throw new Error('Invalid Neon Auth configuration');
  }
  return sdk.createAuthClient(cfg.authUrl);
}

export async function getAuthClient() {
  if (!clientPromise) {
    clientPromise = initializeClient().catch(error => {
      clientPromise = null; // allow retry after a transient network/CDN error
      throw error;
    });
  }
  return clientPromise;
}

export async function getSession() {
  const auth = await getAuthClient();
  const result = await auth.getSession();
  if (result?.error) throw new Error('Neon Auth session temporarily unavailable');
  return result?.data ?? null;
}

export async function signOut() {
  const auth = await getAuthClient();
  const result = await auth.signOut();
  if (result?.error) throw new Error('Neon Auth sign out failed');
}

export async function signInWithGoogle() {
  const auth = await getAuthClient();
  return auth.signIn.social({
    provider: 'google',
    // Do not concatenate location.origin with a relative pathname: it omits '/'.
    callbackURL: new URL('/mypage.html', window.location.origin).href,
  });
}
