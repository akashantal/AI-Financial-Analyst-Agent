"""Research memory endpoints — recall past agent briefings (Phase 4)."""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app import schemas
from app.db.session import get_db
from app.services import memory

router = APIRouter()


@router.get("/search", response_model=list[schemas.ResearchHit])
async def search(
    q: str = Query(..., description="Natural-language query over past briefings"),
    top_k: int = Query(5, ge=1, le=20),
    db: AsyncSession = Depends(get_db),
):
    return await memory.search(db, q, top_k=top_k)


@router.get("/recent", response_model=list[schemas.ResearchHit])
async def recent(
    limit: int = Query(10, ge=1, le=50),
    db: AsyncSession = Depends(get_db),
):
    return await memory.recent(db, limit=limit)
