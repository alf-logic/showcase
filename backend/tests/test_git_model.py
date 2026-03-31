"""Tests for in-memory git model."""

from pathlib import Path

import pytest

from db import DB
from git_model import GitModel


@pytest.fixture()
def setup(tmp_path: Path) -> tuple[DB, str]:
    db: DB = DB(db_path=tmp_path / "test.db")
    run_id: str = db.create_run("/repo", "/tmp/clone")
    return db, run_id


def test_initial_state(setup: tuple[DB, str]) -> None:
    db, run_id = setup
    git: GitModel = GitModel(db, run_id)

    assert "main" in git.get_branch_names()
    graph = git.get_graph()
    assert len(graph["commits"]) == 1
    assert graph["commits"][0]["message"] == "Initial commit"
    assert len(graph["branches"]) == 1


def test_branch_and_commit(setup: tuple[DB, str]) -> None:
    db, run_id = setup
    git: GitModel = GitModel(db, run_id)

    git.create_branch("spec/l1/hash_key")
    sha1: str = git.commit("spec/l1/hash_key", "Add spec for hash_key", "+ Feature: hash_key")
    sha2: str = git.commit("spec/l1/hash_key", "Refine spec", "+ Rule: ...")

    assert len(git.get_branch_names()) == 2
    graph = git.get_graph()
    # initial + 2 commits = 3
    assert len(graph["commits"]) == 3

    c1 = git.get_commit(sha1)
    c2 = git.get_commit(sha2)
    assert c1 is not None
    assert c2 is not None
    assert c2.parent_shas == [sha1]
    assert c1.diff == "+ Feature: hash_key"


def test_merge_creates_two_parent_commit(setup: tuple[DB, str]) -> None:
    db, run_id = setup
    git: GitModel = GitModel(db, run_id)

    git.create_branch("spec/l1/hash_key")
    git.commit("spec/l1/hash_key", "Add spec", "diff")

    merge_sha: str = git.merge("spec/l1/hash_key", "main")
    merge_commit = git.get_commit(merge_sha)

    assert merge_commit is not None
    assert len(merge_commit.parent_shas) == 2
    assert "Merge spec/l1/hash_key into main" == merge_commit.message


def test_full_workflow_graph(setup: tuple[DB, str]) -> None:
    """Simulate processing 2 functions through the pipeline."""
    db, run_id = setup
    git: GitModel = GitModel(db, run_id)

    # Function 1: hash_key
    git.create_branch("spec/hash_key")
    git.commit("spec/hash_key", "L1: spec for hash_key", "spec diff")
    git.commit("spec/hash_key", "L2: refined spec", "refined diff")
    git.commit("spec/hash_key", "L3: tests for hash_key", "test diff")
    git.merge("spec/hash_key")

    # Function 2: split_file
    git.create_branch("spec/split_file")
    git.commit("spec/split_file", "L1: spec for split_file", "spec diff")
    git.commit("spec/split_file", "L3: tests for split_file", "test diff")
    git.merge("spec/split_file")

    graph = git.get_graph()
    # initial + 3 (hash_key) + merge + 2 (split_file) + merge = 8
    assert len(graph["commits"]) == 8
    assert len(graph["branches"]) == 3  # main + 2 feature branches


def test_operations_persisted_to_db(setup: tuple[DB, str]) -> None:
    db, run_id = setup
    fn_id: str = db.create_function(run_id, "hash_key", "hashmap.py", 15)
    git: GitModel = GitModel(db, run_id)

    git.create_branch("spec/hash_key", function_id=fn_id)
    git.commit("spec/hash_key", "Add spec", "diff", function_id=fn_id)
    git.merge("spec/hash_key", function_id=fn_id)

    ops = db.get_git_operations(run_id)
    # init + create_branch + commit + merge = 4
    assert len(ops) == 4
    op_types: list[str] = [o["operation"] for o in ops]
    assert op_types == ["init", "create_branch", "commit", "merge"]
