/**
 * GET /api/health — edge probe of VPS FastAPI /health (no auth).
 * Use in browser: https://3737-k.info/api/health
 *
 * Env VPS_ANALYZE_BASES — same as analyze.js (comma-separated base URLs).
 */
const API_PUBLIC_HTTPS = "https://api.3737-k.info";
const VPS_IP = "139.199.212.59";
const VPS_HOST = "vps-api.3737-k.info";
const VPS_PORT = 8788;

function defaultBases() {
  return [
    API_PUBLIC_HTTPS,
    `http://${VPS_IP}:${VPS_PORT}`,
    `http://${VPS_HOST}:${VPS_PORT}`,
  ];
}

/** @param {Record<string, unknown> | undefined} env */
function getBases(env) {
  const raw = typeof env?.VPS_ANALYZE_BASES === "string" ? env.VPS_ANALYZE_BASES.trim() : "";
  if (raw) {
    const list = raw
      .split(",")
      .map((s) => s.trim().replace(/\/$/, ""))
      .filter(Boolean);
    if (list.length) return list;
  }
  return defaultBases();
}

export async function onRequestGet({ env }) {
  const bases = getBases(env);
  const results = [];

  for (const base of bases) {
    try {
      const res = await fetch(`${base}/health`, { method: "GET" });
      const text = await res.text();
      let json = null;
      try {
        json = JSON.parse(text);
      } catch {
        /* keep raw */
      }
      results.push({
        base,
        ok: res.ok,
        status: res.status,
        health: json ?? { raw: text.slice(0, 500) },
      });
    } catch (e) {
      results.push({
        base,
        ok: false,
        error: String((e && e.message) || e),
      });
    }
  }

  const anyOk = results.some((r) => r.ok);
  const payload = {
    edge_probe_ok: anyOk,
    backends: results,
    hint: anyOk
      ? "至少一条后端可达；若股票页仍 502，多为分析耗时过长或 POST 被拦截，可考虑 meta stock-analyst-api-direct 走 HTTPS 直连 API。"
      : "全部后端失败：检查腾讯云防火墙 8788、VPS 上 systemctl status stock-analyst-api、本机 curl 公网 IP:8788/health。",
  };

  // 始终返回 200 + JSON。若用 HTTP 502，部分情况下 Cloudflare 会把响应替换成通用 HTML 错误页，用户看不到探测明细。
  return new Response(JSON.stringify(payload, null, 2), {
    status: 200,
    headers: {
      "Content-Type": "application/json; charset=utf-8",
      "Access-Control-Allow-Origin": "*",
      "Cache-Control": "no-store",
    },
  });
}

export async function onRequestOptions() {
  return new Response(null, {
    status: 204,
    headers: {
      "Access-Control-Allow-Origin": "*",
      "Access-Control-Allow-Methods": "GET, OPTIONS",
      "Access-Control-Allow-Headers": "Content-Type",
      "Access-Control-Max-Age": "86400",
    },
  });
}
