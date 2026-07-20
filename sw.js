// StockAI PWA Service Worker — 离线支持 + API代理
const CACHE_STATIC = 'stockai-static-v5';
const CACHE_API = 'stockai-api-v5';
const CACHE_PAGES = 'stockai-pages-v5';

// ECS backend IP for API proxying
const API_ORIGIN = 'http://47.97.66.164';

// 安装时预缓存核心资源
const PRECACHE = [
  '/', '/stock', '/media', '/services',
  '/manifest.json', '/sw.js',
  '/css/style.css'
];

self.addEventListener('install', (e) => {
  console.log('[SW] Installing...');
  e.waitUntil(
    caches.open(CACHE_STATIC).then(cache => {
      return Promise.allSettled(PRECACHE.map(url =>
        cache.add(url).catch(err => console.warn('[SW] Precache failed:', url, err))
      ));
    }).then(() => self.skipWaiting())
  );
});

// 激活时清理旧缓存
self.addEventListener('activate', (e) => {
  console.log('[SW] Activating...');
  e.waitUntil(
    caches.keys().then(keys => Promise.all(
      keys.filter(k => k.startsWith('stockai-') && k !== CACHE_STATIC && k !== CACHE_API && k !== CACHE_PAGES)
        .map(k => caches.delete(k))
    )).then(() => self.clients.claim())
  );
});

// API请求代理到ECS后端（绕过GFW域名阻断）
async function apiProxy(request) {
  const url = new URL(request.url);
  const apiUrl = API_ORIGIN + url.pathname + url.search;

  console.log('[SW] Proxying API:', apiUrl);

  try {
    // 构造新的请求，保留原始headers和body
    const proxyRequest = new Request(apiUrl, {
      method: request.method,
      headers: request.headers,
      body: request.method !== 'GET' && request.method !== 'HEAD' ? await request.clone().blob() : undefined,
      mode: 'cors',
      credentials: 'include',
    });

    const response = await fetch(proxyRequest);
    if (response.ok) {
      // 缓存成功的响应
      const cache = await caches.open(CACHE_API);
      cache.put(request, response.clone());
    }
    return response;
  } catch (err) {
    console.warn('[SW] API proxy failed, trying cache:', err);
    const cached = await caches.match(request);
    if (cached) return cached;
    return new Response(JSON.stringify({ error: '网络不可用' }), {
      status: 503,
      headers: { 'Content-Type': 'application/json' }
    });
  }
}

// 请求拦截：分级缓存策略
self.addEventListener('fetch', (e) => {
  const url = new URL(e.request.url);

  // 跳过非 GET 请求（POST/PUT等API由页面直接调用）
  if (e.request.method !== 'GET') {
    // 对于 API 的 POST/PUT 请求，也代理到 ECS
    if (url.pathname.startsWith('/api/')) {
      e.respondWith(apiProxy(e.request));
      return;
    }
    return;
  }

  // API 请求：代理到 ECS 后端
  if (url.pathname.startsWith('/api/')) {
    e.respondWith(apiProxy(e.request));
    return;
  }

  // 页面请求：网络优先 → 离线回退页
  if (url.pathname === '/' || url.pathname.startsWith('/stock') ||
      url.pathname.startsWith('/media') || url.pathname.startsWith('/services')) {
    e.respondWith(
      fetch(e.request).then(response => {
        const clone = response.clone();
        caches.open(CACHE_PAGES).then(c => c.put(e.request, clone));
        return response;
      }).catch(() =>
        caches.match(e.request).then(cached => cached || caches.match('/'))
      )
    );
    return;
  }

  // 静态资源 (CSS/JS/图片/字体)：缓存优先 → 网络更新
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

// 推送通知
self.addEventListener('push', (e) => {
  const data = e.data ? e.data.json() : {};
  e.waitUntil(
    self.registration.showNotification(data.title || 'StockAI', {
      body: data.body || '有新的行情异动',
      icon: '/static/icon-192.png',
      badge: '/static/icon-192.png',
      vibrate: [200, 100, 200],
      data: { url: data.url || '/stock' },
      actions: [{ action: 'open', title: '查看' }, { action: 'close', title: '关闭' }]
    })
  );
});

self.addEventListener('notificationclick', (e) => {
  e.notification.close();
  if (e.action !== 'close') {
    e.waitUntil(clients.openWindow(e.notification.data.url || '/stock'));
  }
});
