"""Research memory — persist agent briefings and recall them semantically.

Each briefing is embedded with Ollama (nomic-embed-text) and stored in pgvector,
so a later question like "what did we find on chip stocks?" can surface prior
analyses by meaning, not just exact ticker match. Same pattern as Project 1.
"""
from __future__ import annotations

import structlog
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.embeddings import embed_single

logger = structlog.get_logger()


async def save_briefing(
    db: AsyncSession,
    ticker: str,
    question: str,
    briefing: str,
) -> str | None:
    """Embed and persist a briefing. Returns the new row id, or None on failure
    (memory is best-effort — it must never break the /analyze response)."""
    try:
        embedding = await embed_single(briefing)
        embedding_str = "[" + ",".join(map(str, embedding)) + "]"
        sql = text(f"""
            INSERT INTO research_notes (ticker, question, briefing, embedding)
            VALUES (:ticker, :question, :briefing, '{embedding_str}'::vector)
            RETURNING id::text
        """)
        row = await db.execute(
            sql, {"ticker": ticker.upper(), "question": question, "briefing": briefing}
        )
        await db.commit()
        new_id = row.scalar_one()
        logger.info("memory.saved", ticker=ticker, id=new_id)
        return new_id
    except Exception as e:
        logger.warning("memory.save_failed", error=str(e))
        await db.rollback()
        return None


async def search(db: AsyncSession, query: str, top_k: int = 5) -> list[dict]:
    """Semantic search over past briefings via pgvector cosine distance."""
    embedding = await embed_single(query)
    embedding_str = "[" + ",".join(map(str, embedding)) + "]"
    sql = text(f"""
        SELECT
            id::text, ticker, question, briefing,
            created_at,
            1 - (embedding <=> '{embedding_str}'::vector) AS similarity
        FROM research_notes
        ORDER BY embedding <=> '{embedding_str}'::vector
        LIMIT :limit
    """)
    rows = await db.execute(sql, {"limit": top_k})
    return [
        {
            "id": r.id,
            "ticker": r.ticker,
            "question": r.question,
            "briefing": r.briefing,
            "created_at": str(r.created_at),
            "similarity": float(r.similarity),
        }
        for r in rows.all()
    ]


async def recent(db: AsyncSession, limit: int = 10) -> list[dict]:
    """Most recent briefings, newest first."""
    sql = text("""
        SELECT id::text, ticker, question, briefing, created_at
        FROM research_notes
        ORDER BY created_at DESC
        LIMIT :limit
    """)
    rows = await db.execute(sql, {"limit": limit})
    return [
        {
            "id": r.id,
            "ticker": r.ticker,
            "question": r.question,
            "briefing": r.briefing,
            "created_at": str(r.created_at),
            "similarity": None,
        }
        for r in rows.all()
    ]
