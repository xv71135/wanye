# -*- coding: utf-8 -*-
import os

from fastapi import FastAPI, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from app.config import DEMO_ACCESS_TOKEN, MINIMAX_API_KEY
from app.graph import run_stock_analyst_pipeline

# 浏览器从 https://3737-k.info 直连 https://api.3737-k.info 为跨域；不可再用 allow_origins=["*"] 且 allow_credentials=True（规范禁止，浏览器会整段失败 → Failed to fetch）
_default_cors = "https://3737-k.info,https://www.3737-k.info,https://wanye-etf.pages.dev,http://127.0.0.1:5500,http://localhost:5173"
CORS_ORIGINS = [
    o.strip()
    for o in os.getenv("CORS_ORIGINS", _default_cors).split(",")
    if o.strip()
]

app = FastAPI(title="Stock Analyst Agent API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    # 与 apex / www / 任意子域页面互跨时更稳（Origin 只会是页面域，不会是 api.*）
    allow_origin_regex=r"^https://([\w-]+\.)*3737-k\.info$",
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


class AnalyzeRequest(BaseModel):
    symbol: str = Field(..., min_length=1, max_length=32, description="如 600519、AAPL、000001")
    question: str | None = Field(None, max_length=2000)


class AnalyzeResponse(BaseModel):
    symbol: str
    report_markdown: str
    meta: dict


@app.get("/")
def root():
    """根路径无分析接口；浏览器打开 IP:8788 时给出可用端点，避免误以为服务未启动。"""
    return {
        "service": "Stock Analyst Agent API",
        "endpoints": {
            "GET /health": "健康检查",
            "POST /analyze": "股票分析（JSON: symbol, question?）",
            "GET /docs": "OpenAPI 文档",
        },
    }


@app.get("/health")
def health():
    return {
        "ok": True,
        "minimax_configured": bool(MINIMAX_API_KEY),
        "auth_required": bool(DEMO_ACCESS_TOKEN),
    }


@app.post("/analyze", response_model=AnalyzeResponse)
def analyze(
    body: AnalyzeRequest,
    x_demo_token: str | None = Header(default=None, alias="X-Demo-Token"),
):
    if DEMO_ACCESS_TOKEN and x_demo_token != DEMO_ACCESS_TOKEN:
        raise HTTPException(status_code=401, detail="Invalid or missing X-Demo-Token")
    if not MINIMAX_API_KEY:
        raise HTTPException(status_code=503, detail="Server missing MINIMAX_API_KEY")

    try:
        result = run_stock_analyst_pipeline(body.symbol, body.question)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"{type(e).__name__}: {e}") from e

    return AnalyzeResponse(
        symbol=result["symbol"],
        report_markdown=result["final_report"],
        meta={
            "validation_excerpt": (result.get("validation") or "")[:800],
            "market_ok": bool((result.get("market") or {}).get("ok")),
            "pipeline": "LangGraph: fetch → validate → draft → review",
            "model_env": "MiniMax OpenAI-compatible (default MiniMax-M2.5)",
        },
    )
