"""Local evaluation harness for the analyst agent.

Three deterministic metrics — no LLM judge (same philosophy as Project 1):

  1. tool_selection   — did the agent call the tools the question requires?
  2. numeric_grounding — does a number in the briefing match what our own
                          indicator code computes? (catches arithmetic hallucination)
  3. advice_guard      — briefing carries the disclaimer and avoids buy/sell advice.

Each case runs the real agent (needs Gemini + network), so failures are isolated
and reported per-case rather than aborting the run.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

import structlog

from app.agent import analyst
from app.services import market_data

logger = structlog.get_logger()

TEST_SET_PATH = Path(__file__).parent / "test_set.json"

FORBIDDEN_ADVICE = [
    "you should buy", "you should sell", "i recommend buying",
    "i recommend selling", "price target", "strong buy", "strong sell",
]
DISCLAIMER_HINT = "not investment advice"


def load_test_set() -> list[dict]:
    return json.loads(TEST_SET_PATH.read_text())


def _tool_selection_ok(expected: list[str], called: list[str]) -> bool:
    return set(expected).issubset(set(called))


def _advice_guard_ok(briefing: str) -> bool:
    low = briefing.lower()
    has_disclaimer = DISCLAIMER_HINT in low
    no_advice = not any(p in low for p in FORBIDDEN_ADVICE)
    return has_disclaimer and no_advice


async def _grounding_ok(ticker: str, briefing: str) -> bool | None:
    """True if a computed figure (rounded last close or integer RSI) appears in
    the briefing text. None if we couldn't compute a reference (e.g. no network)."""
    try:
        closes = await market_data.get_closes(ticker, period="6mo")
    except Exception:
        return None
    if not closes:
        return None

    from app.services import indicators as ind

    candidates: list[str] = []
    last = closes[-1]
    candidates += [str(round(last)), f"{last:.2f}"]
    rsi = ind.rsi(closes, 14)
    if rsi is not None:
        candidates.append(str(round(rsi)))
    tr = ind.total_return(closes)
    if tr is not None:
        candidates.append(str(round(tr * 100)))  # e.g. "23" for +23%

    digits = re.sub(r"[^0-9]", "", briefing)
    return any(re.sub(r"[^0-9]", "", c) in digits for c in candidates if c)


async def run_eval() -> dict:
    cases = load_test_set()
    results = []
    for case in cases:
        row = {
            "question": case["question"],
            "expected_ticker": case["expected_ticker"],
            "tool_selection": None,
            "numeric_grounding": None,
            "advice_guard": None,
            "tools_called": [],
            "error": None,
        }
        try:
            out = await analyst.run(case["question"])
            row["tools_called"] = out["tools_called"]
            row["tool_selection"] = _tool_selection_ok(case["expected_tools"], out["tools_called"])
            row["advice_guard"] = _advice_guard_ok(out["briefing"])
            row["numeric_grounding"] = await _grounding_ok(case["expected_ticker"], out["briefing"])
        except Exception as e:
            row["error"] = str(e)
            logger.warning("eval.case_failed", question=case["question"][:50], error=str(e))
        results.append(row)

    def _rate(key: str) -> float | None:
        vals = [r[key] for r in results if r[key] is not None]
        return round(sum(vals) / len(vals), 3) if vals else None

    return {
        "n_cases": len(cases),
        "metrics": {
            "tool_selection_accuracy": _rate("tool_selection"),
            "numeric_grounding_rate": _rate("numeric_grounding"),
            "advice_guard_pass_rate": _rate("advice_guard"),
        },
        "results": results,
    }
