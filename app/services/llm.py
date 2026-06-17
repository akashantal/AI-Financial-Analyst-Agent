"""LLM client — provider-switchable, OpenAI-compatible.

Two free options, both speaking the OpenAI chat-completions protocol (so the
agent's function-calling loop never changes):

  • LLM_PROVIDER=gemini  → Google AI Studio free tier (gemini-2.0-flash)
  • LLM_PROVIDER=ollama  → fully local Ollama at /v1 (use llama3.1+ for tool calls)
"""
from openai import AsyncOpenAI

from app.config import settings

if settings.llm_provider == "ollama":
    client = AsyncOpenAI(
        api_key="ollama",  # Ollama ignores the key but the SDK requires one
        base_url=settings.ollama_base_url.rstrip("/") + "/v1",
    )
    MODEL = settings.ollama_chat_model
else:  # default: gemini
    client = AsyncOpenAI(
        api_key=settings.gemini_api_key,
        base_url=settings.gemini_base_url,
    )
    MODEL = settings.llm_model


async def chat(
    messages: list[dict],
    tools: list[dict] | None = None,
    tool_choice: str = "auto",
    temperature: float = 0.2,
):
    """Single chat completion. Returns the raw OpenAI-style response object.

    When `tools` is provided, the model may respond with tool_calls instead of
    content — the agent loop inspects that and dispatches accordingly.
    """
    kwargs: dict = {
        "model": MODEL,
        "messages": messages,
        "temperature": temperature,
    }
    if tools:
        kwargs["tools"] = tools
        kwargs["tool_choice"] = tool_choice

    return await client.chat.completions.create(**kwargs)
