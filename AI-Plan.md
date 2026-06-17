# AI Engineering Portfolio — Build Plan

A two-project portfolio to demonstrate production AI-engineering skills, built entirely on **free / local infrastructure** (no paid APIs, no cloud bills).

## Shared free stack (reused across both projects)

| Concern | Tool | Why it's free |
|---|---|---|
| LLM / reasoning | **Google Gemini** (`gemini-2.0-flash`) via the OpenAI-compatible endpoint | Generous free tier on AI Studio |
| Embeddings | **Ollama** `nomic-embed-text` (768-dim), runs locally | Local, no cost |
| Vector + relational store | **Supabase** Postgres + `pgvector` | Free tier |
| Cache / rate-limit buffer | **Upstash Redis** (REST) | Free tier |
| Reranking | **sentence-transformers** cross-encoder, local | Local, no cost |
| API framework | **FastAPI** + async SQLAlchemy + asyncpg | Open source |

---

## Project 1 — `rag-api` ✅ COMPLETE

A production-grade document Q&A service (RAG).

- **Phase 1** — Ingestion: `/documents/upload`, chunking, Ollama embedding, pgvector storage.
- **Phase 2** — Retrieval + generation: vector search → LLM answer (`/query`).
- **Phase 3** — Advanced retrieval: query rewriting, BM25 (Postgres FTS), Reciprocal Rank Fusion, cross-encoder rerank.
- **Phase 4** — Evaluation: local deterministic metrics (retrieval coverage, faithfulness, answer relevance) at `/eval/run`.

Status: shipped to GitHub. Reused here as the architectural template.

---

## Project 2 — `AI-Financial-Analyst-Agent` ✅ PHASES 0–5 COMPLETE

An **agentic market/stock research assistant**. The user asks a natural-language question
("How has NVDA performed this quarter and is it overbought?"). A Gemini-powered agent decides
which tools to call, pulls **live market data from free sources**, computes indicators, and
writes an analyst-style briefing — with caching and optional semantic recall of past research.

> ⚠️ Not investment advice. The agent produces research summaries, never buy/sell recommendations
> or trade execution. This is a portfolio/engineering demo.

### New free source introduced here
- **`yfinance`** — free Yahoo Finance market data (quotes, OHLCV history, fundamentals, news). No API key.
- Optional fallback: **Stooq** CSV endpoint (free, no key) for historical prices.

### Architecture

```
User question
     │
     ▼
┌─────────────────────────────┐
│  Analyst Agent (Gemini)     │  function-calling loop
│  - decides which tools to   │
│    call, may call several   │
└──────────────┬──────────────┘
               │ tool calls
   ┌───────────┼───────────────────────────┐
   ▼           ▼                ▼            ▼
get_quote  get_history   get_fundamentals  get_news     ── market_data.py (yfinance + Upstash cache)
               │
               ▼
        compute_indicators  ── indicators.py (SMA, EMA, RSI, MACD, volatility, returns)
               │
               ▼
   Gemini synthesizes a cited briefing → stored in Supabase, embedded for later recall
```

### Phased build

- ✅ **Phase 0 — Scaffold**
  Repo structure, `config.py`, `.env.example`, FastAPI app with `/health`, DB session + models,
  Upstash cache, Gemini client, Ollama embeddings, `market_data` (yfinance) + `indicators`,
  agent tool registry + loop, `setup_db.sql`.

- ✅ **Phase 1 — Typed market-data layer**
  `yfinance` wrappers (quote, history, fundamentals, news) with Upstash caching and graceful
  fallbacks. Pydantic response models in `app/schemas.py` wired into every `/market/*` endpoint.

- ✅ **Phase 2 — Indicators & analytics**
  SMA/EMA, RSI, MACD, annualized volatility, total return, max drawdown — pure functions in
  `services/indicators.py`, covered by 19 unit tests (`tests/test_indicators.py`, all passing).

- ✅ **Phase 3 — The agent**
  Gemini function-calling loop in `agent/analyst.py`; tool registry in `agent/tools.py`
  (`get_quote`, `get_indicators`, `get_fundamentals`, `get_news`, `compare_tickers`).
  Multi-step reasoning → structured briefing. `/analyze` + `/market/compare`.

- ✅ **Phase 4 — Memory + semantic recall**
  Briefings persisted to Supabase and embedded with Ollama into `pgvector`
  (`services/memory.py`). `/research/search` (semantic) and `/research/recent`.

- ✅ **Phase 5 — Evaluation**
  Local deterministic harness (`app/eval/`): tool-selection accuracy, numeric-grounding
  (does a briefing number match our own computed indicators?), and an advice-guard
  (disclaimer present, no buy/sell language). `/eval/run` + `/eval/test-set`.

### Future ideas (Phase 6+)
- Watchlist endpoints + scheduled daily briefings.
- Stooq fallback data source.
- Streaming `/analyze` responses.

### Interview talking points
- Reused a battle-tested free stack across two very different AI systems (RAG vs. agentic tool-use).
- Agent grounds every claim in deterministically-computed numbers — indicators are computed in code,
  not by the LLM, eliminating arithmetic hallucination.
- Caching layer makes the free data source resilient to rate limits.
