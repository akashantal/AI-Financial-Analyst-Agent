"""Tool registry for the analyst agent.

Each tool has (1) an OpenAI-style JSON schema the LLM sees, and (2) an async
handler that maps the LLM's arguments to our market-data / indicator services.
Indicators are computed in code (see services/indicators.py) so the LLM never
does arithmetic — it only decides *which* tools to call and narrates results.
"""
from __future__ import annotations

from typing import Any, Awaitable, Callable

from app.services import indicators, market_data

# ── JSON schemas exposed to the LLM ───────────────────────────────────────────

TOOL_SCHEMAS: list[dict] = [
    {
        "type": "function",
        "function": {
            "name": "get_quote",
            "description": "Get the latest price snapshot for a stock ticker "
                           "(last price, change, market cap, currency).",
            "parameters": {
                "type": "object",
                "properties": {
                    "ticker": {"type": "string", "description": "Yahoo Finance symbol. US: AAPL. "
                               "India: add .NS for NSE (RELIANCE.NS) or .BO for BSE."}
                },
                "required": ["ticker"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_indicators",
            "description": "Compute a full technical-indicator panel (SMA, EMA, RSI, "
                           "MACD, volatility, total return, max drawdown) for a ticker "
                           "over a period. Use this for performance / momentum questions.",
            "parameters": {
                "type": "object",
                "properties": {
                    "ticker": {"type": "string", "description": "Stock symbol, e.g. NVDA"},
                    "period": {
                        "type": "string",
                        "description": "Look-back window: 1mo, 3mo, 6mo, 1y, 2y, 5y. Default 6mo.",
                    },
                },
                "required": ["ticker"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_fundamentals",
            "description": "Get valuation and quality fundamentals (P/E, P/B, margins, "
                           "ROE, growth, beta, sector) for a ticker.",
            "parameters": {
                "type": "object",
                "properties": {
                    "ticker": {"type": "string"}
                },
                "required": ["ticker"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_news",
            "description": "Get recent news headlines for a ticker.",
            "parameters": {
                "type": "object",
                "properties": {
                    "ticker": {"type": "string"},
                    "limit": {"type": "integer", "description": "How many headlines (default 5)."},
                },
                "required": ["ticker"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "compare_tickers",
            "description": "Compare several tickers side by side on return, RSI, "
                           "volatility, and P/E over a period. Use for 'X vs Y' questions.",
            "parameters": {
                "type": "object",
                "properties": {
                    "tickers": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "List of symbols, e.g. ['AAPL','MSFT'].",
                    },
                    "period": {"type": "string", "description": "Look-back window. Default 6mo."},
                },
                "required": ["tickers"],
            },
        },
    },
]


# ── Handlers ──────────────────────────────────────────────────────────────────

async def _get_quote(ticker: str) -> dict[str, Any]:
    return await market_data.get_quote(ticker)


async def _get_indicators(ticker: str, period: str = "6mo") -> dict[str, Any]:
    closes = await market_data.get_closes(ticker, period=period)
    panel = indicators.summary(closes)
    return {"ticker": ticker.upper(), "period": period, "indicators": panel}


async def _get_fundamentals(ticker: str) -> dict[str, Any]:
    return await market_data.get_fundamentals(ticker)


async def _get_news(ticker: str, limit: int = 5) -> dict[str, Any]:
    return await market_data.get_news(ticker, limit=limit)


async def _compare_tickers(tickers: list[str], period: str = "6mo") -> dict[str, Any]:
    return await market_data.compare(tickers, period=period)


HANDLERS: dict[str, Callable[..., Awaitable[dict]]] = {
    "get_quote": _get_quote,
    "get_indicators": _get_indicators,
    "get_fundamentals": _get_fundamentals,
    "get_news": _get_news,
    "compare_tickers": _compare_tickers,
}


async def dispatch(name: str, arguments: dict) -> dict:
    """Invoke a tool by name with LLM-provided arguments. Errors are returned
    as data so the agent can recover rather than crashing the loop."""
    handler = HANDLERS.get(name)
    if handler is None:
        return {"error": f"unknown tool: {name}"}
    try:
        return await handler(**arguments)
    except Exception as e:
        return {"error": str(e)}
