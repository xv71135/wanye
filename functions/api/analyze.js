/**
 * POST /api/analyze — edge proxy to VPS FastAPI (same-origin from the HTTPS page).
 *
 * Do NOT use resolveOverride with a raw IP; Cloudflare requires a hostname in your zone.
 * Order: try bare IP first, then vps-api hostname (grey-cloud A record).
 *
 * Optional: Pages project → Settings → Environment variables:
 *   VPS_ANALYZE_BASES = http://139.199.212.59:8788,http://vps-api.3737-k.info:8788
 * (no trailing slashes; overrides defaults)
 */
const VPS_IP = "139.199.212.59";
const VPS_HOST = "vps-api.3737-k.info";
const VPS_PORT = 8788;

function defaultBases() {
  return [`http://${VPS_IP}:${VPS_PORT}`, `http://${VPS_HOST}:${VPS_PORT}`];
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
  if (res.status >= 502 && res.status <= 530) return true;
  return looksLikeCf1016(text);
}

export async function onRequestPost({ request, env }) {
  const body = await request.text();
  const hdr = new Headers();
  hdr.set("Content-Type", "application/json");
  const tok = request.headers.get("X-Demo-Token");
  if (tok) hdr.set("X-Demo-Token", tok);

  const hint =
    "边缘无法连上 VPS。请确认：1) 腾讯云安全组放行 8788；2) systemd 中 uvicorn 监听 0.0.0.0:8788；3) 浏览器打开 https://你的域名/api/health 看边缘探测结果；4) 若仍失败，在 VPS 上配置 HTTPS（Nginx 证书）后，于页面 head 增加 meta stock-analyst-api-direct 指向 https API 根地址，浏览器将直连 API、绕过本转发。";

  let last = { text: JSON.stringify({ detail: "all backends failed", hint }), status: 502 };

  for (const base of getBases(env)) {
    try {
      const res = await fetch(`${base}/analyze`, {
        method: "POST",
        headers: hdr,
        body,
      });
      const text = await res.text();
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
