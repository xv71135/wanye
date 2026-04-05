/**
 * POST /api/analyze — 边缘转发到 VPS FastAPI（HTTPS 页同源请求，无混合内容）。
 * 勿用裸 IP：Cloudflare 边缘 fetch 裸 IP 易出现 Error 1016（Origin DNS）。
 * 请在 Cloudflare DNS 添加 A 记录：vps-api.3737-k.info → 服务器 IP，且关闭代理（仅 DNS，灰云）。
 */
const BACKEND = "http://vps-api.3737-k.info:8788";

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
