(function () {
  "use strict";

  function apiBase() {
    var meta = document.querySelector('meta[name="stock-analyst-api-base"]');
    var fromMeta = meta && meta.content ? meta.content.trim() : "";
    if (fromMeta) return fromMeta.replace(/\/$/, "");
    if (typeof window.STOCK_ANALYST_API_BASE === "string" && window.STOCK_ANALYST_API_BASE.trim())
      return window.STOCK_ANALYST_API_BASE.trim().replace(/\/$/, "");
    return "";
  }

  function demoToken() {
    var el = document.getElementById("sa-demo-token");
    return el && el.value ? el.value.trim() : "";
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
      var headers = { "Content-Type": "application/json" };
      var tok = demoToken();
      if (tok) headers["X-Demo-Token"] = tok;

      var res = await fetch(base + "/analyze", {
        method: "POST",
        headers: headers,
        body: JSON.stringify({ symbol: symbol, question: question || null }),
      });

      var data;
      try {
        data = await res.json();
      } catch (_) {
        data = { detail: await res.text() };
      }

      if (!res.ok) {
        var err = data.detail || data.message || data;
        if (Array.isArray(err)) {
          err = err.map(function (x) { return x.msg || JSON.stringify(x); }).join("; ");
        }
        setStatus(String(err), true);
        return;
      }

      out.textContent = data.report_markdown || "";
      setStatus(window.SA_MSG_DONE || "Done.", false);
    } catch (err) {
      setStatus(String(err.message || err), true);
    } finally {
      setLoading(false);
    }
  });
})();
