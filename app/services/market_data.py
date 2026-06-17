"""Market data layer — free Yahoo Finance data via yfinance, buffered by Upstash.

yfinance hits Yahoo's public endpoints (no API key, free). Yahoo rate-limits
aggressively, so every call is cached in Upstash Redis. All network/parse calls
run in a thread (yfinance is synchronous) to avoid blocking the event loop.
"""
from __future__ import annotations

import asyncio
from typing import Any

import structlog
import yfinance as yf

from app.config import settings
from app.services import cache, indicators

logger = structlog.get_logger()


def _clean(ticker: str) -> str:
    return ticker.strip().upper()


async def _to_thread(fn, *args, **kwargs):
    return await asyncio.to_thread(fn, *args, **kwargs)


# ── Quote ─────────────────────────────────────────────────────────────────────

async def get_quote(ticker: str) -> dict[str, Any]:
    """Latest price snapshot for a ticker."""
    ticker = _clean(ticker)
    key = cache.cache_key("quote", ticker)
    cached = await cache.get_json(key)
    if cached is not None:
        return cached

    def _fetch() -> dict[str, Any]:
        t = yf.Ticker(ticker)
        fi = getattr(t, "fast_info", {}) or {}
        info = {}
        try:
            info = t.info or {}
        except Exception:
            pass
        last = fi.get("last_price") or info.get("currentPrice")
        prev = fi.get("previous_close") or info.get("previousClose")
        change = (last - prev) if (last is not None and prev is not None) else None
        change_pct = (change / prev) if (change is not None and prev) else None
        return {
            "ticker": ticker,
            "name": info.get("shortName") or info.get("longName"),
            "currency": fi.get("currency") or info.get("currency"),
            "last_price": last,
            "previous_close": prev,
            "change": round(change, 4) if change is not None else None,
            "change_percent": round(change_pct * 100, 4) if change_pct is not None else None,
            "market_cap": fi.get("market_cap") or info.get("marketCap"),
            "exchange": fi.get("exchange") or info.get("exchange"),
        }

    data = await _to_thread(_fetch)
    if data.get("last_price") is None:
        raise ValueError(f"No quote data found for '{ticker}' (is the symbol correct?)")
    await cache.set_json(key, data, settings.quote_cache_ttl_seconds)
    logger.info("market.quote", ticker=ticker, price=data.get("last_price"))
    return data


# ── History (OHLCV) ─────────────────────────────────────────────────────────

async def get_history(
    ticker: str,
    period: str | None = None,
    interval: str | None = None,
) -> dict[str, Any]:
    """Historical OHLCV. period e.g. '1mo','6mo','1y','5y'; interval e.g. '1d','1wk'."""
    ticker = _clean(ticker)
    period = period or settings.default_history_period
    interval = interval or settings.default_history_interval
    key = cache.cache_key("history", ticker, period, interval)
    cached = await cache.get_json(key)
    if cached is not None:
        return cached

    def _fetch() -> dict[str, Any]:
        t = yf.Ticker(ticker)
        df = t.history(period=period, interval=interval, auto_adjust=True)
        if df is None or df.empty:
            return {"ticker": ticker, "period": period, "interval": interval, "candles": []}
        candles = [
            {
                "date": idx.strftime("%Y-%m-%d"),
                "open": round(float(row["Open"]), 4),
                "high": round(float(row["High"]), 4),
                "low": round(float(row["Low"]), 4),
                "close": round(float(row["Close"]), 4),
                "volume": int(row["Volume"]),
            }
            for idx, row in df.iterrows()
        ]
        return {"ticker": ticker, "period": period, "interval": interval, "candles": candles}

    data = await _to_thread(_fetch)
    if not data["candles"]:
        raise ValueError(f"No price history for '{ticker}' (period={period}, interval={interval}).")
    await cache.set_json(key, data, settings.history_cache_ttl_seconds)
    logger.info("market.history", ticker=ticker, candles=len(data["candles"]))
    return data


async def get_closes(ticker: str, period: str | None = None) -> list[float]:
    """Convenience: just the closing-price series (oldest → newest)."""
    hist = await get_history(ticker, period=period, interval="1d")
    return [c["close"] for c in hist["candles"]]


# ── Fundamentals ──────────────────────────────────────────────────────────────

async def get_fundamentals(ticker: str) -> dict[str, Any]:
    """Key valuation/quality metrics from Yahoo's info blob."""
    ticker = _clean(ticker)
    key = cache.cache_key("fundamentals", ticker)
    cached = await cache.get_json(key)
    if cached is not None:
        return cached

    def _fetch() -> dict[str, Any]:
        info = yf.Ticker(ticker).info or {}
        fields = [
            "sector", "industry", "marketCap", "trailingPE", "forwardPE",
            "priceToBook", "pegRatio", "dividendYield", "beta", "profitMargins",
            "returnOnEquity", "revenueGrowth", "earningsGrowth", "debtToEquity",
            "freeCashflow", "fiftyTwoWeekHigh", "fiftyTwoWeekLow",
        ]
        return {"ticker": ticker, **{f: info.get(f) for f in fields}}

    data = await _to_thread(_fetch)
    await cache.set_json(key, data, settings.fundamentals_cache_ttl_seconds)
    logger.info("market.fundamentals", ticker=ticker)
    return data


# ── News ────────────────────────────────────────────────────────────────────

async def get_news(ticker: str, limit: int = 5) -> dict[str, Any]:
    """Recent headlines for a ticker (titles + links + publisher)."""
    ticker = _clean(ticker)
    key = cache.cache_key("news", ticker, str(limit))
    cached = await cache.get_json(key)
    if cached is not None:
        return cached

    def _fetch() -> dict[str, Any]:
        raw = yf.Ticker(ticker).news or []
        items = []
        for n in raw[:limit]:
            content = n.get("content", n)  # yfinance schema varies by version
            items.append({
                "title": content.get("title") or n.get("title"),
                "publisher": (content.get("provider") or {}).get("displayName")
                              if isinstance(content.get("provider"), dict)
                              else n.get("publisher"),
                "link": (content.get("canonicalUrl") or {}).get("url")
                         if isinstance(content.get("canonicalUrl"), dict)
                         else n.get("link"),
            })
        return {"ticker": ticker, "headlines": items}

    data = await _to_thread(_fetch)
    await cache.set_json(key, data, settings.quote_cache_ttl_seconds * 5)
    logger.info("market.news", ticker=ticker, count=len(data["headlines"]))
    return data


# ── Comparison ────────────────────────────────────────────────────────────────

async def compare(tickers: list[str], period: str | None = None) -> dict[str, Any]:
    """Side-by-side metrics for several tickers. Per-ticker failures are isolated
    so one bad symbol never sinks the whole comparison."""
    period = period or settings.default_history_period
    rows = []
    for raw in tickers:
        t = _clean(raw)
        try:
            closes = await get_closes(t, period=period)
            fund = await get_fundamentals(t)
            rows.append({
                "ticker": t,
                "last_close": closes[-1] if closes else None,
                "total_return": indicators.total_return(closes),
                "rsi_14": indicators.rsi(closes, 14),
                "annualized_volatility": indicators.annualized_volatility(closes),
                "trailingPE": fund.get("trailingPE"),
                "error": None,
            })
        except Exception as e:
            rows.append({"ticker": t, "error": str(e)})
    logger.info("market.compare", tickers=[_clean(x) for x in tickers], period=period)
    return {"period": period, "rows": rows}
