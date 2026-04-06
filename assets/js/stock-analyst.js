(function () {
  "use strict";

  function apiBase() {
    var directEl = document.querySelector('meta[name="stock-analyst-api-direct"]');
    var direct = directEl && directEl.content ? directEl.content.trim().replace(/\/$/, "") : "";
    if (direct) {
      if (typeof location !== "undefined" && location.protocol === "https:" && direct.indexOf("http:") === 0) {
        console.warn(
          "[stock-analyst] stock-analyst-api-direct 使用 http 在 https 页面会被浏览器拦截；请改为 https API 或删除该 meta 以使用同源 /api。"
        );
      }
      return direct;
    }
    var meta = document.querySelector('meta[name="stock-analyst-api-base"]');
    var fromMeta = meta && meta.content ? meta.content.trim() : "";
    if (fromMeta) return fromMeta.replace(/\/$/, "");
    if (typeof window.STOCK_ANALYST_API_BASE === "string" && window.STOCK_ANALYST_API_BASE.trim())
      return window.STOCK_ANALYST_API_BASE.trim().replace(/\/$/, "");
    return "";
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
    var base = apiBase();
    var symbol = (document.getElementById("sa-symbol").value || "").trim();
    var question = (document.getElementById("sa-question").value || "").trim();
    var out = document.getElementById("sa-output");

    if (!base) {
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
      var res = await fetch(base + "/analyze", {
        method: "POST",
        mode: "cors",
        credentials: "omit",
        headers: { "Content-Type": "application/json", Accept: "application/json" },
        body: JSON.stringify({ symbol: symbol, question: question || null }),
      });

      var raw = await res.text();
      var data;
      try {
        data = JSON.parse(raw);
      } catch (_) {
        data = { detail: raw || "(empty response)" };
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

      out.textContent = data.report_markdown || "";
      setStatus(window.SA_MSG_DONE || "Done.", false);
    } catch (err) {
      var msg = String(err.message || err);
      if (msg === "Failed to fetch") {
        msg =
          "请求未到达服务器（Failed to fetch）。常见：① 跨域 CORS（API 须允许 https://3737-k.info）；② Nginx 默认约 60s 超时，流水线更长会被断开；③ 证书/网络。请更新 VPS 上 API 代码并重启，且在 Nginx location 中加 proxy_read_timeout 300s；";
      }
      setStatus(msg, true);
    } finally {
      setLoading(false);
    }
  });
})();
