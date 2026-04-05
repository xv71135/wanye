# -*- coding: utf-8 -*-
import os

from dotenv import load_dotenv

load_dotenv()

# MiniMax OpenAI 兼容（官方文档：https://platform.minimax.io/docs/api-reference/text-openai-api）
MINIMAX_API_BASE = os.getenv("MINIMAX_API_BASE", "https://api.minimax.io/v1").rstrip("/")
MINIMAX_API_KEY = os.getenv("MINIMAX_API_KEY", "").strip()
MINIMAX_MODEL = os.getenv("MINIMAX_MODEL", "MiniMax-M2.5")

# 可选：限制浏览器调用（留空则不校验）
DEMO_ACCESS_TOKEN = os.getenv("DEMO_ACCESS_TOKEN", "").strip()
