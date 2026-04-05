# -*- coding: utf-8 -*-
"""Google News RSS（公开聚合，延迟与覆盖面因地区而异；非投资建议）。"""
from __future__ import annotations

import urllib.parse
from typing import Any


def fetch_google_news_headlines(query: str, max_items: int = 12) -> list[dict[str, Any]]:
    q = (query or "").strip()
    if not q:
        return []
    try:
        import feedparser
    except ImportError:
        return []

    encoded = urllib.parse.quote(q)
    url = f"https://news.google.com/rss/search?q={encoded}&hl=zh-CN&gl=CN&ceid=CN:zh-Hans"
    feed = feedparser.parse(url)
    out: list[dict[str, Any]] = []
    for e in (feed.entries or [])[:max_items]:
        src = e.get("source")
        if isinstance(src, dict):
            st = src.get("title")
        else:
            st = getattr(src, "title", None) if src else None
        out.append(
            {
                "title": e.get("title"),
                "source": st,
                "link": e.get("link"),
                "published": e.get("published"),
            }
        )
    return out


def news_block_for_llm(symbol: str, long_name: str | None) -> str:
    parts: list[str] = []
    q1 = f"{symbol} 股票"
    q2 = (long_name or "").strip() or symbol
    for label, q in (("代码相关", q1), ("公司名相关", f"{q2} 股价")):
        items = fetch_google_news_headlines(q, max_items=8)
        parts.append(f"### RSS 查询：{label} ({q})\n")
        if not items:
            parts.append("（无条目或拉取失败）\n")
            continue
        for it in items:
            t = it.get("title") or ""
            s = it.get("source") or ""
            parts.append(f"- {t} [{s}]\n")
    return "".join(parts)
