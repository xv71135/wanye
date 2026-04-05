/**
 * POST /api/analyze — edge proxy to VPS FastAPI (same-origin from the HTTPS page).
 *
 * Cloudflare 1016 often happens when the first hop uses a hostname that is missing
 * in DNS, orange-clouded (proxy + custom port), or otherwise not resolvable from the
 * edge. Mitigation:
 * 1) Try bare IP first (most reliable from Workers if the security group allows).
 * 2) For vps-api.3737-k.info (same zone as Pages), use cf.resolveOverride to connect
 *    to the VPS IP while keeping the correct Host header — bypasses broken public DNS.
 * 3) Last resort: hostname without override (works if grey-cloud A record is correct).
 *
 * DNS: A record vps-api.3737-k.info → VPS IP, DNS only (grey cloud) is still recommended.
 */
const VPS_IP = "139.199.212.59";
const VPS_HOST = "vps-api.3737-k.info";
const VPS_PORT = 8788;

/** @type {{ base: string, cf?: { resolveOverride: string } }[]} */
const BACKENDS = [
  { base: `http://${VPS_IP}:${VPS_PORT}` },
  { base: `http://${VPS_HOST}:${VPS_PORT}`, cf: { resolveOverride: VPS_IP } },
  { base: `http://${VPS_HOST}:${VPS_PORT}` },
];

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

export async function onRequestPost({ request }) {
  const body = await request.text();
  const hdr = new Headers();
  hdr.set("Content-Type", "application/json");
  const tok = request.headers.get("X-Demo-Token");
  if (tok) hdr.set("X-Demo-Token", tok);

  const hint =
    "边缘无法连上 VPS。请确认：1) 腾讯云安全组放行 8788 给公网；2) stock-analyst-api 在监听 0.0.0.0:8788；3) Cloudflare DNS 中 vps-api.3737-k.info 为灰云 A 记录指向 " +
    VPS_IP +
    "。";

  let last = { text: JSON.stringify({ detail: "all backends failed", hint }), status: 502 };

  for (const { base, cf } of BACKENDS) {
    try {
      const init = {
        method: "POST",
        headers: hdr,
        body,
        ...(cf ? { cf } : {}),
      };
      const res = await fetch(`${base}/analyze`, init);
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
    } catch {
      /* try next */
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
