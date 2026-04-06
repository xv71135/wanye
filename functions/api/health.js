/**
 * GET /api/health — edge probe of VPS FastAPI /health (no auth).
 * Use in browser: https://3737-k.info/api/health
 *
 * Env VPS_ANALYZE_BASES — same as analyze.js (comma-separated base URLs).
 */
const API_PUBLIC_HTTPS = "https://api.3737-k.info";

function defaultBases() {
  return [API_PUBLIC_HTTPS];
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
      const row = {
        base,
        ok: res.ok,
        status: res.status,
        health: json ?? { raw: text.slice(0, 500) },
      };
      if (res.status === 525 || res.status === 526) {
        row.hint =
          "525/526：Cloudflare 与源站 SSL 不匹配。将 api 子域改为 DNS 仅（灰云）+ VPS Let's Encrypt；或 SSL 完全(严格)+源站证书匹配。";
      }
      results.push(row);
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
      : "全部后端失败：若 status 为 525，按各 base 的 hint 调整 Cloudflare SSL/DNS；另查 VPS systemctl status stock-analyst-api、Nginx 反代、防火墙。",
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
