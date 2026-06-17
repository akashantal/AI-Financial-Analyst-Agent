"""Evaluation endpoints (Phase 5)."""
from fastapi import APIRouter

from app.eval import runner

router = APIRouter()


@router.get("/test-set")
async def test_set():
    """Return the evaluation test cases."""
    return runner.load_test_set()


@router.post("/run")
async def run():
    """Run the full evaluation suite and return aggregate metrics + per-case detail.

    Note: each case invokes the real agent (Gemini + live market data), so this
    makes network calls and is slower than a unit test.
    """
    return await runner.run_eval()
