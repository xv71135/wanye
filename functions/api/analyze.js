/**
 * POST /api/analyze — edge proxy to VPS FastAPI (browser calls same-origin /api only).
 *
 * Prefer HTTPS API host (443) first — Cloudflare edge often cannot reach http://IP:8788 (1016),
 * and browser direct to api.* triggers CORS / network quirks → Failed to fetch.
 *
 * Optional env VPS_ANALYZE_BASES = comma-separated bases, no trailing slash.
 */
const API_PUBLIC_HTTPS = "https://api.3737-k.info";
// Workers 对裸 IP 的 fetch 常返回 1016，勿再默认回源 http://IP。
const HINT_SSL =
  "525：Cloudflare 橙云与源站证书/SSL 模式不匹配。将 api 子域改为「DNS 仅」（灰云）并在 VPS 用 Let's Encrypt 配好 api 的 443；或保持橙云且源站证书域名匹配并把 SSL 设为「完全(严格)」。Pages 可设环境变量 VPS_ANALYZE_BASES 指向已可用的 HTTPS 源。";

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

function looksLikeCf1016(text) {
  return (
    text.includes("error code: 1016") ||
    text.includes("Error 1016") ||
    (text.includes("Cloudflare") && text.includes("1016"))
  );
}

function shouldRetry(res, text) {
  const ct = (res.headers.get("Content-Type") || "").toLowerCase();
  if (ct.includes("application/json")) return false;
  if (res.status === 525 || res.status === 526) return false;
  if (res.status >= 502 && res.status <= 530) return true;
  return looksLikeCf1016(text);
}

/** Turn CF HTML error pages into JSON so the stock page never shows raw 502 HTML. */
function jsonSslHelp(status) {
  return JSON.stringify({
    detail: `边缘回源失败（HTTP ${status}）。${HINT_SSL}`,
    hint: HINT_SSL,
  });
}

export async function onRequestPost({ request, env }) {
  const body = await request.text();
  const hdr = new Headers();
  hdr.set("Content-Type", "application/json");
  const tok = request.headers.get("X-Demo-Token");
  if (tok) hdr.set("X-Demo-Token", tok);

  const hint = HINT_SSL;

  let last = { text: JSON.stringify({ detail: "all backends failed", hint }), status: 502 };

  for (const base of getBases(env)) {
    try {
      const res = await fetch(`${base}/analyze`, {
        method: "POST",
        headers: hdr,
        body,
      });
      const text = await res.text();
      if (res.status === 525 || res.status === 526) {
        return new Response(jsonSslHelp(res.status), {
          status: 503,
          headers: {
            "Content-Type": "application/json; charset=utf-8",
            "Access-Control-Allow-Origin": "*",
          },
        });
      }
      if (!shouldRetry(res, text)) {
        return new Response(text, {
          status: res.status,
          headers: {
            "Content-Type": res.headers.get("Content-Type") || "application/json",
            "Access-Control-Allow-Origin": "*",
          },
        });
      }
      last = { text, status: res.status };
    } catch (e) {
      last = {
        text: JSON.stringify({
          detail: `fetch failed: ${String((e && e.message) || e)}`,
          hint,
          base,
        }),
        status: 502,
      };
    }
  }

  if (looksLikeCf1016(last.text)) {
    last = {
      text: JSON.stringify({
        detail: "Cloudflare 1016：边缘到 VPS 的 DNS/连接失败。",
        hint,
      }),
      status: 502,
    };
  }

  return new Response(last.text, {
    status: last.status,
    headers: {
      "Content-Type": last.text.trim().startsWith("{") ? "application/json" : "text/plain",
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
