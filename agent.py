"""Optional OpenRouter agent that selects and calls local finance analysis tools."""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

import pandas as pd
from dotenv import load_dotenv

from finance_tools import create_saving_plan, get_spending_insights, query_transactions

ROOT = Path(__file__).resolve().parent
load_dotenv(ROOT / ".env")
MODEL_NAME = os.getenv("FINANCE_AGENT_MODEL", "openai/gpt-4.1-mini")
OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"
MINIMUM_TOOL_CALLS = 2


def _schema(name: str, description: str, properties: dict[str, Any], required: list[str]) -> dict[str, Any]:
    return {"type": "function", "function": {"name": name, "description": description, "parameters": {"type": "object", "properties": properties, "required": required, "additionalProperties": False}}}


MONTH = {"type": "string", "description": "Billing month in YYYY-MM."}
AGENT_TOOL_SCHEMAS = [
    _schema("query_transactions", "Read the selected month's local statement. Filter by category or merchant text, then return the largest matching transactions or group spending by category, merchant, or date. Use it to investigate a specific question.", {
        "month": MONTH,
        "category": {"type": "string", "description": "Optional exact budget category, for example Food and Dining or Lifestyle and Social."},
        "merchant_contains": {"type": "string", "description": "Optional text to find in merchant names."},
        "group_by": {"type": "string", "enum": ["transaction", "category", "merchant", "date"], "description": "How to present the matching rows."},
        "limit": {"type": "integer", "minimum": 1, "maximum": 20, "description": "Maximum returned items."},
    }, ["month"]),
    _schema("get_spending_insights", "Get a deterministic whole-month overview: total, category totals and shares, five largest transactions, and comparison with the UI monthly spending limit.", {"month": MONTH}, ["month"]),
    _schema("create_saving_plan", "Create a deterministic plan for the UI saving target. Categories marked to keep in the UI are excluded. Call only when the user asks for a saving or reduction recommendation.", {"month": MONTH}, ["month"]),
]


def _execute(name: str, arguments: dict[str, Any], frame: pd.DataFrame, maximum_spending: float, saving_target: float, protected_categories: list[str]) -> dict[str, Any]:
    if name == "query_transactions":
        return query_transactions(frame, **arguments)
    if name == "get_spending_insights":
        return get_spending_insights(frame, arguments["month"], maximum_spending)
    if name == "create_saving_plan":
        return create_saving_plan(frame, arguments["month"], saving_target, protected_categories)
    raise ValueError(f"Unknown agent tool: {name}")


def _system_prompt(context: dict[str, Any]) -> str:
    return (
        "Role: You are a thoughtful personal-finance analysis agent for one selected local statement month. Reply in English unless the user explicitly requests another language. "
        "Decision making: You decide which tools to call and in which order. Before answering, collect at least two complementary tool observations; do not repeat an identical tool call merely to meet this requirement. "
        "Evidence: All claims about transaction amounts, categories, merchants, dates, budget status, or saving capacity must come from a local tool result in this conversation. Never invent a transaction, category, cause, or amount. Do not alter UI constraints. "
        "Tool strategy: For a simple factual question, one relevant tool may be enough. Use get_spending_insights for a monthly overview or budget question. Use query_transactions to investigate a category, merchant, date, or unusually large transaction. Use create_saving_plan only if the user explicitly asks for a saving or reduction recommendation. "
        "Complex analysis: For why, diagnosis, comparison, or recommendation questions, conduct a multi-step investigation. Start with get_spending_insights, then use query_transactions to inspect the evidence behind the largest or relevant spending. For a saving request, inspect evidence before create_saving_plan, and never recommend reducing categories the user marked to keep. "
        "Interpretation: Most Lifestyle and Social spending may reflect social or entertainment activity, but never assume every transfer or item in that category has that meaning. State uncertainty when descriptions do not support a confident conclusion. "
        "Final response: Give (1) a direct conclusion, (2) 2–4 evidence points with SGD amounts, (3) specific practical next actions when useful, and (4) one short limitation or caveat when the data is ambiguous. Do not mention internal tool names unless the user asks. Keep personal names and unnecessary raw transaction descriptions out of the answer. This is budgeting information, not professional financial advice. "
        "Current UI context: " + json.dumps(context, ensure_ascii=False)
    )


def run_openrouter_agent(query: str, frame: pd.DataFrame, month: str, maximum_spending: float, saving_target: float, protected_categories: list[str], history: list[dict[str, str]] | None = None) -> dict[str, Any]:
    """Run a bounded OpenRouter client-tool loop against the selected local statement."""
    api_key = os.getenv("OPENROUTER_API_KEY")
    if not api_key:
        raise RuntimeError("OPENROUTER_API_KEY is missing. Create .env from .env.example, then restart Streamlit.")
    if not query.strip():
        raise ValueError("Enter a question for the agent.")
    from openai import OpenAI

    context = {"selected_month": month, "maximum_monthly_spending_sgd": maximum_spending, "saving_target_sgd": saving_target, "protected_budget_categories": protected_categories}
    system = _system_prompt(context)
    client = OpenAI(base_url=OPENROUTER_BASE_URL, api_key=api_key, default_headers={"X-OpenRouter-Title": "Personal Finance Statement Agent"})
    safe_history = [
        {"role": item["role"], "content": item["content"]}
        for item in (history or [])
        if item.get("role") in {"user", "assistant"} and item.get("content")
    ]
    messages: list[dict[str, Any]] = [{"role": "system", "content": system}, *safe_history, {"role": "user", "content": query}]
    trace: list[dict[str, Any]] = []
    total_tokens = 0
    for _ in range(6):
        # The model selects the tools and their order. The loop requires two
        # observations so a response is based on investigation rather than one
        # isolated aggregate; after that the model decides whether to continue.
        tool_choice: Any = "required" if len(trace) < MINIMUM_TOOL_CALLS else "auto"
        response = client.chat.completions.create(model=MODEL_NAME, messages=messages, tools=AGENT_TOOL_SCHEMAS, tool_choice=tool_choice, parallel_tool_calls=tool_choice == "auto")
        if response.usage and response.usage.total_tokens:
            total_tokens += response.usage.total_tokens
        message = response.choices[0].message
        calls = list(message.tool_calls or [])
        if not calls:
            if len(trace) < MINIMUM_TOOL_CALLS:
                raise RuntimeError("The agent stopped before completing its minimum two-step investigation.")
            return {"answer": message.content or "The agent finished after the requested analysis.", "tool_trace": trace, "total_tokens": total_tokens, "model": MODEL_NAME}
        messages.append({"role": "assistant", "content": message.content or "", "tool_calls": [{"id": call.id, "type": "function", "function": {"name": call.function.name, "arguments": call.function.arguments}} for call in calls]})
        for call in calls:
            arguments: dict[str, Any] = {}
            try:
                arguments = json.loads(call.function.arguments)
                result = _execute(call.function.name, arguments, frame, maximum_spending, saving_target, protected_categories)
            except Exception as error:
                result = {"error": str(error)}
            trace.append({"tool": call.function.name, "arguments": arguments, "result": result})
            messages.append({"role": "tool", "tool_call_id": call.id, "content": json.dumps(result, ensure_ascii=False)})
    raise RuntimeError("Agent stopped after six tool-calling rounds.")
