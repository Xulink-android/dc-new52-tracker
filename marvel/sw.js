const CACHE='marvel-tracker-audit-v3';
const FILES=['./','./index.html','./catalog.js','./manifest.webmanifest','./icon.svg','./icon-192.png','./icon-512.png'];
self.addEventListener('install',e=>e.waitUntil(caches.open(CACHE).then(c=>c.addAll(FILES)).then(()=>self.skipWaiting())));
self.addEventListener('activate',e=>e.waitUntil(caches.keys().then(keys=>Promise.all(keys.filter(k=>k!==CACHE).map(k=>caches.delete(k)))).then(()=>self.clients.claim())));
self.addEventListener('fetch',e=>{const r=e.request;if(r.method!=='GET'||new URL(r.url).origin!==self.location.origin)return;if(r.mode==='navigate'){e.respondWith(fetch(r).then(response=>{if(response.ok){const copy=response.clone();caches.open(CACHE).then(c=>c.put(r,copy))}return response}).catch(()=>caches.match(r).then(x=>x||caches.match('./index.html'))));return}e.respondWith(caches.match(r).then(x=>x||fetch(r).then(response=>{if(response.ok){const copy=response.clone();caches.open(CACHE).then(c=>c.put(r,copy))}return response})))});
