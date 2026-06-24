// ============================================================
// XORPay API Proxy — Cloudflare Worker
// 部署到 Cloudflare Workers 后替换下面的 WORKER_URL
// ============================================================
//
// 部署步骤:
// 1. 打开 https://dash.cloudflare.com → Workers & Pages → 创建 Worker
// 2. 把这段代码粘贴进去，点「部署」
// 3. 把 worker 的 URL (如 xpay-proxy.xxx.workers.dev) 填入下面的 WORKER_URL
// 4. 在 Cloudflare Worker 设置里添加路由: kunhuang.top/xpay-proxy/*
//
// 原理: Worker 运行在 Cloudflare 中国边缘节点，能正常调通 XORPay API
// ============================================================

export default {
  async fetch(request) {
    // CORS 预检
    if (request.method === 'OPTIONS') {
      return new Response(null, {
        headers: {
          'Access-Control-Allow-Origin': '*',
          'Access-Control-Allow-Methods': 'POST, OPTIONS',
          'Access-Control-Allow-Headers': 'Content-Type',
          'Access-Control-Max-Age': '86400',
        }
      });
    }

    // 只允许 POST
    if (request.method !== 'POST') {
      return new Response('Method Not Allowed', { status: 405 });
    }

    // 从 URL search params 获取 XORPay AID (格式: /705874)
    const url = new URL(request.url);
    const aid = url.pathname.split('/').pop() || '705874';
    const body = await request.text();

    // 转发到 XORPay API
    const xorpayUrl = `https://xorpay.com/api/pay/${aid}`;

    try {
      const response = await fetch(xorpayUrl, {
        method: 'POST',
        headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
        body: body
      });

      const data = await response.json();

      return new Response(JSON.stringify(data), {
        status: 200,
        headers: {
          'Content-Type': 'application/json; charset=utf-8',
          'Access-Control-Allow-Origin': '*',
          'Cache-Control': 'no-store',
        }
      });
    } catch (e) {
      return new Response(JSON.stringify({
        status: 'error',
        info: 'Worker proxy error: ' + e.message
      }), {
        status: 502,
        headers: {
          'Content-Type': 'application/json',
          'Access-Control-Allow-Origin': '*',
        }
      });
    }
  }
};
