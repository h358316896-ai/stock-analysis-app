// Cloudflare Pages Function — XORPay API Proxy
// URL: /xpay-proxy/:aid  (e.g., POST /xpay-proxy/705874)
// 前端直调此接口 → Pages Function 从中国边缘节点调 XORPay → 返回结果 + CORS 头

export async function onRequest(context) {
  const { request, params } = context;
  const aid = params.aid || '705874';

  // CORS preflight
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
    return new Response('Method Not Allowed', { status: 405 });
  }

  // 读取前端发来的 XORPay 表单参数
  const body = await request.text();

  try {
    // 从中国边缘节点调 XORPay API（不受 geo-blocking 影响）
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
    return new Response(JSON.stringify({
      status: 'error',
      info: 'Pages proxy error: ' + e.message
    }), {
      status: 502,
      headers: {
        'Content-Type': 'application/json',
        'Access-Control-Allow-Origin': '*',
      }
    });
  }
}
