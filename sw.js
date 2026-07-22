// StockAI Service Worker — API proxy to ECS
const ECS = "http://47.97.66.164";

self.addEventListener("install", () => self.skipWaiting());
self.addEventListener("activate", (e) => {
  e.waitUntil(self.clients.claim());
});

self.addEventListener("fetch", (e) => {
  const url = new URL(e.request.url);
  if (url.pathname.startsWith("/api/") || url.pathname === "/health") {
    e.respondWith(
      fetch(ECS + url.pathname + url.search, {
        method: e.request.method,
        headers: e.request.headers,
        body: e.request.method !== "GET" && e.request.method !== "HEAD"
          ? e.request.clone().arrayBuffer() : undefined,
      }).catch(() => new Response(
        JSON.stringify({ error: "网络不可用" }),
        { status: 503, headers: { "Content-Type": "application/json" } }
      ))
    );
  }
});
