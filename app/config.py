from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # Database — Supabase Postgres + pgvector
    supabase_database_url: str

    # LLM provider — "gemini" (free AI Studio tier) or "ollama" (fully local).
    # Both are reached through the OpenAI-compatible chat-completions API, so the
    # agent's function-calling loop is identical regardless of provider.
    llm_provider: str = "gemini"

    # Gemini via OpenAI-compatible endpoint
    gemini_api_key: str = ""
    gemini_base_url: str = "https://generativelanguage.googleapis.com/v1beta/openai/"
    llm_model: str = "gemini-2.0-flash"

    # Local Ollama (OpenAI-compatible at /v1). Use a tool-capable model (llama3.1+).
    ollama_chat_model: str = "llama3.1"

    # Embeddings — Ollama local (used for semantic recall of research notes)
    ollama_base_url: str = "http://localhost:11434"
    embedding_model: str = "nomic-embed-text"
    embedding_dim: int = 768  # nomic-embed-text output dimension

    # Cache — Upstash Redis (buffers free market-data API against rate limits)
    upstash_redis_rest_url: str = ""
    upstash_redis_rest_token: str = ""
    quote_cache_ttl_seconds: int = 60        # quotes go stale fast
    history_cache_ttl_seconds: int = 3600    # OHLCV history changes slowly intraday
    fundamentals_cache_ttl_seconds: int = 86400  # fundamentals change rarely

    # Agent tuning knobs
    agent_max_steps: int = 6          # max tool-call rounds before forcing a final answer
    default_history_period: str = "6mo"
    default_history_interval: str = "1d"


settings = Settings()
