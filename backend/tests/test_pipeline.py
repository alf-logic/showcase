"""Integration test for the full pipeline orchestrator.

This runs real OpenAI API calls on all 10 functions. It's expensive (~$0.10-0.30)
and takes 2-5 minutes, so it's marked as slow.
"""

from pathlib import Path
from typing import Any

import pytest

from db import DB
from pipeline import run_pipeline

SHOWCASE_EXAMPLE_PATH: str = "/Users/alexfetisov/dev/showcase-example"

# Expected outcomes (some may vary due to LLM non-determinism)
EXPECTED_COVERED: set[str] = {"hash_key", "put", "delete", "split_file", "calculate_boundaries", "validate_checksum"}
EXPECTED_BUG_SUSPECT: set[str] = {"get", "merge_chunks"}
EXPECTED_NEEDS_REFACTOR: set[str] = {"resize"}
EXPECTED_FAILURES: set[str] = {"handle_partial_chunk"}


@pytest.fixture()
def db(tmp_path: Path) -> DB:
    return DB(db_path=tmp_path / "test.db")


@pytest.mark.slow
def test_full_pipeline_10_functions(db: DB) -> None:
    """Run the full pipeline and check results."""
    try:
        from llm import LLMClient
        LLMClient(model="gpt-4o-mini")
    except ValueError:
        pytest.skip("OPENAI_API_KEY not set")

    run_id: str = db.create_run(SHOWCASE_EXAMPLE_PATH, SHOWCASE_EXAMPLE_PATH, budget_limit=2.0)

    events: list[dict[str, Any]] = []
    def collect_event(event: dict[str, Any]) -> None:
        events.append(event)

    results: dict[str, str] = run_pipeline(db, run_id, SHOWCASE_EXAMPLE_PATH, on_event=collect_event)

    # Basic sanity checks
    assert len(results) == 10, f"Expected 10 functions, got {len(results)}: {results}"

    # Check run completed
    run = db.get_run(run_id)
    assert run["status"] == "completed"
    assert run["budget_used_usd"] > 0
    assert run["budget_used_usd"] <= 2.0

    # Check we got events
    event_types: set[str] = {e["type"] for e in events}
    assert "pipeline_start" in event_types
    assert "pipeline_complete" in event_types
    assert "function_start" in event_types

    # Check function statuses in DB
    functions = db.get_functions_for_run(run_id)
    assert len(functions) == 10

    status_counts: dict[str, int] = {}
    for fn in functions:
        status: str = fn["status"]
        status_counts[status] = status_counts.get(status, 0) + 1
        print(f"  {fn['name']:30s} → {status}")

    # At minimum: resize should be needs_refactor (strong directional prompt)
    resize_fn = [f for f in functions if f["name"] == "resize"]
    assert len(resize_fn) == 1
    assert resize_fn[0]["status"] == "needs_refactor", f"resize should be needs_refactor, got: {resize_fn[0]['status']}"

    # Check agent logs exist
    all_logs = db.get_all_agent_logs(run_id)
    assert len(all_logs) > 20, f"Expected 20+ agent log entries, got {len(all_logs)}"

    # Check git operations exist
    git_ops = db.get_git_operations(run_id)
    assert len(git_ops) > 10, f"Expected 10+ git operations, got {len(git_ops)}"

    print(f"\nBudget used: ${run['budget_used_usd']:.4f} / ${run['budget_limit_usd']:.2f}")
    print(f"Status distribution: {status_counts}")
    print(f"Agent log entries: {len(all_logs)}")
    print(f"Git operations: {len(git_ops)}")
