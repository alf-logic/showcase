"""Layer 3: Test generation agent — generates tests and runs them."""

from __future__ import annotations

import subprocess
import sys
import tempfile
from pathlib import Path

from db import DB
from git_model import GitModel
from llm import LLMClient, LLMResponse, check_budget_and_call

from agents.prompts import L3_HINTS, SYSTEM_PROMPT_L3


def _run_tests(test_code: str, clone_path: str) -> tuple[bool, str]:
    """Write test code to a temp file and run it with pytest.

    Returns (passed, output).
    """
    # Write test file into the cloned repo so imports work
    test_dir: Path = Path(clone_path)
    test_file: Path = test_dir / "_fv_generated_test.py"
    try:
        test_file.write_text(test_code, encoding="utf-8")
        result = subprocess.run(
            [sys.executable, "-m", "pytest", str(test_file), "-v", "--tb=short", "--no-header"],
            capture_output=True,
            text=True,
            timeout=30,
            cwd=str(test_dir),
            env={**__import__("os").environ, "PYTHONPATH": str(test_dir)},
        )
        output: str = result.stdout + result.stderr
        passed: bool = result.returncode == 0
        return passed, output
    except subprocess.TimeoutExpired:
        return False, "Test execution timed out (30s)"
    except Exception as exc:
        return False, f"Test execution error: {exc}"
    finally:
        test_file.unlink(missing_ok=True)


def _classify_failure(test_output: str) -> str:
    """Classify test failure as bug_suspect or test_failed."""
    output_lower: str = test_output.lower()
    # Runtime errors during test execution → code behaves differently than spec → bug suspect
    bug_indicators: list[str] = [
        "assertionerror", "keyerror", "valueerror",
        "indexerror", "typeerror", "attributeerror", "runtimeerror",
        "zerodivisionerror", "overflowerror",
    ]
    if any(indicator in output_lower for indicator in bug_indicators):
        return "bug_suspect"
    # Import errors, syntax errors → test generation issue
    return "test_failed"


def run_l3(
    db: DB,
    llm: LLMClient,
    git: GitModel,
    run_id: str,
    function_id: str,
    function_name: str,
    source_code: str,
    spec_text: str,
    file_path: str,
    clone_path: str,
) -> str:
    """Generate tests and run them.

    Returns the final status: 'covered', 'bug_suspect', or 'test_failed'.
    """
    db.update_function_status(function_id, "l3_in_progress")

    hint: str = L3_HINTS.get(function_name, "")
    system_msg: str = SYSTEM_PROMPT_L3
    if hint:
        system_msg += f"\n\nAdditional context:\n{hint}"

    user_msg: str = (
        f"Generate pytest tests for `{function_name}` from `{file_path}`.\n\n"
        f"Source code:\n```python\n{source_code}\n```\n\n"
        f"Gherkin spec:\n```gherkin\n{spec_text}\n```\n\n"
        f"Import the function with: `from {file_path.replace('/', '.').removesuffix('.py')} import {function_name}`\n"
        f"Also import any module-level constants that the tests might need (like EMPTY, DELETED, etc)."
    )

    messages: list[dict[str, str]] = [
        {"role": "system", "content": system_msg},
        {"role": "user", "content": user_msg},
    ]

    db.add_agent_log(run_id, function_id, "l3", "system", system_msg)
    db.add_agent_log(run_id, function_id, "l3", "user", user_msg)

    response: LLMResponse = check_budget_and_call(llm, db, run_id, messages)
    test_code: str = response.content.strip()

    # Clean up markdown fences
    if test_code.startswith("```"):
        lines: list[str] = test_code.split("\n")
        lines = [l for l in lines if not l.startswith("```")]
        test_code = "\n".join(lines).strip()

    db.add_agent_log(
        run_id, function_id, "l3", "assistant", test_code,
        model=response.model,
        tokens_used=response.total_tokens,
        cost_usd=response.cost_usd,
    )

    # Run the tests
    passed, test_output = _run_tests(test_code, clone_path)

    db.update_function_tests(function_id, test_code, test_output)

    if passed:
        status: str = "covered"
        db.update_function_status(function_id, "covered")
    else:
        status = _classify_failure(test_output)
        reason: str = test_output[:500]  # truncate for DB
        db.update_function_status(function_id, status, reason=reason)

    # Git: commit tests
    branch_name: str = f"spec/{function_name}"
    git.commit(branch_name, f"L3: tests for {function_name}", test_code, function_id=function_id)

    if passed:
        git.merge(branch_name, function_id=function_id)

    return status
