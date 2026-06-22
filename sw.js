// StockAI PWA Service Worker — 离线支持 + 智能缓存
const CACHE_STATIC = 'stockai-static-v4';
const CACHE_API = 'stockai-api-v4';
const CACHE_PAGES = 'stockai-pages-v4';

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

// 请求拦截：分级缓存策略
self.addEventListener('fetch', (e) => {
  const url = new URL(e.request.url);

  // 跳过非 GET 请求
  if (e.request.method !== 'GET') return;

  // API 请求：网络优先 → 缓存回退（5分钟新鲜度）
  if (url.pathname.startsWith('/api/')) {
    e.respondWith(networkFirst(e.request, CACHE_API, 300));
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

// 网络优先策略
async function networkFirst(request, cacheName, maxAge) {
  try {
    const response = await fetch(request);
    if (response.ok) {
      const clone = response.clone();
      const cache = await caches.open(cacheName);
      // 存储时记录时间戳
      await cache.put(request, clone);
      // 将时间戳存储到单独的条目
      const meta = await cache.put(
        new Request(request.url + '::meta'),
        new Response(JSON.stringify({ cachedAt: Date.now() }))
      );
    }
    return response;
  } catch (err) {
    // 网络失败 → 检查缓存是否在有效期内
    const cached = await caches.match(request);
    if (cached) {
      const metaReq = new Request(request.url + '::meta');
      const metaRes = await caches.match(metaReq);
      if (metaRes) {
        try {
          const meta = await metaRes.json();
          if (Date.now() - meta.cachedAt < maxAge * 1000) {
            return cached;
          }
        } catch (e) {}
      }
      return cached; // 即使过期也返回，比什么都没有好
    }
    throw err;
  }
}

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
