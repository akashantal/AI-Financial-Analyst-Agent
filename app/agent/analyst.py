"""The analyst agent — a Gemini function-calling loop.

Flow:
  1. Send the user's question + tool schemas to Gemini.
  2. If Gemini asks for tool calls, run them (concurrently) and feed results back.
  3. Repeat up to `agent_max_steps`, then force a final text briefing.

Indicators/quotes are computed by our services, so the model grounds every number
in real data instead of inventing it.
"""
from __future__ import annotations

import json

import structlog

from app.agent import tools
from app.config import settings
from app.services import llm

logger = structlog.get_logger()

SYSTEM_PROMPT = (
    "You are a financial-markets research assistant. Use the provided tools to gather "
    "live market data, indicators, fundamentals, and news before answering. "
    "Ground EVERY numeric claim in tool output — never estimate or invent figures. "
    "Write a concise analyst-style briefing: what the data shows, momentum/valuation "
    "context, and notable risks. "
    "You are NOT a financial advisor: do not give buy/sell recommendations or price targets. "
    "End every briefing with: 'This is research, not investment advice.'"
)


async def run(question: str) -> dict:
    """Run the agent loop and return the briefing plus a trace of tools used."""
    messages: list[dict] = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": question},
    ]
    tools_called: list[str] = []
    tickers_seen: list[str] = []

    for step in range(settings.agent_max_steps):
        response = await llm.chat(messages, tools=tools.TOOL_SCHEMAS)
        msg = response.choices[0].message

        # No tool calls → the model produced its final briefing.
        if not msg.tool_calls:
            logger.info("agent.done", steps=step, tools=tools_called)
            return {
                "question": question,
                "briefing": msg.content or "",
                "tools_called": tools_called,
                "tickers": tickers_seen,
                "steps": step,
            }

        # Record the assistant turn (with its tool-call requests) verbatim.
        messages.append({
            "role": "assistant",
            "content": msg.content,
            "tool_calls": [
                {
                    "id": tc.id,
                    "type": "function",
                    "function": {"name": tc.function.name, "arguments": tc.function.arguments},
                }
                for tc in msg.tool_calls
            ],
        })

        # Execute each requested tool and append its result.
        for tc in msg.tool_calls:
            name = tc.function.name
            try:
                args = json.loads(tc.function.arguments or "{}")
            except json.JSONDecodeError:
                args = {}
            tools_called.append(name)
            # Track tickers the agent touched (for memory tagging).
            if isinstance(args.get("ticker"), str):
                tickers_seen.append(args["ticker"].upper())
            for tk in args.get("tickers", []) if isinstance(args.get("tickers"), list) else []:
                if isinstance(tk, str):
                    tickers_seen.append(tk.upper())
            result = await tools.dispatch(name, args)
            logger.info("agent.tool", step=step, tool=name, args=args)
            messages.append({
                "role": "tool",
                "tool_call_id": tc.id,
                "content": json.dumps(result, default=str),
            })

    # Hit the step cap — ask for a final answer using whatever was gathered.
    messages.append({
        "role": "user",
        "content": "Summarize your findings now as the final briefing.",
    })
    final = await llm.chat(messages)
    logger.info("agent.forced_final", tools=tools_called)
    return {
        "question": question,
        "briefing": final.choices[0].message.content or "",
        "tools_called": tools_called,
        "tickers": tickers_seen,
        "steps": settings.agent_max_steps,
    }
