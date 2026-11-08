/* Cache only public lab shell; authenticated API, HTML state, tokens and order data are NEVER cached. */
"use strict";
const CACHE="garak-order-lab-ui-v1";
const ASSETS=["/order-lab/app.css","/order-lab/app.js","/order-lab/index.html"];
self.addEventListener("install",event=>{
  event.waitUntil(caches.open(CACHE).then(cache=>cache.addAll(ASSETS)).then(()=>self.skipWaiting()));
});
self.addEventListener("activate",event=>{
  event.waitUntil(caches.keys().then(keys=>Promise.all(keys.filter(k=>k!==CACHE).map(k=>caches.delete(k)))).then(()=>self.clients.claim()));
});
self.addEventListener("fetch",event=>{
  if(event.request.method!=="GET")return;
  const url=new URL(event.request.url);
  if(url.origin!==self.location.origin||!ASSETS.includes(url.pathname))return;
  event.respondWith(fetch(event.request).then(resp=>{
    if(resp.ok&&resp.type==="basic"){const copy=resp.clone();caches.open(CACHE).then(cache=>cache.put(event.request,copy))}
    return resp;
  }).catch(()=>caches.match(event.request)));
});
