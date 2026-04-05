/**
 * POST /api/analyze — 服务端转发到 VPS 上的 FastAPI，避免 https 页面请求 http API 被浏览器拦截。
 * 修改 BACKEND 时只改此处。
 */
const BACKEND = "http://139.199.212.59:8788";

export async function onRequestPost({ request }) {
  const body = await request.text();
  const hdr = new Headers();
  hdr.set("Content-Type", "application/json");
  const tok = request.headers.get("X-Demo-Token");
  if (tok) hdr.set("X-Demo-Token", tok);

  const res = await fetch(`${BACKEND}/analyze`, {
    method: "POST",
    headers: hdr,
    body,
  });

  const out = await res.text();
  return new Response(out, {
    status: res.status,
    headers: {
      "Content-Type": res.headers.get("Content-Type") || "application/json",
      "Access-Control-Allow-Origin": "*",
    },
  });
}

export async function onRequestOptions() {
  return new Response(null, {
    status: 204,
    headers: {
      "Access-Control-Allow-Origin": "*",
      "Access-Control-Allow-Methods": "POST, OPTIONS",
      "Access-Control-Allow-Headers": "Content-Type, X-Demo-Token",
      "Access-Control-Max-Age": "86400",
    },
  });
}
