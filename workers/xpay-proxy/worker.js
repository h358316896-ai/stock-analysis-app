// XORPay API CORS Proxy Worker
// 前端直调此 Worker → Worker 从中国边缘节点转发到 XORPay
// Cloudflare 边缘节点在中国有 IP，能绕开 XORPay 的 geo-blocking
export default {
  async fetch(request) {
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

    if (request.method !== 'POST') {
      return new Response(JSON.stringify({ status: 'error', info: '仅支持 POST' }), {
        status: 405,
        headers: { 'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*' }
      });
    }

    // 从 URL 路径提取 XORPay AID (如 /705874)
    const url = new URL(request.url);
    const pathParts = url.pathname.replace(/^\/+/, '').split('/');
    const aid = pathParts[0] || '705874';
    const body = await request.text();

    try {
      const r = await fetch(`https://xorpay.com/api/pay/${aid}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
        body
      });

      const data = await r.json();

      return new Response(JSON.stringify(data), {
        headers: {
          'Content-Type': 'application/json; charset=utf-8',
          'Access-Control-Allow-Origin': '*',
          'Cache-Control': 'no-store',
        }
      });
    } catch (e) {
      return new Response(JSON.stringify({ status: 'error', info: 'Proxy error: ' + e.message }), {
        status: 502,
        headers: {
          'Content-Type': 'application/json',
          'Access-Control-Allow-Origin': '*',
        }
      });
    }
  }
};
