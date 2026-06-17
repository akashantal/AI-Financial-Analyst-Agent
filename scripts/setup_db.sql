-- ============================================================
-- Run this once in Supabase SQL Editor before starting the app
-- Dashboard → SQL Editor → paste → Run
-- (Only needed for Phase 4 memory/recall; the market + agent
--  endpoints work without any tables.)
-- ============================================================

-- 1. Enable pgvector
CREATE EXTENSION IF NOT EXISTS vector;

-- 2. Research notes — agent briefings, embedded for semantic recall
CREATE TABLE IF NOT EXISTS research_notes (
    id         UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    ticker     TEXT        NOT NULL,
    question   TEXT        NOT NULL,
    briefing   TEXT        NOT NULL,
    embedding  vector(768),                 -- matches nomic-embed-text output
    created_at TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX IF NOT EXISTS research_notes_ticker_idx ON research_notes(ticker);

CREATE INDEX IF NOT EXISTS research_notes_embedding_hnsw_idx
    ON research_notes USING hnsw (embedding vector_cosine_ops)
    WITH (m = 16, ef_construction = 128);

-- 3. Watchlist
CREATE TABLE IF NOT EXISTS watchlist (
    id         UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    ticker     TEXT        NOT NULL UNIQUE,
    note       TEXT,
    created_at TIMESTAMPTZ DEFAULT now()
);

-- 4. Agent run logs — observability
CREATE TABLE IF NOT EXISTS agent_run_logs (
    id           UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    question     TEXT        NOT NULL,
    tools_called TEXT,
    steps        INTEGER,
    latency_ms   INTEGER,
    created_at   TIMESTAMPTZ DEFAULT now()
);

-- Verify
SELECT table_name FROM information_schema.tables
WHERE table_schema = 'public'
ORDER BY table_name;
