import time

import structlog
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings

logger = structlog.get_logger()

app = FastAPI(
    title="AI Financial Analyst Agent",
    description="Agentic market/stock research on free data (yfinance + Gemini + Supabase).",
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Request latency logging ───────────────────────────────────────────────────
@app.middleware("http")
async def log_requests(request: Request, call_next):
    start = time.perf_counter()
    response = await call_next(request)
    latency_ms = round((time.perf_counter() - start) * 1000)
    logger.info(
        "request",
        method=request.method,
        path=request.url.path,
        status=response.status_code,
        latency_ms=latency_ms,
    )
    return response


# ── Health check ──────────────────────────────────────────────────────────────
@app.get("/health", tags=["ops"])
async def health():
    try:
        from sqlalchemy import text

        from app.db.session import engine

        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        db_status = "ok"
    except Exception as e:
        db_status = f"error: {e}"

    from app.services.llm import MODEL as llm_model

    return {
        "status": "ok" if db_status == "ok" else "degraded",
        "db": db_status,
        "llm_provider": settings.llm_provider,
        "llm_model": llm_model,
        "embedding_model": settings.embedding_model,
        "data_source": "yfinance (Yahoo Finance, free)",
    }


# ── Routers ───────────────────────────────────────────────────────────────────
from app.api.market import router as market_router  # noqa: E402
app.include_router(market_router, prefix="/market", tags=["market"])

from app.api.analyze import router as analyze_router  # noqa: E402
app.include_router(analyze_router, prefix="/analyze", tags=["analyze"])

from app.api.research import router as research_router  # noqa: E402
app.include_router(research_router, prefix="/research", tags=["research"])

from app.api.eval import router as eval_router  # noqa: E402
app.include_router(eval_router, prefix="/eval", tags=["eval"])
