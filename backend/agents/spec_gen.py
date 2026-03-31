"""Layer 1: Gherkin spec generation agent."""

from __future__ import annotations

from db import DB
from git_model import GitModel
from llm import LLMClient, LLMResponse, check_budget_and_call

from agents.prompts import L1_HINTS, SYSTEM_PROMPT_L1


def run_l1(
    db: DB,
    llm: LLMClient,
    git: GitModel,
    run_id: str,
    function_id: str,
    function_name: str,
    source_code: str,
    file_path: str,
) -> str | None:
    """Generate a Gherkin spec for a function.

    Returns the spec text on success, None on failure.
    """
    db.update_function_status(function_id, "l1_in_progress")

    hint: str = L1_HINTS.get(function_name, "")
    system_msg: str = SYSTEM_PROMPT_L1
    if hint:
        system_msg += f"\n\nAdditional context for this function:\n{hint}"

    user_msg: str = f"Generate a Gherkin spec for the following function from `{file_path}`:\n\n```python\n{source_code}\n```"

    messages: list[dict[str, str]] = [
        {"role": "system", "content": system_msg},
        {"role": "user", "content": user_msg},
    ]

    # Log the system + user messages
    db.add_agent_log(run_id, function_id, "l1", "system", system_msg)
    db.add_agent_log(run_id, function_id, "l1", "user", user_msg)

    response: LLMResponse = check_budget_and_call(llm, db, run_id, messages)

    spec_text: str = response.content.strip()
    # Clean up markdown fences if the model wraps them
    if spec_text.startswith("```"):
        lines: list[str] = spec_text.split("\n")
        lines = [l for l in lines if not l.startswith("```")]
        spec_text = "\n".join(lines).strip()

    db.add_agent_log(
        run_id, function_id, "l1", "assistant", spec_text,
        model=response.model,
        tokens_used=response.total_tokens,
        cost_usd=response.cost_usd,
    )

    # Validate: must have Feature and Scenario
    if "Feature:" not in spec_text or "Scenario:" not in spec_text:
        db.update_function_status(function_id, "l1_done", reason="Invalid spec generated")
        return None

    db.update_function_spec(function_id, spec_text)
    db.update_function_status(function_id, "l1_done")

    # Git: create branch and commit the spec
    branch_name: str = f"spec/{function_name}"
    git.create_branch(branch_name, function_id=function_id)
    git.commit(branch_name, f"L1: add spec for {function_name}", spec_text, function_id=function_id)

    return spec_text
