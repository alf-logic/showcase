"""Pipeline orchestrator — runs L1→L2→L3 for all functions."""

from __future__ import annotations

import ast
import asyncio
import json
import logging
from collections.abc import Callable
from pathlib import Path
from typing import Any

from db import DB
from git_model import GitModel
from llm import BudgetExceededError, LLMClient, MockLLMClient

from agents.spec_gen import run_l1
from agents.spec_refine import run_l2
from agents.test_gen import run_l3

logger: logging.Logger = logging.getLogger(__name__)


def _extract_function_source(file_path: Path, function_name: str) -> str | None:
    """Extract a single function's source code from a file."""
    source: str = file_path.read_text(encoding="utf-8")
    tree = ast.parse(source)
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name == function_name:
            lines: list[str] = source.splitlines()
            # Get from function def to end of function
            start: int = node.lineno - 1
            end: int = node.end_lineno if node.end_lineno else start + 1
            return "\n".join(lines[start:end])
    return None


def _extract_all_functions(clone_path: Path) -> list[dict[str, Any]]:
    """Extract all function info from Python files in the repo."""
    functions: list[dict[str, Any]] = []
    for py_file in sorted(clone_path.rglob("*.py")):
        if py_file.name.startswith("_") and py_file.name != "__init__.py":
            continue
        if py_file.name == "__init__.py":
            continue
        rel_path: str = str(py_file.relative_to(clone_path))
        try:
            source: str = py_file.read_text(encoding="utf-8")
            tree = ast.parse(source)
        except (SyntaxError, UnicodeDecodeError):
            continue
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                args: list[str] = [a.arg for a in node.args.args]
                functions.append({
                    "name": node.name,
                    "file": rel_path,
                    "line": node.lineno,
                    "args": json.dumps(args),
                })
    return functions


def _process_function(
    db: DB,
    llm: LLMClient,
    git: GitModel,
    run_id: str,
    fn_id: str,
    function_name: str,
    source_code: str,
    file_path: str,
    clone_path: str,
    on_event: Callable[[dict[str, Any]], None] | None = None,
) -> str:
    """Process a single function through L1→L2→L3.

    Returns the final status string.
    """
    def emit(event: dict[str, Any]) -> None:
        if on_event:
            on_event(event)

    emit({"type": "function_start", "name": function_name, "file": file_path})

    # Layer 1: Spec generation
    emit({"type": "layer_start", "name": function_name, "layer": "l1"})
    try:
        spec: str | None = run_l1(db, llm, git, run_id, fn_id, function_name, source_code, file_path)
    except BudgetExceededError:
        db.update_function_status(fn_id, "pending", reason="Budget exceeded")
        emit({"type": "function_status", "name": function_name, "status": "pending", "reason": "Budget exceeded"})
        return "pending"

    if spec is None:
        emit({"type": "function_status", "name": function_name, "status": "test_failed", "reason": "L1 failed"})
        db.update_function_status(fn_id, "test_failed", reason="L1 spec generation failed")
        return "test_failed"
    emit({"type": "layer_complete", "name": function_name, "layer": "l1"})

    # Layer 2: Refinement / Review
    emit({"type": "layer_start", "name": function_name, "layer": "l2"})
    try:
        refined, accepted = run_l2(db, llm, git, run_id, fn_id, function_name, source_code, spec, file_path)
    except BudgetExceededError:
        db.update_function_status(fn_id, "pending", reason="Budget exceeded")
        emit({"type": "function_status", "name": function_name, "status": "pending", "reason": "Budget exceeded"})
        return "pending"

    if not accepted:
        emit({"type": "function_status", "name": function_name, "status": "needs_refactor"})
        return "needs_refactor"
    emit({"type": "layer_complete", "name": function_name, "layer": "l2"})

    # Layer 3: Test generation + execution
    emit({"type": "layer_start", "name": function_name, "layer": "l3"})
    try:
        status: str = run_l3(db, llm, git, run_id, fn_id, function_name, source_code, refined, file_path, clone_path)
    except BudgetExceededError:
        db.update_function_status(fn_id, "pending", reason="Budget exceeded")
        emit({"type": "function_status", "name": function_name, "status": "pending", "reason": "Budget exceeded"})
        return "pending"

    emit({"type": "layer_complete", "name": function_name, "layer": "l3"})
    emit({"type": "function_status", "name": function_name, "status": status})
    return status


def run_pipeline(
    db: DB,
    run_id: str,
    clone_path: str,
    model: str = "mock",
    on_event: Callable[[dict[str, Any]], None] | None = None,
) -> dict[str, str]:
    """Run the full pipeline on all functions in the repo.

    Use model="mock" (default) for deterministic predefined responses.
    Use model="gpt-4o-mini" or other for real OpenAI API calls.

    Returns a dict of function_name → final_status.
    """
    def emit(event: dict[str, Any]) -> None:
        if on_event:
            on_event(event)

    clone: Path = Path(clone_path)
    llm: LLMClient | MockLLMClient
    if model == "mock":
        llm = MockLLMClient()
    else:
        llm = LLMClient(model=model)
    git: GitModel = GitModel(db, run_id)

    db.update_run_status(run_id, "running")
    emit({"type": "pipeline_start", "run_id": run_id})

    # Extract all functions and register them in DB
    raw_functions: list[dict[str, Any]] = _extract_all_functions(clone)
    function_ids: dict[str, str] = {}
    for fn_info in raw_functions:
        fn_id: str = db.create_function(
            run_id, fn_info["name"], fn_info["file"], fn_info["line"], fn_info["args"],
        )
        function_ids[fn_info["name"]] = fn_id

    emit({"type": "functions_discovered", "count": len(raw_functions), "names": [f["name"] for f in raw_functions]})

    # Process each function
    results: dict[str, str] = {}
    for fn_info in raw_functions:
        fn_name: str = fn_info["name"]
        fn_id = function_ids[fn_name]
        file_path: str = fn_info["file"]

        source: str | None = _extract_function_source(clone / file_path, fn_name)
        if source is None:
            db.update_function_status(fn_id, "test_failed", reason="Could not extract source")
            results[fn_name] = "test_failed"
            continue

        # Check budget before starting
        remaining: float = db.get_remaining_budget(run_id)
        if remaining <= 0:
            db.update_function_status(fn_id, "pending", reason="Budget exceeded")
            results[fn_name] = "pending"
            continue

        status: str = _process_function(
            db, llm, git, run_id, fn_id, fn_name, source, file_path, clone_path, on_event,
        )
        results[fn_name] = status

        run = db.get_run(run_id)
        emit({"type": "budget_update", "used": run["budget_used_usd"], "limit": run["budget_limit_usd"]})

    db.update_run_status(run_id, "completed")

    summary: dict[str, int] = {}
    for status in results.values():
        summary[status] = summary.get(status, 0) + 1

    emit({"type": "pipeline_complete", "results": results, "summary": summary})
    return results
