"""In-memory git model that tracks branches, commits, and merges."""

from __future__ import annotations

import hashlib
import time
from dataclasses import dataclass, field

from db import DB


@dataclass
class Commit:
    sha: str
    branch: str
    message: str
    diff: str
    parent_shas: list[str]
    timestamp: float


@dataclass
class Branch:
    name: str
    head_sha: str
    created_from: str | None = None


class GitModel:
    """In-memory git graph with SQLite persistence."""

    def __init__(self, db: DB, run_id: str) -> None:
        self.db: DB = db
        self.run_id: str = run_id
        self.commits: dict[str, Commit] = {}
        self.branches: dict[str, Branch] = {}

        # Create initial commit + main branch
        initial_sha: str = self._make_sha("initial")
        initial: Commit = Commit(
            sha=initial_sha,
            branch="main",
            message="Initial commit",
            diff="",
            parent_shas=[],
            timestamp=time.time(),
        )
        self.commits[initial_sha] = initial
        self.branches["main"] = Branch(name="main", head_sha=initial_sha)

        self.db.add_git_operation(
            run_id, None, "init",
            branch_name="main",
            commit_sha=initial_sha,
            commit_message="Initial commit",
        )

    def _make_sha(self, content: str) -> str:
        raw: str = f"{content}-{time.time()}-{len(self.commits)}"
        return hashlib.sha1(raw.encode()).hexdigest()[:10]

    def create_branch(self, name: str, from_branch: str = "main", function_id: str | None = None) -> str:
        """Create a new branch from the head of an existing branch."""
        parent_branch: Branch = self.branches[from_branch]
        self.branches[name] = Branch(
            name=name,
            head_sha=parent_branch.head_sha,
            created_from=from_branch,
        )
        self.db.add_git_operation(
            self.run_id, function_id, "create_branch",
            branch_name=name,
            parent_sha=parent_branch.head_sha,
        )
        return parent_branch.head_sha

    def commit(
        self,
        branch: str,
        message: str,
        diff: str,
        function_id: str | None = None,
    ) -> str:
        """Create a commit on a branch."""
        branch_obj: Branch = self.branches[branch]
        sha: str = self._make_sha(message)
        commit: Commit = Commit(
            sha=sha,
            branch=branch,
            message=message,
            diff=diff,
            parent_shas=[branch_obj.head_sha],
            timestamp=time.time(),
        )
        self.commits[sha] = commit
        branch_obj.head_sha = sha

        self.db.add_git_operation(
            self.run_id, function_id, "commit",
            branch_name=branch,
            commit_sha=sha,
            commit_message=message,
            diff=diff,
            parent_sha=commit.parent_shas[0],
        )
        return sha

    def merge(
        self,
        source_branch: str,
        target_branch: str = "main",
        function_id: str | None = None,
    ) -> str:
        """Merge source branch into target branch."""
        source: Branch = self.branches[source_branch]
        target: Branch = self.branches[target_branch]

        sha: str = self._make_sha(f"merge-{source_branch}")
        merge_commit: Commit = Commit(
            sha=sha,
            branch=target_branch,
            message=f"Merge {source_branch} into {target_branch}",
            diff="",
            parent_shas=[target.head_sha, source.head_sha],
            timestamp=time.time(),
        )
        self.commits[sha] = merge_commit
        target.head_sha = sha

        self.db.add_git_operation(
            self.run_id, function_id, "merge",
            branch_name=source_branch,
            commit_sha=sha,
            commit_message=merge_commit.message,
            parent_sha=f"{target.head_sha},{source.head_sha}",
        )
        return sha

    def get_graph(self) -> dict:
        """Return the full git graph for visualization."""
        return {
            "commits": [
                {
                    "sha": c.sha,
                    "branch": c.branch,
                    "message": c.message,
                    "parents": c.parent_shas,
                    "timestamp": c.timestamp,
                }
                for c in sorted(self.commits.values(), key=lambda c: c.timestamp)
            ],
            "branches": [
                {
                    "name": b.name,
                    "head_sha": b.head_sha,
                    "created_from": b.created_from,
                }
                for b in self.branches.values()
            ],
        }

    def get_branch_names(self) -> list[str]:
        return list(self.branches.keys())

    def get_commit(self, sha: str) -> Commit | None:
        return self.commits.get(sha)
