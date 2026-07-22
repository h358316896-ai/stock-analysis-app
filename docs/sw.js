// StockAI Service Worker — API proxy to ECS + offline cache
const ECS = "http://47.97.66.164";
const CACHE_STATIC = "stockai-v8";
const RETRY_MAX = 2;

// --- Install & Activate ---
self.addEventListener("install", (e) => {
  e.waitUntil(self.skipWaiting());
});
self.addEventListener("activate", (e) => {
  e.waitUntil(
    caches.keys().then((keys) =>
      Promise.all(keys.filter((k) => k !== CACHE_STATIC).map((k) => caches.delete(k)))
    ).then(() => self.clients.claim())
  );
});

// --- API Proxy ---
async function proxyAPI(request) {
  const url = new URL(request.url);
  const target = ECS + url.pathname + url.search;

  for (let i = 0; i <= RETRY_MAX; i++) {
    try {
      const controller = new AbortController();
      const timer = setTimeout(() => controller.abort(), 10000);

      const proxyReq = new Request(target, {
        method: request.method,
        headers: request.headers,
        body: request.method !== "GET" && request.method !== "HEAD"
          ? await request.clone().arrayBuffer()
          : undefined,
        signal: controller.signal,
      });

      const response = await fetch(proxyReq);
      clearTimeout(timer);
      return response;
    } catch (err) {
      if (i === RETRY_MAX) {
        return new Response(
          JSON.stringify({ error: "网络不可用，请刷新重试" }),
          { status: 503, headers: { "Content-Type": "application/json" } }
        );
      }
      await new Promise((r) => setTimeout(r, 200));
    }
  }
}

// --- Fetch Handler ---
self.addEventListener("fetch", (e) => {
  const url = new URL(e.request.url);

  // API requests → proxy to ECS
  if (url.pathname.startsWith("/api/") || url.pathname === "/health") {
    e.respondWith(proxyAPI(e.request));
    return;
  }

  // Static assets → cache first
  if (e.request.method === "GET") {
    e.respondWith(
      caches.match(e.request).then((cached) => {
        const fetched = fetch(e.request).then((response) => {
          if (response.ok) {
            const clone = response.clone();
            caches.open(CACHE_STATIC).then((c) => c.put(e.request, clone));
          }
          return response;
        });
        return cached || fetched;
      })
    );
  }
});
