"""Local embeddings via Ollama (nomic-embed-text, 768-dim).

Used to embed agent briefings so past research can be recalled semantically
from pgvector. Identical pattern to Project 1 (rag-api).
"""
import httpx

from app.config import settings


async def embed_texts(texts: list[str]) -> list[list[float]]:
    """Embed a list of texts via Ollama. Returns 768-dim vectors.

    Tries the newer batch endpoint (/api/embed, Ollama >= 0.1.32) first,
    then falls back to the older per-text endpoint (/api/embeddings).
    """
    async with httpx.AsyncClient(timeout=120.0) as client:
        try:
            resp = await client.post(
                f"{settings.ollama_base_url}/api/embed",
                json={"model": settings.embedding_model, "input": texts},
            )
            if resp.status_code == 200:
                return resp.json()["embeddings"]
        except Exception:
            pass

        embeddings = []
        for text in texts:
            resp = await client.post(
                f"{settings.ollama_base_url}/api/embeddings",
                json={"model": settings.embedding_model, "prompt": text},
            )
            resp.raise_for_status()
            embeddings.append(resp.json()["embedding"])
        return embeddings


async def embed_single(text: str) -> list[float]:
    """Convenience wrapper for embedding a single string."""
    vectors = await embed_texts([text])
    return vectors[0]
