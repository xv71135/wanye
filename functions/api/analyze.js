/**
 * POST /api/analyze — edge proxy to VPS FastAPI (same-origin from the HTTPS page).
 * Prefer hostname (avoids some edge cases with bare IP). If the response looks like
 * Cloudflare Error 1016 HTML or the request fails, retry the fallback origin.
 *
 * DNS: A record vps-api.3737-k.info → VPS IP, DNS only (grey cloud).
 */
const BACKENDS = [
  "http://vps-api.3737-k.info:8788",
  "http://139.199.212.59:8788",
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

  let last = { text: '{"detail":"all backends failed"}', status: 502 };

  for (const base of BACKENDS) {
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
    } catch {
      /* try next */
    }
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
