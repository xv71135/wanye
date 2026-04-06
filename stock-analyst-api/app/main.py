# -*- coding: utf-8 -*-
import os
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeoutError

from fastapi import FastAPI, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from app.config import DEMO_ACCESS_TOKEN, MINIMAX_API_KEY, MINIMAX_MODEL, MINIMAX_PROVIDER
from app.llm_factory import get_chat_model

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
        "provider": MINIMAX_PROVIDER,
        "model": MINIMAX_MODEL,
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

    timeout_sec = int(os.getenv("ANALYZE_LLM_TIMEOUT_SEC", "45"))

    def _single_shot_report() -> str:
        llm = get_chat_model()
        system = (
            "你是资深股票研究助手。输出简洁的 Markdown 报告，包含："
            "核心观察、风险提示、需核实问题、下一步建议、免责声明。"
            "若信息不足必须明确写“数据不足，无法判断”。不要给确定性投资建议。"
        )
        user = (
            f"股票代码：{body.symbol}\n"
            f"用户问题：{body.question or '无'}\n\n"
            "请输出结构化简报，重点是可执行与可核实。"
        )
        msg = llm.invoke(
            [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
        )
        text = (getattr(msg, "content", None) or "").strip()
        if not text:
            raise RuntimeError("empty_model_response")
        return text

    try:
        ex = ThreadPoolExecutor(max_workers=1)
        fut = ex.submit(_single_shot_report)
        report_markdown = fut.result(timeout=timeout_sec)
        ex.shutdown(wait=False, cancel_futures=True)
    except FuturesTimeoutError:
        return AnalyzeResponse(
            symbol=body.symbol,
            report_markdown=(
                f"## {body.symbol} 分析超时（已触发兜底）\n\n"
                "上游推理或外部数据源响应较慢，请稍后重试。\n\n"
                "这不是模型不可用，只是本次请求超时。"
            ),
            meta={
                "pipeline": "single-shot model generation",
                "provider": MINIMAX_PROVIDER,
                "model": MINIMAX_MODEL,
                "degraded_mode": True,
                "llm_error": f"pipeline_timeout_{timeout_sec}s",
            },
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"{type(e).__name__}: {e}") from e

    return AnalyzeResponse(
        symbol=body.symbol,
        report_markdown=report_markdown,
        meta={
            "pipeline": "single-shot model generation",
            "provider": MINIMAX_PROVIDER,
            "model": MINIMAX_MODEL,
            "degraded_mode": False,
        },
    )
