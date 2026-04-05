# -*- coding: utf-8 -*-
from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from typing import Any


def normalize_symbol(raw: str) -> str:
    s = (raw or "").strip().upper()
    if not s:
        return ""
    if re.fullmatch(r"\d{6}", s):
        return f"{s}.SS" if s.startswith("6") else f"{s}.SZ"
    if "." in s:
        return s
    return s


def _safe_num(x: Any) -> Any:
    if x is None:
        return None
    try:
        if hasattr(x, "item"):
            return float(x.item())
        return float(x)
    except (TypeError, ValueError):
        return str(x)


def fetch_market_context(symbol: str) -> dict[str, Any]:
    sym = normalize_symbol(symbol)
    out: dict[str, Any] = {
        "symbol_requested": symbol,
        "symbol_yfinance": sym,
        "fetched_at_utc": datetime.now(timezone.utc).isoformat(),
        "ok": False,
        "error": None,
        "info": {},
        "recent_price_stats": {},
        "yfinance_news": [],
    }
    if not sym:
        out["error"] = "empty_symbol"
        return out

    try:
        import yfinance as yf
    except ImportError:
        out["error"] = "yfinance_not_installed"
        return out

    try:
        t = yf.Ticker(sym)
        info = t.info or {}
        keys = (
            "longName",
            "shortName",
            "symbol",
            "exchange",
            "currency",
            "quoteType",
            "sector",
            "industry",
            "marketCap",
            "trailingPE",
            "forwardPE",
            "priceToBook",
            "dividendYield",
            "fiftyTwoWeekHigh",
            "fiftyTwoWeekLow",
            "averageVolume",
        )
        out["info"] = {k: info.get(k) for k in keys if info.get(k) is not None}

        hist = t.history(period="3mo")
        if hist is not None and len(hist) > 0:
            last = hist.iloc[-1]
            first = hist.iloc[0]
            out["recent_price_stats"] = {
                "period": "3mo",
                "last_close": _safe_num(last.get("Close")),
                "last_date": str(hist.index[-1])[:10],
                "period_start_close": _safe_num(first.get("Close")),
                "high_3m": _safe_num(hist["High"].max()),
                "low_3m": _safe_num(hist["Low"].min()),
                "volume_last": _safe_num(last.get("Volume")),
            }
        else:
            out["recent_price_stats"] = {"note": "no_history_rows"}

        raw_news = getattr(t, "news", None) or []
        if isinstance(raw_news, list):
            for item in raw_news[:15]:
                if not isinstance(item, dict):
                    continue
                out["yfinance_news"].append(
                    {
                        "title": item.get("title"),
                        "publisher": item.get("publisher"),
                        "link": item.get("link"),
                    }
                )

        out["ok"] = True
    except Exception as e:
        out["error"] = f"{type(e).__name__}: {e}"

    return out
