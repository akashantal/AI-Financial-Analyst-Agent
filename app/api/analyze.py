"""The agentic endpoint — natural-language question → analyst briefing.

After the agent answers, the briefing is persisted + embedded for later semantic
recall (Phase 4). Persistence is best-effort and never blocks the response.
"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app import schemas
from app.agent import analyst
from app.db.session import get_db
from app.services import memory

router = APIRouter()


@router.post("/", response_model=schemas.AnalyzeResponse)
async def analyze(
    req: schemas.AnalyzeRequest,
    remember: bool = Query(True, description="Persist + embed the briefing for later recall"),
    db: AsyncSession = Depends(get_db),
):
    result = await analyst.run(req.question)

    if remember and result["briefing"]:
        tickers = result.get("tickers") or []
        primary = tickers[0] if tickers else "N/A"
        await memory.save_briefing(db, primary, req.question, result["briefing"])

    return schemas.AnalyzeResponse(
        question=result["question"],
        briefing=result["briefing"],
        tools_called=result["tools_called"],
        steps=result["steps"],
    )
