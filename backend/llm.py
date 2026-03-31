"""OpenAI API wrapper with cost tracking and budget enforcement."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv
from openai import OpenAI

# Load .env from project root
load_dotenv(Path(__file__).parent.parent / ".env")

# Pricing per 1M tokens (as of 2026-03, gpt-4o-mini)
PRICING: dict[str, dict[str, float]] = {
    "gpt-4o-mini": {"input": 0.15, "output": 0.60},
    "gpt-4o": {"input": 2.50, "output": 10.00},
    "gpt-4.1-mini": {"input": 0.40, "output": 1.60},
    "gpt-4.1-nano": {"input": 0.10, "output": 0.40},
}

DEFAULT_MODEL: str = "gpt-4o-mini"


class BudgetExceededError(Exception):
    """Raised when a pipeline run's budget is exhausted."""


@dataclass
class LLMResponse:
    content: str
    model: str
    input_tokens: int
    output_tokens: int
    total_tokens: int
    cost_usd: float


def _calculate_cost(model: str, input_tokens: int, output_tokens: int) -> float:
    prices = PRICING.get(model, PRICING[DEFAULT_MODEL])
    input_cost: float = (input_tokens / 1_000_000) * prices["input"]
    output_cost: float = (output_tokens / 1_000_000) * prices["output"]
    return input_cost + output_cost


class LLMClient:
    """OpenAI chat completion client with budget tracking."""

    def __init__(self, model: str = DEFAULT_MODEL) -> None:
        api_key: str | None = os.environ.get("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OPENAI_API_KEY not set")
        self.client: OpenAI = OpenAI(api_key=api_key)
        self.model: str = model

    def chat(
        self,
        messages: list[dict[str, str]],
        temperature: float = 0.3,
        max_tokens: int = 4096,
    ) -> LLMResponse:
        """Make a chat completion call and return structured response with cost."""
        response = self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
        )

        choice = response.choices[0]
        usage = response.usage
        input_tokens: int = usage.prompt_tokens if usage else 0
        output_tokens: int = usage.completion_tokens if usage else 0
        total_tokens: int = usage.total_tokens if usage else 0
        cost: float = _calculate_cost(self.model, input_tokens, output_tokens)

        return LLMResponse(
            content=choice.message.content or "",
            model=self.model,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            total_tokens=total_tokens,
            cost_usd=cost,
        )


def check_budget_and_call(
    llm: LLMClient,
    db: "DB",
    run_id: str,
    messages: list[dict[str, str]],
    temperature: float = 0.3,
    max_tokens: int = 4096,
) -> LLMResponse:
    """Check budget before calling LLM, update budget after."""
    from db import DB

    remaining: float = db.get_remaining_budget(run_id)
    if remaining <= 0:
        raise BudgetExceededError(f"Budget exhausted for run {run_id}")

    response: LLMResponse = llm.chat(messages, temperature=temperature, max_tokens=max_tokens)
    db.update_run_budget(run_id, response.cost_usd)
    return response
