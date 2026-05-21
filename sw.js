// 秒投 Service Worker — 离线缓存
const CACHE = 'miaotou-v3';
const SHELL = [
  '/',
  '/index.html',
  '/resume.html',
  '/manifest.webmanifest',
  '/icons/icon-192.png',
  '/icons/icon-512.png',
  'https://unpkg.com/leaflet@1.9.4/dist/leaflet.css',
  'https://unpkg.com/leaflet@1.9.4/dist/leaflet.js',
];

self.addEventListener('install', e => {
  e.waitUntil(
    caches.open(CACHE)
      .then(c => c.addAll(SHELL).catch(() => {}))
      .then(() => self.skipWaiting())
  );
});

self.addEventListener('activate', e => {
  e.waitUntil(
    caches.keys()
      .then(keys => Promise.all(keys.filter(k => k !== CACHE).map(k => caches.delete(k))))
      .then(() => self.clients.claim())
  );
});

self.addEventListener('fetch', e => {
  const req = e.request;
  if (req.method !== 'GET') return;

  // version.json：始终走网络，确保能检测到新一轮更新
  if (req.url.includes('version.json')) {
    e.respondWith(fetch(req).catch(() => caches.match(req)));
    return;
  }

  // HTML 页面：网络优先（保证每天的数据是最新的），离线时回退缓存
  if (req.mode === 'navigate' || req.destination === 'document') {
    e.respondWith(
      fetch(req)
        .then(r => {
          const cp = r.clone();
          caches.open(CACHE).then(c => c.put(req, cp));
          return r;
        })
        .catch(() => caches.match(req).then(r => r || caches.match('/index.html')))
    );
    return;
  }

  // 其他静态资源：缓存优先
  e.respondWith(
    caches.match(req).then(cached => {
      if (cached) return cached;
      return fetch(req).then(resp => {
        if (resp && resp.ok) {
          const cp = resp.clone();
          caches.open(CACHE).then(c => c.put(req, cp));
        }
        return resp;
      }).catch(() => cached);
    })
  );
});
