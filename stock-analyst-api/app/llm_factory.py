# -*- coding: utf-8 -*-
from langchain_openai import ChatOpenAI

from app.config import MINIMAX_API_BASE, MINIMAX_API_KEY, MINIMAX_MODEL


def get_chat_model() -> ChatOpenAI:
    # MiniMax：temperature 须在 (0, 1]，文档建议可至 1.0
    return ChatOpenAI(
        base_url=MINIMAX_API_BASE,
        api_key=MINIMAX_API_KEY or "placeholder",
        model=MINIMAX_MODEL,
        temperature=0.85,
        max_tokens=4096,
    )
