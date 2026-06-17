"""Typed response models for the market + analyze endpoints.

Keeping these in one place gives Swagger accurate schemas and makes the API
contract explicit. Fields are Optional where the upstream free data source
(yfinance) may omit them.
"""
from __future__ import annotations

from pydantic import BaseModel


class Quote(BaseModel):
    ticker: str
    name: str | None = None
    currency: str | None = None
    last_price: float | None = None
    previous_close: float | None = None
    change: float | None = None
    change_percent: float | None = None
    market_cap: float | None = None
    exchange: str | None = None


class Candle(BaseModel):
    date: str
    open: float
    high: float
    low: float
    close: float
    volume: int


class History(BaseModel):
    ticker: str
    period: str
    interval: str
    candles: list[Candle]


class IndicatorPanel(BaseModel):
    last_close: float | None = None
    sma_20: float | None = None
    sma_50: float | None = None
    ema_20: float | None = None
    rsi_14: float | None = None
    macd: dict | None = None
    annualized_volatility: float | None = None
    total_return: float | None = None
    max_drawdown: float | None = None
    data_points: int


class IndicatorResponse(BaseModel):
    ticker: str
    period: str
    indicators: IndicatorPanel


class Fundamentals(BaseModel):
    ticker: str
    sector: str | None = None
    industry: str | None = None
    marketCap: float | None = None
    trailingPE: float | None = None
    forwardPE: float | None = None
    priceToBook: float | None = None
    pegRatio: float | None = None
    dividendYield: float | None = None
    beta: float | None = None
    profitMargins: float | None = None
    returnOnEquity: float | None = None
    revenueGrowth: float | None = None
    earningsGrowth: float | None = None
    debtToEquity: float | None = None
    freeCashflow: float | None = None
    fiftyTwoWeekHigh: float | None = None
    fiftyTwoWeekLow: float | None = None


class Headline(BaseModel):
    title: str | None = None
    publisher: str | None = None
    link: str | None = None


class News(BaseModel):
    ticker: str
    headlines: list[Headline]


class ComparisonRow(BaseModel):
    ticker: str
    last_close: float | None = None
    total_return: float | None = None
    rsi_14: float | None = None
    annualized_volatility: float | None = None
    trailingPE: float | None = None
    error: str | None = None


class Comparison(BaseModel):
    period: str
    rows: list[ComparisonRow]


# ── Agent ─────────────────────────────────────────────────────────────────────

class AnalyzeRequest(BaseModel):
    question: str


class AnalyzeResponse(BaseModel):
    question: str
    briefing: str
    tools_called: list[str]
    steps: int


# ── Research memory (Phase 4) ─────────────────────────────────────────────────

class ResearchHit(BaseModel):
    id: str
    ticker: str
    question: str
    briefing: str
    created_at: str
    similarity: float | None = None
