"""Direct market-data endpoints (no LLM) — the deterministic foundation."""
from fastapi import APIRouter, HTTPException, Query

from app import schemas
from app.services import indicators, market_data

router = APIRouter()


@router.get("/{ticker}/quote", response_model=schemas.Quote)
async def quote(ticker: str):
    try:
        return await market_data.get_quote(ticker)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/{ticker}/history", response_model=schemas.History)
async def history(
    ticker: str,
    period: str = Query("6mo"),
    interval: str = Query("1d"),
):
    try:
        return await market_data.get_history(ticker, period=period, interval=interval)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/{ticker}/indicators", response_model=schemas.IndicatorResponse)
async def indicator_panel(ticker: str, period: str = Query("6mo")):
    try:
        closes = await market_data.get_closes(ticker, period=period)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    return {"ticker": ticker.upper(), "period": period, "indicators": indicators.summary(closes)}


@router.get("/{ticker}/fundamentals", response_model=schemas.Fundamentals)
async def fundamentals(ticker: str):
    return await market_data.get_fundamentals(ticker)


@router.get("/{ticker}/news", response_model=schemas.News)
async def news(ticker: str, limit: int = Query(5, ge=1, le=20)):
    return await market_data.get_news(ticker, limit=limit)


@router.get("/compare", response_model=schemas.Comparison)
async def compare(
    tickers: list[str] = Query(..., description="Repeat the param, e.g. ?tickers=AAPL&tickers=MSFT"),
    period: str = Query("6mo"),
):
    return await market_data.compare(tickers, period=period)
