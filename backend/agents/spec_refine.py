"""Layer 2: Spec refinement / review agent."""

from __future__ import annotations

from db import DB
from git_model import GitModel
from llm import LLMClient, LLMResponse, check_budget_and_call

from agents.prompts import L2_HINTS, SYSTEM_PROMPT_L2


def run_l2(
    db: DB,
    llm: LLMClient,
    git: GitModel,
    run_id: str,
    function_id: str,
    function_name: str,
    source_code: str,
    l1_spec: str,
    file_path: str,
) -> tuple[str | None, bool]:
    """Review and refine a spec.

    Returns (refined_spec, accepted). If rejected, returns (None, False).
    """
    db.update_function_status(function_id, "l2_in_progress")

    hint: str = L2_HINTS.get(function_name, "")
    system_msg: str = SYSTEM_PROMPT_L2
    if hint:
        system_msg += f"\n\nAdditional context for this function:\n{hint}"

    user_msg: str = (
        f"Review this spec for `{function_name}` from `{file_path}`.\n\n"
        f"Source code:\n```python\n{source_code}\n```\n\n"
        f"L1 Spec:\n```gherkin\n{l1_spec}\n```"
    )

    messages: list[dict[str, str]] = [
        {"role": "system", "content": system_msg},
        {"role": "user", "content": user_msg},
    ]

    db.add_agent_log(run_id, function_id, "l2", "system", system_msg)
    db.add_agent_log(run_id, function_id, "l2", "user", user_msg)

    response: LLMResponse = check_budget_and_call(llm, db, run_id, messages)
    result: str = response.content.strip()

    db.add_agent_log(
        run_id, function_id, "l2", "assistant", result,
        model=response.model,
        tokens_used=response.total_tokens,
        cost_usd=response.cost_usd,
    )

    # Check for rejection
    if result.upper().startswith("REJECTED:"):
        reason: str = result.split(":", 1)[1].strip()
        db.update_function_status(function_id, "needs_refactor", reason=reason)
        return None, False

    # Clean up markdown fences
    refined_spec: str = result
    if refined_spec.startswith("```"):
        lines: list[str] = refined_spec.split("\n")
        lines = [l for l in lines if not l.startswith("```")]
        refined_spec = "\n".join(lines).strip()

    if "Feature:" not in refined_spec:
        # Model didn't return a valid spec, keep the L1 spec
        refined_spec = l1_spec

    db.update_function_spec(function_id, refined_spec)
    db.update_function_status(function_id, "l2_done")

    # Git: commit refinement
    branch_name: str = f"spec/{function_name}"
    git.commit(branch_name, f"L2: refined spec for {function_name}", refined_spec, function_id=function_id)

    return refined_spec, True
