// Garak V8: cache only explicit public demo assets. Never cache account/admin/API data.
const CACHE='garak-public-v15';
const ASSETS=['/index.html','/assets/css/style.css','/assets/css/garak-brand-v10.css','/assets/js/garak-brand-v10.js','/assets/brand/wordmark.png','/assets/brand/mascot.webp','/assets/js/app.js','/assets/js/garak-v3.js','/assets/js/commerce-bridge-v6.js','/recipes/index.html','/community/index.html','/assets/images/hero-market.webp'];
self.addEventListener('install',event=>event.waitUntil(caches.open(CACHE).then(cache=>cache.addAll(ASSETS))));
self.addEventListener('activate',event=>event.waitUntil(caches.keys().then(keys=>Promise.all(keys.filter(key=>key!==CACHE).map(key=>caches.delete(key))))));
self.addEventListener('fetch',event=>{
 const req=event.request;
 if(req.method!=='GET')return;
 const url=new URL(req.url);
 if(url.origin!==self.location.origin || url.pathname.startsWith('/api/') || url.pathname.startsWith('/admin/') || url.pathname.includes('account') || url.pathname.includes('checkout'))return;
 if(!ASSETS.includes(url.pathname))return;
 event.respondWith(fetch(req,{cache:'no-store'}).catch(()=>caches.match(req)));
});
