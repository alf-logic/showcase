"""Tests for OpenAI client and budget tracking."""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from db import DB
from llm import (
    BudgetExceededError,
    LLMClient,
    LLMResponse,
    _calculate_cost,
    check_budget_and_call,
)


def test_cost_calculation_gpt4o_mini() -> None:
    # 1000 input + 500 output tokens with gpt-4o-mini
    cost: float = _calculate_cost("gpt-4o-mini", 1000, 500)
    expected: float = (1000 / 1_000_000) * 0.15 + (500 / 1_000_000) * 0.60
    assert cost == pytest.approx(expected)


def test_cost_calculation_gpt4o() -> None:
    cost: float = _calculate_cost("gpt-4o", 1000, 500)
    expected: float = (1000 / 1_000_000) * 2.50 + (500 / 1_000_000) * 10.00
    assert cost == pytest.approx(expected)


def test_real_api_call() -> None:
    """One real API call to verify the client works."""
    try:
        client: LLMClient = LLMClient(model="gpt-4o-mini")
    except ValueError:
        pytest.skip("OPENAI_API_KEY not set")

    response: LLMResponse = client.chat(
        messages=[{"role": "user", "content": "Say exactly: hello"}],
        max_tokens=10,
    )
    assert "hello" in response.content.lower()
    assert response.input_tokens > 0
    assert response.output_tokens > 0
    assert response.cost_usd > 0
    assert response.model == "gpt-4o-mini"


def test_budget_exceeded_blocks_call(tmp_path: Path) -> None:
    db: DB = DB(db_path=tmp_path / "test.db")
    run_id: str = db.create_run("/repo", "/tmp/clone", budget_limit=0.01)
    # Exhaust the budget
    db.update_run_budget(run_id, 0.01)

    mock_llm: MagicMock = MagicMock(spec=LLMClient)
    with pytest.raises(BudgetExceededError):
        check_budget_and_call(mock_llm, db, run_id, [{"role": "user", "content": "hi"}])

    # LLM should never have been called
    mock_llm.chat.assert_not_called()


def test_budget_updated_after_call(tmp_path: Path) -> None:
    db: DB = DB(db_path=tmp_path / "test.db")
    run_id: str = db.create_run("/repo", "/tmp/clone", budget_limit=2.0)

    mock_response: LLMResponse = LLMResponse(
        content="hello", model="gpt-4o-mini",
        input_tokens=100, output_tokens=50,
        total_tokens=150, cost_usd=0.05,
    )
    mock_llm: MagicMock = MagicMock(spec=LLMClient)
    mock_llm.chat.return_value = mock_response

    result: LLMResponse = check_budget_and_call(mock_llm, db, run_id, [{"role": "user", "content": "hi"}])
    assert result.content == "hello"
    assert db.get_remaining_budget(run_id) == pytest.approx(1.95)
