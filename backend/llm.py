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


class MockLLMClient:
    """Deterministic mock that returns predefined responses. No API calls."""

    def __init__(self, model: str = "mock") -> None:
        self.model: str = model
        self._call_count: int = 0

    def chat(
        self,
        messages: list[dict[str, str]],
        temperature: float = 0.3,
        max_tokens: int = 4096,
    ) -> LLMResponse:
        """Return predefined response based on the user message content."""
        from mock_responses import get_mock_response

        user_msg: str = ""
        for msg in messages:
            if msg["role"] == "user":
                user_msg = msg["content"]
                break

        # Extract function name from the user message
        function_name: str = self._extract_function_name(user_msg)

        # Determine layer from system message
        system_msg: str = ""
        for msg in messages:
            if msg["role"] == "system":
                system_msg = msg["content"]
                break

        if "specification agent" in system_msg.lower() or "spec generation" in system_msg.lower():
            layer = "l1"
        elif "specification reviewer" in system_msg.lower() or "review" in system_msg.lower():
            layer = "l2"
        elif "test generation" in system_msg.lower():
            layer = "l3"
        else:
            layer = "l1"

        content: str = get_mock_response(function_name, layer)
        if not content:
            content = f"Feature: {function_name}\n  Scenario: placeholder\n    When called\n    Then it works"

        self._call_count += 1
        output_tokens: int = len(content.split())
        return LLMResponse(
            content=content,
            model=self.model,
            input_tokens=200,
            output_tokens=output_tokens,
            total_tokens=200 + output_tokens,
            cost_usd=0.0001,
        )

    def _extract_function_name(self, user_msg: str) -> str:
        """Extract function name from user message."""
        # Pattern: "for `function_name` from" or "for `function_name`"
        import re
        match = re.search(r'`(\w+)`\s+from', user_msg)
        if match:
            return match.group(1)
        match = re.search(r'`(\w+)`', user_msg)
        if match:
            return match.group(1)
        # Fallback: look for "def function_name"
        match = re.search(r'def (\w+)\(', user_msg)
        if match:
            return match.group(1)
        return "unknown"


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
