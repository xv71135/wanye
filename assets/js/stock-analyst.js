(function () {
  "use strict";

  function sleep(ms) {
    return new Promise(function (resolve) { setTimeout(resolve, ms); });
  }

  async function typewriter(el, text, cps) {
    if (!el) return;
    var full = String(text || "");
    var speed = Math.max(10, Number(cps) || 75);
    var chunk = full.length > 1200 ? 3 : 1;
    el.classList.add("sa-output--typing");
    el.textContent = "";
    for (var i = 0; i < full.length; i += chunk) {
      el.textContent += full.slice(i, i + chunk);
      await sleep(1000 / speed);
    }
    el.classList.remove("sa-output--typing");
  }

  function analyzeTimeoutMs() {
    return 120000;
  }

  /** @returns {AbortSignal|undefined} */
  function analyzeFetchSignal() {
    var ms = analyzeTimeoutMs();
    if (typeof AbortSignal !== "undefined" && typeof AbortSignal.timeout === "function") {
      return AbortSignal.timeout(ms);
    }
    var c = new AbortController();
    setTimeout(function () {
      try {
        c.abort();
      } catch (_e) {}
    }, ms);
    return c.signal;
  }

  function looksLike525Body(s) {
    var t = String(s || "");
    return /\b525\b/.test(t) && (/cloudflare/i.test(t) || /ssl/i.test(t) || /handshake/i.test(t));
  }

  function apiBases() {
    var bases = [];
    var directEl = document.querySelector('meta[name="stock-analyst-api-direct"]');
    var direct = directEl && directEl.content ? directEl.content.trim().replace(/\/$/, "") : "";
    if (direct) {
      if (typeof location !== "undefined" && location.protocol === "https:" && direct.indexOf("http:") === 0) {
        console.warn(
          "[stock-analyst] stock-analyst-api-direct 使用 http 在 https 页面会被浏览器拦截；请改为 https API 或删除该 meta 以使用同源 /api。"
        );
      }
      bases.push(direct);
    }
    var meta = document.querySelector('meta[name="stock-analyst-api-base"]');
    var fromMeta = meta && meta.content ? meta.content.trim() : "";
    if (fromMeta) bases.push(fromMeta.replace(/\/$/, ""));
    if (typeof window.STOCK_ANALYST_API_BASE === "string" && window.STOCK_ANALYST_API_BASE.trim()) {
      bases.push(window.STOCK_ANALYST_API_BASE.trim().replace(/\/$/, ""));
    }
    return bases.filter(function (v, i, arr) { return v && arr.indexOf(v) === i; });
  }

  function setStatus(msg, isErr) {
    var el = document.getElementById("sa-status");
    if (!el) return;
    el.textContent = msg || "";
    el.className = "sa-status" + (isErr ? " sa-status--err" : "");
  }

  function setLoading(on) {
    var btn = document.getElementById("sa-submit");
    if (btn) btn.disabled = !!on;
  }

  document.getElementById("sa-form").addEventListener("submit", async function (e) {
    e.preventDefault();
    var bases = apiBases();
    var symbol = (document.getElementById("sa-symbol").value || "").trim();
    var question = (document.getElementById("sa-question").value || "").trim();
    var out = document.getElementById("sa-output");

    if (!bases.length) {
      setStatus(window.SA_MSG_NO_API || "Configure API base URL (meta stock-analyst-api-base).", true);
      return;
    }
    if (!symbol) {
      setStatus(window.SA_MSG_NO_SYMBOL || "Enter a symbol.", true);
      return;
    }

    setLoading(true);
    setStatus(window.SA_MSG_LOADING || "Running pipeline…", false);
    out.textContent = "";

    try {
      var res = null;
      var raw = "";
      var data = null;
      var lastErr = "";
      for (var i = 0; i < bases.length; i++) {
        var base = bases[i];
        try {
          res = await fetch(base + "/analyze", {
            method: "POST",
            mode: "cors",
            credentials: "omit",
            headers: { "Content-Type": "application/json", Accept: "application/json" },
            body: JSON.stringify({ symbol: symbol, question: question || null }),
            signal: analyzeFetchSignal(),
          });
        } catch (e) {
          lastErr = String((e && e.message) || e || "Failed to fetch");
          if (/aborted|AbortError|timeout/i.test(lastErr)) {
            lastErr =
              "请求在 " +
              analyzeTimeoutMs() / 1000 +
              " 秒内未完成。若经同源 /api，边缘子请求可能更短；请优先修复直连 https://api 的可达性，并检查 Nginx proxy_read_timeout。";
          }
          continue;
        }

        raw = await res.text();
        try {
          data = JSON.parse(raw);
        } catch (_) {
          data = { detail: raw || "(empty response)" };
        }

        // If direct path fails at network level or returns gateway HTML, try fallback base.
        if (!res.ok) {
          var preview = String((data && (data.detail || data.message)) || raw || "");
          var isCfHtml =
            /^[\s]*<!DOCTYPE/i.test(preview) || /cf-error-details|cloudflare/i.test(preview);
          if (isCfHtml && i < bases.length - 1) {
            continue;
          }
        }
        break;
      }

      if (!res) {
        throw new Error(lastErr || "Failed to fetch");
      }

      if (!res.ok) {
        var err = data.detail || data.message || data;
        if (Array.isArray(err)) {
          err = err.map(function (x) { return x.msg || JSON.stringify(x); }).join("; ");
        }
        err = String(err);
        if (/^[\s]*<!DOCTYPE/i.test(err) || /cf-error-details|cloudflare/i.test(err)) {
          if (looksLike525Body(err) || res.status === 525 || res.status === 526) {
            err =
              "HTTPS 525/526：api 子域经 Cloudflare 橙云时与源站证书不匹配。请在 Cloudflare 将 api 的 A 记录改为「仅限 DNS」（灰云），在 VPS 用 certbot 为 api.3737-k.info 签发证书并配置 Nginx 443→127.0.0.1:8788；或保持橙云且把 SSL 设为「完全(严格)」并确保证书域名含 api。";
          } else {
            err =
              "网关错误（502/524 等）。同源 /api 受 Cloudflare Worker 子请求限制且回源失败时常返回 HTML。请打开 https://3737-k.info/api/health 看各 base 的 status；优先按 525 说明修复 https://api 的 SSL。";
          }
        }
        if (data.hint) {
          var hintStr = String(data.hint);
          if (err.indexOf(hintStr.slice(0, 28)) < 0) err = err + " " + hintStr;
        }
        setStatus(err, true);
        return;
      }

      await typewriter(out, data.report_markdown || "", 85);
      setStatus(window.SA_MSG_DONE || "Done.", false);
    } catch (err) {
      var msg = String(err.message || err);
      if (msg === "Failed to fetch" || /Failed to fetch/i.test(msg)) {
        msg =
          "请求未到达服务器（Failed to fetch）。请检查：1) 浏览器能否打开 https://api.3737-k.info/health；2) 若为 525，按页内说明将 api 改为 DNS 仅并配置证书；3) Cloudflare Pages 是否已重新部署。";
      }
      setStatus(msg, true);
    } finally {
      setLoading(false);
    }
  });
})();
