"""Tests for L2 spec refinement agent."""

from pathlib import Path

import pytest

from agents.spec_gen import run_l1
from agents.spec_refine import run_l2
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

RESIZE_SOURCE: str = '''def resize(table: list[list], new_capacity: int) -> list[list]:
    """Resize the hash table to a new capacity, rehashing all entries."""
    if new_capacity < 1:
        raise ValueError("capacity must be positive")
    new_table: list = [EMPTY] * new_capacity
    migrated: int = 0
    skipped: int = 0
    for slot in table:
        if slot is EMPTY or slot is DELETED:
            skipped += 1
            continue
        key: str = slot[0]
        value: Any = slot[1]
        idx: int = hash_key(key, new_capacity)
        for _ in range(new_capacity):
            if new_table[idx] is EMPTY:
                new_table[idx] = [key, value]
                migrated += 1
                break
            idx = (idx + 1) % new_capacity
        else:
            raise RuntimeError(f"no space for key {key!r} during resize")
    load_factor: float = migrated / new_capacity if new_capacity > 0 else 0.0
    if load_factor > 0.75:
        raise ValueError(f"resize target too small: load factor {load_factor:.2f} > 0.75")
    return new_table
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


def test_l2_accepts_simple_function(setup: tuple[DB, LLMClient, GitModel, str]) -> None:
    db, llm, git, run_id = setup
    fn_id: str = db.create_function(run_id, "hash_key", "hashmap/hashmap.py", 15)

    # Run L1 first
    l1_spec: str | None = run_l1(db, llm, git, run_id, fn_id, "hash_key", HASH_KEY_SOURCE, "hashmap/hashmap.py")
    assert l1_spec is not None

    # Run L2
    refined, accepted = run_l2(db, llm, git, run_id, fn_id, "hash_key", HASH_KEY_SOURCE, l1_spec, "hashmap/hashmap.py")

    assert accepted is True
    assert refined is not None
    assert "Feature:" in refined

    fn = db.get_function(fn_id)
    assert fn["status"] == "l2_done"


def test_l2_rejects_complex_function(setup: tuple[DB, LLMClient, GitModel, str]) -> None:
    db, llm, git, run_id = setup
    fn_id: str = db.create_function(run_id, "resize", "hashmap/hashmap.py", 78)

    # Run L1 first
    l1_spec: str | None = run_l1(db, llm, git, run_id, fn_id, "resize", RESIZE_SOURCE, "hashmap/hashmap.py")
    assert l1_spec is not None

    # Run L2 — should reject
    refined, accepted = run_l2(db, llm, git, run_id, fn_id, "resize", RESIZE_SOURCE, l1_spec, "hashmap/hashmap.py")

    assert accepted is False
    assert refined is None

    fn = db.get_function(fn_id)
    assert fn["status"] == "needs_refactor"
    assert fn["status_reason"] is not None
