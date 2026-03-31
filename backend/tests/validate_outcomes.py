"""Thorough validation of pipeline outcomes against DB state.

Run with: uv run python tests/validate_outcomes.py
"""

from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

from db import DB
from pipeline import run_pipeline

SHOWCASE_EXAMPLE_PATH: str = "/Users/alexfetisov/dev/showcase-example"


def validate() -> bool:
    db_path: Path = Path(tempfile.mktemp(suffix=".db"))
    db: DB = DB(db_path=db_path)
    run_id: str = db.create_run(SHOWCASE_EXAMPLE_PATH, SHOWCASE_EXAMPLE_PATH, budget_limit=2.0)

    events: list[dict] = []
    results: dict[str, str] = run_pipeline(db, run_id, SHOWCASE_EXAMPLE_PATH, on_event=lambda e: events.append(e))

    ok: bool = True

    def check(condition: bool, msg: str) -> None:
        nonlocal ok
        status: str = "PASS" if condition else "FAIL"
        if not condition:
            ok = False
        print(f"  [{status}] {msg}")

    # === 1. Run completion ===
    print("\n=== Run Completion ===")
    run = db.get_run(run_id)
    check(run is not None, "Run exists in DB")
    check(run["status"] == "completed", f"Run status is 'completed' (got: {run['status']})")
    check(run["budget_used_usd"] > 0, f"Budget was used: ${run['budget_used_usd']:.4f}")
    check(run["budget_used_usd"] <= 2.0, f"Budget under $2 limit: ${run['budget_used_usd']:.4f}")

    # === 2. All 10 functions registered ===
    print("\n=== Function Registration ===")
    functions = db.get_functions_for_run(run_id)
    fn_by_name: dict[str, dict] = {f["name"]: f for f in functions}
    check(len(functions) == 10, f"All 10 functions registered (got: {len(functions)})")

    expected_names: set[str] = {
        "hash_key", "put", "get", "resize", "delete",
        "split_file", "calculate_boundaries", "merge_chunks",
        "validate_checksum", "handle_partial_chunk",
    }
    actual_names: set[str] = set(fn_by_name.keys())
    check(actual_names == expected_names, f"All function names match (missing: {expected_names - actual_names}, extra: {actual_names - expected_names})")

    # === 3. No function stuck in intermediate state ===
    print("\n=== Final Status (no intermediate states) ===")
    terminal_statuses: set[str] = {"covered", "bug_suspect", "needs_refactor", "test_failed", "pending"}
    for fn in functions:
        check(
            fn["status"] in terminal_statuses,
            f"{fn['name']}: status is terminal '{fn['status']}' (not stuck in l1_in_progress etc.)"
        )

    # === 4. Expected outcomes per function ===
    print("\n=== Expected Outcomes ===")
    print(f"  Results: { {fn['name']: fn['status'] for fn in functions} }")

    # resize MUST be needs_refactor (strong directional prompt)
    check(fn_by_name["resize"]["status"] == "needs_refactor", f"resize → needs_refactor (got: {fn_by_name['resize']['status']})")

    # Covered functions should have spec + tests
    for name in ["hash_key", "put", "delete", "split_file", "calculate_boundaries", "validate_checksum"]:
        fn = fn_by_name[name]
        if fn["status"] == "covered":
            check(fn["spec_text"] is not None and len(fn["spec_text"]) > 10, f"{name} (covered): has spec text")
            check(fn["test_code"] is not None and len(fn["test_code"]) > 10, f"{name} (covered): has test code")
            check(fn["test_output"] is not None and "passed" in fn["test_output"].lower(), f"{name} (covered): tests passed")

    # Bug suspect functions should have spec + failed test output with assertion errors
    for name in ["get", "merge_chunks"]:
        fn = fn_by_name[name]
        if fn["status"] == "bug_suspect":
            check(fn["spec_text"] is not None, f"{name} (bug_suspect): has spec text")
            check(fn["test_code"] is not None, f"{name} (bug_suspect): has test code")
            check(fn["test_output"] is not None, f"{name} (bug_suspect): has test output")
            check(fn["status_reason"] is not None, f"{name} (bug_suspect): has status_reason")

    # === 5. Agent logs exist for each processed function ===
    print("\n=== Agent Logs ===")
    all_logs = db.get_all_agent_logs(run_id)
    check(len(all_logs) > 20, f"Total agent log entries: {len(all_logs)} (expected >20)")

    for fn in functions:
        fn_logs = db.get_agent_logs(fn["id"])
        has_l1: bool = any(log["layer"] == "l1" for log in fn_logs)
        check(has_l1, f"{fn['name']}: has L1 (spec gen) conversation logs")

        if fn["status"] not in ("needs_refactor",):
            # Functions that pass L2 should have L2 + L3 logs
            has_l2: bool = any(log["layer"] == "l2" for log in fn_logs)
            check(has_l2, f"{fn['name']}: has L2 (refinement) conversation logs")

        # Check conversation structure: system → user → assistant
        l1_logs = [log for log in fn_logs if log["layer"] == "l1"]
        if l1_logs:
            roles: list[str] = [log["role"] for log in l1_logs]
            check("system" in roles, f"{fn['name']}: L1 has system message")
            check("user" in roles, f"{fn['name']}: L1 has user message")
            check("assistant" in roles, f"{fn['name']}: L1 has assistant response")
            assistant_logs = [log for log in l1_logs if log["role"] == "assistant"]
            if assistant_logs:
                check(assistant_logs[0]["model"] is not None, f"{fn['name']}: L1 assistant has model recorded")
                check(assistant_logs[0]["tokens_used"] > 0, f"{fn['name']}: L1 assistant has tokens_used > 0")
                check(assistant_logs[0]["cost_usd"] > 0, f"{fn['name']}: L1 assistant has cost_usd > 0")

    # === 6. Git operations ===
    print("\n=== Git Operations ===")
    git_ops = db.get_git_operations(run_id)
    check(len(git_ops) > 10, f"Total git operations: {len(git_ops)} (expected >10)")

    op_types: set[str] = {op["operation"] for op in git_ops}
    check("init" in op_types, "Has init operation")
    check("create_branch" in op_types, "Has create_branch operations")
    check("commit" in op_types, "Has commit operations")

    # Covered functions should have merge operations
    merge_ops = [op for op in git_ops if op["operation"] == "merge"]
    if merge_ops:
        check(True, f"Has {len(merge_ops)} merge operations (covered functions merged to main)")
    else:
        check(False, "No merge operations found — covered functions should merge")

    # Each processed function should have a branch
    branch_ops = [op for op in git_ops if op["operation"] == "create_branch"]
    branch_names: set[str] = {op["branch_name"] for op in branch_ops if op["branch_name"]}
    check(len(branch_names) >= 8, f"At least 8 function branches created (got: {len(branch_names)}: {branch_names})")

    # === 7. Status change events in SSE ===
    print("\n=== SSE Events ===")
    event_types: set[str] = {e["type"] for e in events}
    check("pipeline_start" in event_types, "SSE: pipeline_start event")
    check("pipeline_complete" in event_types, "SSE: pipeline_complete event")
    check("functions_discovered" in event_types, "SSE: functions_discovered event")
    check("function_start" in event_types, "SSE: function_start events")
    check("function_status" in event_types, "SSE: function_status events")
    check("budget_update" in event_types, "SSE: budget_update events")

    fn_status_events = [e for e in events if e["type"] == "function_status"]
    check(len(fn_status_events) == 10, f"SSE: 10 function_status events (got: {len(fn_status_events)})")

    # === Summary ===
    print(f"\n{'='*60}")
    status_counts: dict[str, int] = {}
    for fn in functions:
        status_counts[fn["status"]] = status_counts.get(fn["status"], 0) + 1
    print(f"Status distribution: {status_counts}")
    print(f"Budget: ${run['budget_used_usd']:.4f} / ${run['budget_limit_usd']:.2f}")
    print(f"Agent logs: {len(all_logs)}")
    print(f"Git operations: {len(git_ops)}")
    print(f"SSE events: {len(events)}")

    db.close()
    db_path.unlink(missing_ok=True)

    if ok:
        print("\nALL CHECKS PASSED")
    else:
        print("\nSOME CHECKS FAILED")
    return ok


if __name__ == "__main__":
    success: bool = validate()
    sys.exit(0 if success else 1)
