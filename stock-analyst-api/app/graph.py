# -*- coding: utf-8 -*-
"""
LangGraph 流水线：拉数 → 校验 → 写稿 → 复核。
"""
from __future__ import annotations

import json
from typing import TypedDict

from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.graph import END, StateGraph

from app.config import MINIMAX_API_KEY
from app.llm_factory import get_chat_model
from app.news_rss import news_block_for_llm
from app.stock_tools import fetch_market_context


class AnalystState(TypedDict, total=False):
    symbol: str
    question: str | None
    market: dict
    news_block: str
    validation: str
    draft: str
    final: str


def _llm_text(system: str, user: str) -> str:
    llm = get_chat_model()
    msg = llm.invoke(
        [SystemMessage(content=system), HumanMessage(content=user)],
    )
    return (getattr(msg, "content", None) or "").strip()


def node_fetch(state: AnalystState) -> dict:
    symbol = state.get("symbol") or ""
    m = fetch_market_context(symbol)
    info = m.get("info") or {}
    long_name = info.get("longName") if isinstance(info, dict) else None
    nb = news_block_for_llm(symbol, long_name if isinstance(long_name, str) else None)
    yfn = m.get("yfinance_news") or []
    if isinstance(yfn, list) and yfn:
        lines = []
        for x in yfn:
            if isinstance(x, dict):
                lines.append(f"- {x.get('title')} [{x.get('publisher')}]")
        yf_text = "\n".join(lines)
    else:
        yf_text = "(yfinance 无新闻条目)"
    combined = f"【yfinance news】\n{yf_text}\n\n【Google News RSS 聚合】\n{nb}"
    return {"market": m, "news_block": combined}


def node_validate(state: AnalystState) -> dict:
    m = state.get("market") or {}
    payload = json.dumps(m, ensure_ascii=False, indent=2)
    sys = (
        "你是证券数据质检助手。根据工具 JSON 判断数据是否完整，列出可写研报的要点与缺失项。"
        "禁止编造数字。输出简短中文条目列表。"
    )
    user = (
        f"标的：{state.get('symbol')}\n\nJSON：\n{payload}\n\n"
        f"新闻素材长度：{len(state.get('news_block') or '')} 字符。"
    )
    return {"validation": _llm_text(sys, user)}


def node_draft(state: AnalystState) -> dict:
    sys = """你是证券研究助理。根据给定数据与新闻素材撰写中文 Markdown 研报。
必须：
1) 数据缺失处明确写「数据不可用」，禁止编造价格或财务数字。
2) 区分事实（来自 JSON）与推断。
3) 必须包含 ## 情绪与新闻 小节：综合 yfinance 新闻与 RSS 标题做中性概述，不得捏造行情。
4) 包含 ## 风险提示。
5) 文末 ## 免责声明：本内容由 AI 根据公开延迟信息生成，不构成投资建议。
结构建议：## 标的与数据概况 ## 基本面要点 ## 技术面与量价 ## 情绪与新闻 ## 情景与风险 ## 免责声明"""
    user = (
        f"标的用户输入：{state.get('symbol')}\n\n"
        f"【校验说明】\n{state.get('validation')}\n\n"
        f"【行情 JSON】\n{json.dumps(state.get('market') or {}, ensure_ascii=False, indent=2)}\n\n"
        f"【新闻与舆情】\n{state.get('news_block')}\n\n"
        f"【用户额外问题】\n{state.get('question') or '无'}\n"
    )
    return {"draft": _llm_text(sys, user)}


def node_review(state: AnalystState) -> dict:
    sys = """你是研报复核编辑。对照「原始 JSON」检查稿件中的数字是否与 JSON 一致；不一致则删除或改正为与 JSON 一致。
保留结构与免责声明。只输出最终 Markdown 全文，勿输出思考过程。"""
    user = (
        f"【原始 JSON】\n{json.dumps(state.get('market') or {}, ensure_ascii=False, indent=2)}\n\n"
        f"【待复核稿件】\n{state.get('draft')}\n"
    )
    return {"final": _llm_text(sys, user)}


def build_graph():
    g = StateGraph(AnalystState)
    g.add_node("fetch", node_fetch)
    g.add_node("validate", node_validate)
    g.add_node("draft", node_draft)
    g.add_node("review", node_review)
    g.set_entry_point("fetch")
    g.add_edge("fetch", "validate")
    g.add_edge("validate", "draft")
    g.add_edge("draft", "review")
    g.add_edge("review", END)
    return g.compile()


_compiled = None


def get_compiled_graph():
    global _compiled
    if _compiled is None:
        _compiled = build_graph()
    return _compiled


def run_stock_analyst_pipeline(symbol: str, question: str | None = None) -> dict:
    if not MINIMAX_API_KEY:
        raise ValueError("缺少环境变量 MINIMAX_API_KEY")
    sym = (symbol or "").strip()
    if not sym:
        raise ValueError("symbol 不能为空")
    init: AnalystState = {
        "symbol": sym,
        "question": (question or "").strip() or None,
        "market": {},
        "news_block": "",
        "validation": "",
        "draft": "",
        "final": "",
    }
    out = get_compiled_graph().invoke(init)
    return {
        "symbol": sym,
        "final_report": out.get("final") or "",
        "draft_report": out.get("draft") or "",
        "validation": out.get("validation") or "",
        "market": out.get("market") or {},
        "news_block": out.get("news_block") or "",
    }
