# -*- coding: utf-8 -*-
from __future__ import annotations

from types import SimpleNamespace
from typing import Any

import requests
from langchain_openai import ChatOpenAI

from app.config import (
    MINIMAX_API_BASE,
    MINIMAX_API_KEY,
    MINIMAX_MODEL,
    MINIMAX_PROVIDER,
    MINIMAX_TOKEN_PLAN_BASE,
)


def _extract_text_blocks(data: dict[str, Any]) -> str:
    content = data.get("content")
    if not isinstance(content, list):
        return ""
    parts: list[str] = []
    for item in content:
        if isinstance(item, dict) and item.get("type") == "text":
            t = item.get("text")
            if isinstance(t, str):
                parts.append(t.strip())
    return "\n".join([p for p in parts if p]).strip()


class TokenPlanChatModel:
    """Minimal adapter to mimic ChatOpenAI.invoke(messages)."""

    def invoke(self, messages):
        if not MINIMAX_API_KEY:
            raise ValueError("missing MINIMAX_API_KEY")

        system_parts: list[str] = []
        user_parts: list[str] = []
        for m in messages:
            content = getattr(m, "content", "")
            role = m.__class__.__name__.lower()
            if "system" in role:
                system_parts.append(str(content))
            else:
                user_parts.append(str(content))

        payload = {
            "model": MINIMAX_MODEL,
            "max_tokens": 1800,
            "system": "\n".join(system_parts).strip(),
            "messages": [{"role": "user", "content": "\n".join(user_parts).strip()}],
        }
        headers = {
            "x-api-key": MINIMAX_API_KEY,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        }
        url = f"{MINIMAX_TOKEN_PLAN_BASE}/v1/messages"
        r = requests.post(url, headers=headers, json=payload, timeout=30)
        if r.status_code >= 400:
            raise RuntimeError(f"token_plan_http_{r.status_code}: {(r.text or '')[:350]}")
        text = _extract_text_blocks(r.json() if r.text else {})
        if not text:
            raise RuntimeError("token_plan_empty_response")
        return SimpleNamespace(content=text)


def get_chat_model():
    if MINIMAX_PROVIDER == "token_plan":
        return TokenPlanChatModel()
    # MiniMax：temperature 须在 (0, 1]，文档建议可至 1.0
    return ChatOpenAI(
        base_url=MINIMAX_API_BASE,
        api_key=MINIMAX_API_KEY or "placeholder",
        model=MINIMAX_MODEL,
        temperature=0.85,
        max_tokens=4096,
        timeout=20,
        max_retries=0,
    )
