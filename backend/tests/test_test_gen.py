"""Tests for L3 test generation + execution agent."""

from pathlib import Path

import pytest

from agents.spec_gen import run_l1
from agents.spec_refine import run_l2
from agents.test_gen import run_l3
from db import DB
from git_model import GitModel
from llm import LLMClient

# We need the showcase-example repo cloned for running generated tests.
SHOWCASE_EXAMPLE_PATH: str = "/Users/alexfetisov/dev/showcase-example"

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
    run_id: str = db.create_run(SHOWCASE_EXAMPLE_PATH, SHOWCASE_EXAMPLE_PATH, budget_limit=2.0)
    try:
        llm: LLMClient = LLMClient(model="gpt-4o-mini")
    except ValueError:
        pytest.skip("OPENAI_API_KEY not set")
    git: GitModel = GitModel(db, run_id)
    return db, llm, git, run_id


def test_l3_hash_key_produces_passing_tests(setup: tuple[DB, LLMClient, GitModel, str]) -> None:
    db, llm, git, run_id = setup
    fn_id: str = db.create_function(run_id, "hash_key", "hashmap/hashmap.py", 15)

    # L1 + L2
    spec: str | None = run_l1(db, llm, git, run_id, fn_id, "hash_key", HASH_KEY_SOURCE, "hashmap/hashmap.py")
    assert spec is not None
    refined, accepted = run_l2(db, llm, git, run_id, fn_id, "hash_key", HASH_KEY_SOURCE, spec, "hashmap/hashmap.py")
    assert accepted is True
    assert refined is not None

    # L3 — LLM output is non-deterministic, so we allow up to 2 attempts
    status: str = "test_failed"
    for attempt in range(2):
        fn_id_attempt: str = fn_id if attempt == 0 else db.create_function(run_id, "hash_key", "hashmap/hashmap.py", 15)
        if attempt > 0:
            db.update_function_spec(fn_id_attempt, refined)
            db.update_function_status(fn_id_attempt, "l2_done")
            git.create_branch(f"spec/hash_key_retry{attempt}", function_id=fn_id_attempt)
        status = run_l3(
            db, llm, git, run_id, fn_id_attempt, "hash_key", HASH_KEY_SOURCE, refined,
            "hashmap/hashmap.py", SHOWCASE_EXAMPLE_PATH,
        )
        if status == "covered":
            break

    assert status == "covered", f"hash_key should be covered after retries, got: {status}"
    fn = db.get_function(fn_id_attempt)
    assert fn["test_code"] is not None
    assert fn["test_output"] is not None


def test_l3_get_detects_bug(setup: tuple[DB, LLMClient, GitModel, str]) -> None:
    db, llm, git, run_id = setup
    fn_id: str = db.create_function(run_id, "get", "hashmap/hashmap.py", 57)

    # L1 + L2
    spec: str | None = run_l1(db, llm, git, run_id, fn_id, "get", GET_SOURCE, "hashmap/hashmap.py")
    assert spec is not None
    refined, accepted = run_l2(db, llm, git, run_id, fn_id, "get", GET_SOURCE, spec, "hashmap/hashmap.py")
    assert accepted is True
    assert refined is not None

    # L3 — should detect the off-by-one bug
    status: str = run_l3(
        db, llm, git, run_id, fn_id, "get", GET_SOURCE, refined,
        "hashmap/hashmap.py", SHOWCASE_EXAMPLE_PATH,
    )

    # Could be bug_suspect or test_failed depending on how the model writes the test
    assert status in ("bug_suspect", "test_failed"), f"Expected failure but got: {status}"
    fn = db.get_function(fn_id)
    assert fn["status"] in ("bug_suspect", "test_failed")
