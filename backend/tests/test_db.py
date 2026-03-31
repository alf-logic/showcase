"""Tests for the SQLite DB layer."""

import json
from pathlib import Path

import pytest

from db import DB


@pytest.fixture()
def db(tmp_path: Path) -> DB:
    return DB(db_path=tmp_path / "test.db")


def test_create_and_get_run(db: DB) -> None:
    run_id: str = db.create_run("/some/repo", "/tmp/clone", budget_limit=2.0)
    run = db.get_run(run_id)
    assert run is not None
    assert run["repo_url"] == "/some/repo"
    assert run["clone_path"] == "/tmp/clone"
    assert run["status"] == "pending"
    assert run["budget_limit_usd"] == 2.0
    assert run["budget_used_usd"] == 0.0


def test_update_run_status(db: DB) -> None:
    run_id: str = db.create_run("/repo", "/tmp/clone")
    db.update_run_status(run_id, "running")
    run = db.get_run(run_id)
    assert run is not None
    assert run["status"] == "running"


def test_budget_tracking(db: DB) -> None:
    run_id: str = db.create_run("/repo", "/tmp/clone", budget_limit=2.0)
    assert db.get_remaining_budget(run_id) == 2.0

    db.update_run_budget(run_id, 0.50)
    assert db.get_remaining_budget(run_id) == pytest.approx(1.50)

    db.update_run_budget(run_id, 1.00)
    assert db.get_remaining_budget(run_id) == pytest.approx(0.50)


def test_create_and_get_function(db: DB) -> None:
    run_id: str = db.create_run("/repo", "/tmp/clone")
    fn_id: str = db.create_function(run_id, "hash_key", "hashmap/hashmap.py", 15, json.dumps(["key", "capacity"]))

    fn = db.get_function(fn_id)
    assert fn is not None
    assert fn["name"] == "hash_key"
    assert fn["file"] == "hashmap/hashmap.py"
    assert fn["status"] == "pending"


def test_function_status_transitions(db: DB) -> None:
    run_id: str = db.create_run("/repo", "/tmp/clone")
    fn_id: str = db.create_function(run_id, "get", "hashmap/hashmap.py", 57)

    # Walk through the full pipeline
    db.update_function_status(fn_id, "l1_in_progress")
    assert db.get_function(fn_id)["status"] == "l1_in_progress"

    db.update_function_status(fn_id, "l1_done")
    assert db.get_function(fn_id)["status"] == "l1_done"

    db.update_function_status(fn_id, "l2_in_progress")
    db.update_function_status(fn_id, "l2_done")

    db.update_function_status(fn_id, "l3_in_progress")
    db.update_function_status(fn_id, "bug_suspect", reason="off-by-one in probe loop")

    fn = db.get_function(fn_id)
    assert fn["status"] == "bug_suspect"
    assert fn["status_reason"] == "off-by-one in probe loop"


def test_function_spec_and_tests(db: DB) -> None:
    run_id: str = db.create_run("/repo", "/tmp/clone")
    fn_id: str = db.create_function(run_id, "hash_key", "hashmap/hashmap.py", 15)

    db.update_function_spec(fn_id, "Feature: hash_key\n  Scenario: basic")
    db.update_function_tests(fn_id, "def test_hash_key(): ...", "PASSED")

    fn = db.get_function(fn_id)
    assert fn["spec_text"] == "Feature: hash_key\n  Scenario: basic"
    assert fn["test_code"] == "def test_hash_key(): ..."
    assert fn["test_output"] == "PASSED"


def test_get_functions_for_run(db: DB) -> None:
    run_id: str = db.create_run("/repo", "/tmp/clone")
    db.create_function(run_id, "hash_key", "hashmap/hashmap.py", 15)
    db.create_function(run_id, "split_file", "chunker/chunker.py", 12)

    fns = db.get_functions_for_run(run_id)
    assert len(fns) == 2
    names: set[str] = {f["name"] for f in fns}
    assert names == {"hash_key", "split_file"}


def test_agent_logs(db: DB) -> None:
    run_id: str = db.create_run("/repo", "/tmp/clone")
    fn_id: str = db.create_function(run_id, "hash_key", "hashmap/hashmap.py", 15)

    db.add_agent_log(run_id, fn_id, "l1", "system", "Generate specs...", model="gpt-4o-mini", tokens_used=100, cost_usd=0.001)
    db.add_agent_log(run_id, fn_id, "l1", "assistant", "Feature: hash_key...", model="gpt-4o-mini", tokens_used=200, cost_usd=0.002)

    logs = db.get_agent_logs(fn_id)
    assert len(logs) == 2
    assert logs[0]["role"] == "system"
    assert logs[1]["role"] == "assistant"
    assert logs[0]["layer"] == "l1"

    all_logs = db.get_all_agent_logs(run_id)
    assert len(all_logs) == 2


def test_git_operations(db: DB) -> None:
    run_id: str = db.create_run("/repo", "/tmp/clone")
    fn_id: str = db.create_function(run_id, "hash_key", "hashmap/hashmap.py", 15)

    db.add_git_operation(run_id, fn_id, "create_branch", branch_name="spec/l1/hash_key")
    db.add_git_operation(
        run_id, fn_id, "commit",
        branch_name="spec/l1/hash_key",
        commit_sha="abc123",
        commit_message="Add spec for hash_key",
        diff="+ Feature: hash_key",
        parent_sha="000000",
    )
    db.add_git_operation(
        run_id, None, "merge",
        branch_name="spec/l1/hash_key",
        commit_sha="def456",
        commit_message="Merge spec/l1/hash_key into main",
        parent_sha="abc123",
    )

    ops = db.get_git_operations(run_id)
    assert len(ops) == 3
    assert ops[0]["operation"] == "create_branch"
    assert ops[1]["operation"] == "commit"
    assert ops[1]["commit_sha"] == "abc123"
    assert ops[2]["operation"] == "merge"
