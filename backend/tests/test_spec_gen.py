"""Tests for L1 spec generation agent."""

from pathlib import Path

import pytest

from agents.spec_gen import run_l1
from db import DB
from git_model import GitModel
from llm import LLMClient

HASH_KEY_SOURCE: str = '''def hash_key(key: str, capacity: int) -> int:
    """Compute a deterministic hash index for a string key."""
    h: int = 0x811C9DC5
    for byte in key.encode("utf-8"):
        h ^= byte
        h = (h * 0x01000193) & 0xFFFFFFFF
    return h % capacity
'''

GET_SOURCE: str = '''def get(table: list[list], key: str) -> Any:
    """Retrieve a value by key using linear probing."""
    capacity: int = len(table)
    idx: int = hash_key(key, capacity)

    for _ in range(capacity - 1):  # BUG: should be range(capacity)
        slot = table[idx]
        if slot is EMPTY:
            break
        if slot is not DELETED and slot[0] == key:
            return slot[1]
        idx = (idx + 1) % capacity

    raise KeyError(key)
'''


@pytest.fixture()
def setup(tmp_path: Path) -> tuple[DB, LLMClient, GitModel, str]:
    db: DB = DB(db_path=tmp_path / "test.db")
    run_id: str = db.create_run("/repo", "/tmp/clone", budget_limit=2.0)
    try:
        llm: LLMClient = LLMClient(model="gpt-4o-mini")
    except ValueError:
        pytest.skip("OPENAI_API_KEY not set")
    git: GitModel = GitModel(db, run_id)
    return db, llm, git, run_id


def test_l1_hash_key_produces_valid_spec(setup: tuple[DB, LLMClient, GitModel, str]) -> None:
    db, llm, git, run_id = setup
    fn_id: str = db.create_function(run_id, "hash_key", "hashmap/hashmap.py", 15)

    spec: str | None = run_l1(db, llm, git, run_id, fn_id, "hash_key", HASH_KEY_SOURCE, "hashmap/hashmap.py")

    assert spec is not None
    assert "Feature:" in spec
    assert "Scenario:" in spec
    assert "hash_key" in spec.lower() or "hash" in spec.lower()

    # Check DB state
    fn = db.get_function(fn_id)
    assert fn["status"] == "l1_done"
    assert fn["spec_text"] is not None

    # Check agent logs
    logs = db.get_agent_logs(fn_id)
    assert len(logs) >= 3  # system + user + assistant

    # Check git operations
    assert "spec/hash_key" in git.get_branch_names()


def test_l1_get_mentions_probing(setup: tuple[DB, LLMClient, GitModel, str]) -> None:
    db, llm, git, run_id = setup
    fn_id: str = db.create_function(run_id, "get", "hashmap/hashmap.py", 57)

    spec: str | None = run_l1(db, llm, git, run_id, fn_id, "get", GET_SOURCE, "hashmap/hashmap.py")

    assert spec is not None
    # The spec should mention probing or loop behavior
    spec_lower: str = spec.lower()
    assert any(word in spec_lower for word in ["probe", "loop", "search", "slot", "key"]), f"Spec doesn't mention probing: {spec}"
