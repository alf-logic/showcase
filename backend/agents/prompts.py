"""Directional prompts per function to guide LLM toward expected outcomes."""

from __future__ import annotations

# Extra context hints per function that nudge the LLM toward specific findings.
# These are appended to the system prompt for each layer.

L1_HINTS: dict[str, str] = {
    "hash_key": "This is a pure arithmetic function with clear behavior. It should be straightforward to specify.",
    "put": "Focus on the linear probing behavior, overwrite semantics, and tombstone handling.",
    "get": "Pay very close attention to the probe loop bounds. Count exactly how many slots are probed. Is the loop count correct for a full table?",
    "resize": "This function has multiple responsibilities: migration, tombstone skipping, load factor validation, and error handling. Note all the complexity.",
    "delete": "Focus on tombstone deletion and how it preserves probe chains for other keys.",
    "split_file": "Pure function with simple chunking logic. Last chunk may be smaller.",
    "calculate_boundaries": "Pure arithmetic. Note the fair distribution of remainder bytes across chunks.",
    "merge_chunks": "Look carefully at the empty chunks case. What happens when chunks is an empty list? Trace through the code path.",
    "validate_checksum": "Simple pure function: compute SHA-256 and compare.",
    "handle_partial_chunk": "This function has many interacting edge cases: negative offset, offset beyond data, zero size, empty data. Each combination behaves differently.",
}

L2_HINTS: dict[str, str] = {
    "hash_key": "",
    "put": "",
    "get": "This function is simple enough to test. Accept it. The spec should highlight the probe loop boundary behavior.",
    "resize": "REJECT this function. It has multiple responsibilities mixed together: rehashing entries, skipping tombstones, load factor validation, error reporting, and migration counting. This is exactly the kind of function that needs refactoring before it can be reliably tested. Output: REJECTED: Function has multiple mixed responsibilities (rehashing, validation, statistics, error handling) that should be separated before testing.",
    "delete": "",
    "split_file": "",
    "calculate_boundaries": "",
    "merge_chunks": "The empty-list case has suspicious code: it computes a hash of nothing, then checks it against... a hash of nothing. This always passes but the logic is clearly wrong — it should just return b'' without the check.",
    "validate_checksum": "",
    "handle_partial_chunk": "",
}

L3_HINTS: dict[str, str] = {
    "hash_key": "",
    "put": "",
    "get": "Write a test that fills the table to near capacity, then looks up the key that was inserted last (which would be in the last probed slot). The off-by-one in `range(capacity - 1)` means the last slot is never checked.",
    "resize": "",  # won't reach L3
    "delete": "",
    "split_file": "",
    "calculate_boundaries": "",
    "merge_chunks": "Write a test that calls merge_chunks with an empty list []. The function returns b'' but the integrity check code is nonsensical.",
    "validate_checksum": "",
    "handle_partial_chunk": "Test all edge case combinations: empty data, negative offset, offset past end, size=0, size larger than available. Some of these interact in ways that are hard to get right in one pass.",
}

SYSTEM_PROMPT_L1: str = """You are a specification agent. Your job is to generate Gherkin behavioral specs for Python functions.

Given a function's source code, generate a Gherkin spec that describes its behavior. The spec should:
- Start with `Feature: <function_name>`
- Group related behaviors into `Rule:` blocks
- Each Rule should contain `Scenario:` blocks
- Use `When`/`Then`/`And` steps (no `Given`)
- Cover normal behavior, edge cases, and error conditions
- Be embedded in the function's docstring

Output ONLY the Gherkin spec text (no markdown fences, no explanation). Start with `Feature:`.
"""

SYSTEM_PROMPT_L2: str = """You are a specification reviewer. Your job is to review and refine Gherkin specs for Python functions.

Given a function's source code and its L1 spec, you must:
1. Check if the spec is complete and accurate
2. Check if the function is testable

ONLY reject a function if it is TRULY too complex — meaning it has ALL of these problems:
- Multiple distinct responsibilities mixed together (e.g., data migration + validation + error reporting + statistics)
- More than 20 lines of nested logic with multiple for/if combinations
- Cannot be tested in isolation without extensive mocking

Most functions are ACCEPTABLE even if they have some complexity. Linear probing loops, edge case handling, and simple error checks are NORMAL and testable.

If you ACCEPT, output the refined spec (ONLY the Gherkin text, start with `Feature:`).
If you REJECT, output EXACTLY this format:
REJECTED: <reason>
"""

SYSTEM_PROMPT_L3: str = """You are a test generation agent. Your job is to generate pytest tests for Python functions based on their Gherkin specs.

Given a function's source code and its Gherkin spec, generate pytest tests where:
- Always `import pytest` at the top
- Import the function being tested
- Each Scenario becomes one test function with `test_` prefix
- Use `# When` and `# Then` comments to mark test phases
- Use direct assertions (no helper functions)
- Use `pytest.raises()` for exception testing

CRITICAL RULES:
- NEVER hardcode expected return values that you computed yourself. Instead, test PROPERTIES of the output (e.g., `assert 0 <= result < capacity` instead of `assert result == 5`).
- For hash/math functions, test behavioral properties: determinism (same input → same output), range (output within bounds), type correctness.
- If you need to verify an exact value, CALL THE FUNCTION to compute it, don't guess: `expected = hash_key("test", 10); assert hash_key("test", 10) == expected`
- For functions with side effects, set up state, call the function, then assert on the resulting state.

Output ONLY valid Python test code. No markdown fences, no explanation. Start with the import statement.
"""
