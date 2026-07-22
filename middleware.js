// Vercel Edge Middleware — API proxy to ECS with retry
const ECS_BASE = "http://47.97.66.164";
const MAX_RETRIES = 2;

export default async function middleware(request) {
  const url = new URL(request.url);

  // Only proxy /api/* and /health
  if (!url.pathname.startsWith("/api/") && url.pathname !== "/health") {
    return;
  }

  const targetURL = ECS_BASE + url.pathname + url.search;

  for (let attempt = 0; attempt <= MAX_RETRIES; attempt++) {
    try {
      const controller = new AbortController();
      const timeout = setTimeout(() => controller.abort(), 8000);

      const response = await fetch(targetURL, {
        method: request.method,
        headers: request.headers,
        body: request.method !== "GET" && request.method !== "HEAD"
          ? await request.clone().arrayBuffer()
          : undefined,
        signal: controller.signal,
      });

      clearTimeout(timeout);

      // Return successful response
      return new Response(response.body, {
        status: response.status,
        statusText: response.statusText,
        headers: response.headers,
      });
    } catch (err) {
      console.log(`ECS proxy attempt ${attempt + 1} failed: ${err.message}`);
      if (attempt === MAX_RETRIES) {
        return new Response(
          JSON.stringify({ error: "service temporarily unavailable" }),
          { status: 503, headers: { "Content-Type": "application/json" } }
        );
      }
      // Wait before retry
      await new Promise((r) => setTimeout(r, 300));
    }
  }
}

export const config = {
  matcher: ["/api/:path*", "/health"],
};
