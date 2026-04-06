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
          });
        } catch (e) {
          lastErr = String((e && e.message) || e || "Failed to fetch");
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
          if ((/^[\s]*<!DOCTYPE/i.test(preview) || /cf-error-details|cloudflare/i.test(preview)) && i < bases.length - 1) {
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
          err =
            "网关 502：若走同源 /api，多为 Cloudflare Function 转发超时（分析常超 1～2 分钟）。页面已优先 stock-analyst-api-direct 直连 https://api；请硬刷新。仍 502 时查 VPS Nginx proxy_read_timeout 与 API 日志。";
        }
        if (data.hint) err = err + " " + String(data.hint);
        setStatus(err, true);
        return;
      }

      await typewriter(out, data.report_markdown || "", 85);
      setStatus(window.SA_MSG_DONE || "Done.", false);
    } catch (err) {
      var msg = String(err.message || err);
      if (msg === "Failed to fetch") {
        msg =
          "请求未到达服务器（Failed to fetch）。已尝试直连 API 与同源 /api 回退。请检查：1) https://api.3737-k.info/health 可访问；2) Nginx/防火墙；3) Pages 是否最新部署。";
      }
      setStatus(msg, true);
    } finally {
      setLoading(false);
    }
  });
})();
