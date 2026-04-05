# -*- coding: utf-8 -*-
from fastapi import FastAPI, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from app.config import DEMO_ACCESS_TOKEN, MINIMAX_API_KEY
from app.graph import run_stock_analyst_pipeline

app = FastAPI(title="Stock Analyst Agent API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
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
