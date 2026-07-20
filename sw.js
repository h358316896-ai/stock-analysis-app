// StockAI PWA Service Worker — 离线缓存
const CACHE_STATIC = 'stockai-static-v6';
const CACHE_PAGES = 'stockai-pages-v6';

const PRECACHE = [
  '/', '/stock.html', '/media.html', '/services.html',
  '/manifest.json', '/css/style.css'
];

self.addEventListener('install', (e) => {
  console.log('[SW] Installing...');
  e.waitUntil(
    caches.open(CACHE_STATIC).then(cache =>
      Promise.allSettled(PRECACHE.map(url =>
        cache.add(url).catch(err => console.warn('[SW] Precache failed:', url, err))
      ))
    ).then(() => self.skipWaiting())
  );
});

self.addEventListener('activate', (e) => {
  console.log('[SW] Activating...');
  e.waitUntil(
    caches.keys().then(keys => Promise.all(
      keys.filter(k => k.startsWith('stockai-') && k !== CACHE_STATIC && k !== CACHE_PAGES)
        .map(k => caches.delete(k))
    )).then(() => self.clients.claim())
  );
});

self.addEventListener('fetch', (e) => {
  const url = new URL(e.request.url);
  if (e.request.method !== 'GET') return;

  // API 请求放行，Vercel rewrites 代理到 ECS
  if (url.pathname.startsWith('/api/')) return;

  // 静态资源：缓存优先
  e.respondWith(
    caches.match(e.request).then(cached => {
      const fetched = fetch(e.request).then(response => {
        if (response.ok) {
          const clone = response.clone();
          caches.open(CACHE_STATIC).then(c => c.put(e.request, clone));
        }
        return response;
      });
      return cached || fetched;
    })
  );
});
