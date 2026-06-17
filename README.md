# AI Financial Analyst Agent

An **agentic market/stock research assistant** built entirely on free / local infrastructure.
Ask a natural-language question and a Gemini-powered agent pulls live market data, computes
technical indicators, and writes an analyst-style briefing — grounding every number in real,
code-computed values (no arithmetic hallucination).

> ⚠️ **Not investment advice.** This is a portfolio/engineering project. The agent produces
> research summaries only — never buy/sell recommendations or trade execution.

This is **Project 2** of a two-project AI portfolio; it reuses the free stack proven in
[`rag-api`](../rag-api) (Project 1). See [`AI-Plan.md`](./AI-Plan.md) for the full roadmap.

## Free stack

| Concern | Tool |
|---|---|
| Market data | **yfinance** (Yahoo Finance, no API key) |
| LLM / agent reasoning | **Google Gemini** `gemini-2.0-flash` (free AI Studio tier, OpenAI-compatible endpoint) |
| Embeddings | **Ollama** `nomic-embed-text` (local) |
| Storage / vectors | **Supabase** Postgres + `pgvector` (free tier) |
| Cache | **Upstash Redis** (free tier; optional — app no-ops without it) |
| API | **FastAPI** + async SQLAlchemy |

## Quick start

```bash
cd ~/Desktop/AI-Financial-Analyst-Agent
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

cp .env.example .env        # fill in Supabase + Gemini (+ optional Upstash) values
ollama pull nomic-embed-text  # for Phase 4 semantic recall

# (optional, Phase 4) run scripts/setup_db.sql in the Supabase SQL Editor

uvicorn app.main:app --reload
```

Open http://localhost:8000/docs for interactive Swagger.

## Endpoints

| Method | Path | Description |
|---|---|---|
| GET | `/health` | Liveness + config + DB status |
| GET | `/market/{ticker}/quote` | Latest price snapshot |
| GET | `/market/{ticker}/history?period=6mo&interval=1d` | OHLCV candles |
| GET | `/market/{ticker}/indicators?period=6mo` | SMA, EMA, RSI, MACD, volatility, returns, drawdown |
| GET | `/market/{ticker}/fundamentals` | P/E, P/B, margins, ROE, growth, beta |
| GET | `/market/{ticker}/news?limit=5` | Recent headlines |
| GET | `/market/compare?tickers=AAPL&tickers=MSFT&period=1y` | Side-by-side metrics |
| POST | `/analyze?remember=true` | `{ "question": "..." }` → agentic analyst briefing (persisted + embedded) |
| GET | `/research/search?q=...` | Semantic recall of past briefings |
| GET | `/research/recent?limit=10` | Most recent briefings |
| GET | `/eval/test-set` | Evaluation test cases |
| POST | `/eval/run` | Run the agent eval suite (tool-selection, numeric grounding, advice guard) |

Example:

```bash
curl -X POST localhost:8000/analyze -H 'content-type: application/json' \
  -d '{"question":"How has NVDA performed over the last 6 months and is it overbought?"}'
```

### Indian markets (NSE / BSE)

Works out of the box via Yahoo Finance symbols — figures come back in **INR**:

- **NSE**: append `.NS` → `RELIANCE.NS`, `TCS.NS`, `INFY.NS`, `HDFCBANK.NS`
- **BSE**: append `.BO` → `RELIANCE.BO`, `500325.BO`
- **Indices**: `^NSEI` (Nifty 50), `^BSESN` (Sensex)

```bash
curl -s localhost:8000/market/RELIANCE.NS/quote
curl -s "localhost:8000/market/TCS.NS/indicators?period=6mo"
curl -s "localhost:8000/market/compare?tickers=TCS.NS&tickers=INFY.NS&period=1y"
```

The agent knows the suffix convention, so plain names work too:

```bash
curl -s -X POST localhost:8000/analyze -H 'content-type: application/json' \
  -d '{"question":"How has Reliance performed over the last 6 months?"}'
```

Note: Yahoo's fundamentals are sometimes sparser for Indian tickers (some P/E or margin
fields may be null); price/indicator data is reliable.

## Architecture

```
/analyze  ─►  Analyst agent (Gemini function-calling loop, app/agent/analyst.py)
                 │ decides + calls tools (app/agent/tools.py)
                 ▼
       get_quote · get_indicators · get_fundamentals · get_news
                 │
                 ▼
       market_data.py (yfinance + Upstash cache)  +  indicators.py (pure functions)
```

Indicators are computed deterministically in `app/services/indicators.py`; the LLM only
decides which tools to call and narrates the returned numbers. This is the core reliability
property of the design.

## Build status

- ✅ **Phase 0 — Scaffold**: structure, config, FastAPI app, market-data layer, indicators, agent loop, endpoints.
- ✅ **Phase 1 — Typed API**: Pydantic response models for every endpoint (`app/schemas.py`).
- ✅ **Phase 2 — Indicators + tests**: 19 unit tests in `tests/test_indicators.py` (all passing).
- ✅ **Phase 3 — Richer agent**: multi-ticker `compare_tickers` tool + `/market/compare`.
- ✅ **Phase 4 — Memory + recall**: briefings persisted + embedded to pgvector; `/research/search` & `/research/recent`.
- ✅ **Phase 5 — Evaluation**: `app/eval/` harness + `/eval/run` (tool-selection, numeric grounding, advice guard).

Run the tests:

```bash
pytest -q          # 19 passed
```

See [`AI-Plan.md`](./AI-Plan.md).
