"""Predefined LLM responses for deterministic pipeline runs.

Each function has L1 (spec), L2 (review), and L3 (tests) responses.
L3 test code is designed to produce the expected outcome when run
against the real showcase-example code.
"""

from __future__ import annotations

# ============================================================
# L1: Gherkin specs
# ============================================================

L1_SPECS: dict[str, str] = {
    "hash_key": """Feature: hash_key

  Rule: Determinism
    Scenario: Same input produces same output
      When hash_key is called twice with key="hello" and capacity=10
      Then both calls return the same integer

  Rule: Output range
    Scenario: Result is within capacity bounds
      When hash_key is called with any key and capacity=100
      Then the result is >= 0 and < 100

  Rule: Edge cases
    Scenario: Empty string is valid input
      When hash_key is called with key="" and capacity=10
      Then a valid integer in [0, 10) is returned""",

    "put": """Feature: put

  Rule: Insert new entry
    Scenario: Insert into empty slot
      When put is called with a key not in the table
      Then the key-value pair is stored at the hashed index

  Rule: Update existing entry
    Scenario: Overwrite existing key
      When put is called with a key already in the table
      Then the value is updated in place

  Rule: Tombstone reuse
    Scenario: Reuse deleted slot
      When put encounters a DELETED tombstone during probing
      Then it uses the tombstone slot for the new entry""",

    "get": """Feature: get

  Rule: Successful lookup
    Scenario: Key exists in table
      When get is called with a key that was previously inserted
      Then the associated value is returned

  Rule: Key not found
    Scenario: Key does not exist
      When get is called with a key not in the table
      Then a KeyError is raised

  Rule: Probe chain traversal
    Scenario: Key found after probing past collisions
      When the table has collisions and the key is beyond the first probe
      Then get correctly traverses the probe chain to find it

  Rule: Near-full table lookup
    Scenario: Key in last probe position of a nearly full table
      When the table is nearly full and the key is at the last possible probe position
      Then get should find the key (but may fail due to off-by-one in probe count)""",

    "resize": """Feature: resize

  Rule: Rehash all entries
    Scenario: All live entries migrated to new table
      When resize is called with a larger capacity
      Then all non-EMPTY non-DELETED entries appear in the new table

  Rule: Tombstone cleanup
    Scenario: DELETED slots are not migrated
      When the old table has DELETED tombstones
      Then the new table does not contain them

  Rule: Load factor validation
    Scenario: Reject undersized target
      When the new capacity would result in load factor > 0.75
      Then a ValueError is raised

  Rule: Error handling
    Scenario: Zero capacity rejected
      When resize is called with new_capacity < 1
      Then a ValueError is raised""",

    "delete": """Feature: delete

  Rule: Successful deletion
    Scenario: Key exists and is removed
      When delete is called with a key present in the table
      Then the slot is replaced with DELETED and True is returned

  Rule: Key not found
    Scenario: Key does not exist
      When delete is called with a key not in the table
      Then False is returned and the table is unchanged

  Rule: Probe chain preservation
    Scenario: Tombstone preserves subsequent lookups
      When a key is deleted between two colliding keys
      Then the second key is still findable via get""",

    "split_file": """Feature: split_file

  Rule: Normal splitting
    Scenario: Data splits into equal chunks
      When split_file is called with 10 bytes and chunk_size=5
      Then two 5-byte chunks are returned

  Rule: Last chunk may be smaller
    Scenario: Data not evenly divisible
      When split_file is called with 7 bytes and chunk_size=3
      Then three chunks are returned: 3, 3, and 1 bytes

  Rule: Edge cases
    Scenario: Empty data returns empty list
      When split_file is called with empty bytes
      Then an empty list is returned

    Scenario: Invalid chunk_size raises error
      When split_file is called with chunk_size=0
      Then a ValueError is raised""",

    "calculate_boundaries": """Feature: calculate_boundaries

  Rule: Equal distribution
    Scenario: Evenly divisible size
      When total_size=100 and chunk_count=4
      Then boundaries are [(0,25), (25,50), (50,75), (75,100)]

  Rule: Remainder distribution
    Scenario: Size not evenly divisible
      When total_size=10 and chunk_count=3
      Then first chunks get one extra byte each

  Rule: Edge cases
    Scenario: Zero total_size
      When total_size=0 and chunk_count=3
      Then all boundaries have zero length

    Scenario: Invalid chunk_count raises error
      When chunk_count=0
      Then a ValueError is raised""",

    "merge_chunks": """Feature: merge_chunks

  Rule: Normal merge
    Scenario: Multiple chunks merged into original data
      When merge_chunks is called with [b"abc", b"def"]
      Then b"abcdef" is returned

  Rule: Single chunk
    Scenario: One chunk returns itself
      When merge_chunks is called with [b"hello"]
      Then b"hello" is returned

  Rule: Empty input
    Scenario: Empty list handling
      When merge_chunks is called with an empty list []
      Then b"" should be returned but the integrity check logic is suspicious""",

    "validate_checksum": """Feature: validate_checksum

  Rule: Valid checksum
    Scenario: Matching checksum returns True
      When the computed SHA-256 of the chunk matches the expected hex digest
      Then True is returned

  Rule: Invalid checksum
    Scenario: Mismatched checksum returns False
      When the computed SHA-256 does not match the expected hex digest
      Then False is returned""",

    "handle_partial_chunk": """Feature: handle_partial_chunk

  Rule: Normal extraction
    Scenario: Extract bytes from middle of data
      When offset=5 and size=3 on a 10-byte input
      Then 3 bytes starting at position 5 are returned

  Rule: Boundary clamping
    Scenario: Size exceeds available data
      When offset=8 and size=10 on a 10-byte input
      Then only the remaining 2 bytes are returned

  Rule: Edge cases
    Scenario: Negative offset wraps from end
      When offset=-3 and size=2 on a 10-byte input
      Then bytes from position 7 are returned

    Scenario: Offset beyond data returns empty
      When offset=100 on a 10-byte input
      Then empty bytes are returned

    Scenario: Empty data always returns empty
      When data is empty regardless of offset and size
      Then empty bytes are returned""",
}

# ============================================================
# L2: Review decisions
# ============================================================

L2_REVIEWS: dict[str, str] = {
    "hash_key": L1_SPECS["hash_key"],  # accepted, return same spec
    "put": L1_SPECS["put"],
    "get": L1_SPECS["get"],
    "resize": "REJECTED: Function has multiple mixed responsibilities — rehashing entries, skipping tombstones, load factor validation, error reporting, and migration counting. These should be separated into smaller functions before reliable testing is possible.",
    "delete": L1_SPECS["delete"],
    "split_file": L1_SPECS["split_file"],
    "calculate_boundaries": L1_SPECS["calculate_boundaries"],
    "merge_chunks": L1_SPECS["merge_chunks"],
    "validate_checksum": L1_SPECS["validate_checksum"],
    "handle_partial_chunk": L1_SPECS["handle_partial_chunk"],
}

# ============================================================
# L3: Test code (designed to produce expected outcomes)
# ============================================================

L3_TESTS: dict[str, str] = {
    "hash_key": """import pytest
from hashmap.hashmap import hash_key

def test_hash_key_determinism():
    # When
    result1 = hash_key("hello", 10)
    result2 = hash_key("hello", 10)
    # Then
    assert result1 == result2

def test_hash_key_range():
    # When
    result = hash_key("test", 100)
    # Then
    assert 0 <= result < 100

def test_hash_key_empty_string():
    # When
    result = hash_key("", 10)
    # Then
    assert 0 <= result < 10
""",

    "put": """import pytest
from hashmap.hashmap import hash_key, put, get, EMPTY, DELETED

def test_put_insert_new():
    # When
    table = [EMPTY] * 16
    put(table, "alice", 42)
    # Then
    idx = hash_key("alice", 16)
    found = False
    for i in range(16):
        slot = table[(idx + i) % 16]
        if slot is not EMPTY and slot is not DELETED and slot[0] == "alice":
            assert slot[1] == 42
            found = True
            break
    assert found

def test_put_overwrite():
    # When
    table = [EMPTY] * 16
    put(table, "alice", 42)
    put(table, "alice", 99)
    # Then — find alice, should have value 99
    idx = hash_key("alice", 16)
    for i in range(16):
        slot = table[(idx + i) % 16]
        if slot is not EMPTY and slot is not DELETED and slot[0] == "alice":
            assert slot[1] == 99
            break
""",

    "get": """import pytest
from hashmap.hashmap import hash_key, put, get, EMPTY, DELETED

def test_get_existing_key():
    # When
    table = [EMPTY] * 16
    put(table, "alice", 42)
    result = get(table, "alice")
    # Then
    assert result == 42

def test_get_missing_key():
    # When
    table = [EMPTY] * 16
    # Then
    with pytest.raises(KeyError):
        get(table, "missing")

def test_get_nearly_full_table_last_slot():
    # When — fill all slots, then look up the key in the last probed position
    # The spec says get should find any key in the table, but the
    # implementation uses range(capacity - 1) instead of range(capacity),
    # so it never checks the last slot.
    capacity = 4
    table = [EMPTY] * capacity

    # Fill all slots manually
    for i in range(capacity):
        table[i] = [f"k{i}", i]

    # Patch hash_key to always return 0 so probing starts at slot 0
    import hashmap.hashmap as hm
    original_hash = hm.hash_key
    hm.hash_key = lambda k, c: 0

    try:
        # The key "k3" is at index 3 (the last slot).
        # get() probes slots 0,1,2 but NOT 3 due to range(capacity-1).
        # This SHOULD return 3 but will raise KeyError — the bug.
        result = get(table, "k3")
        assert result == 3  # This assertion will fail because KeyError is raised first
    finally:
        hm.hash_key = original_hash
""",

    # resize: won't reach L3 (rejected at L2)
    "resize": "",

    "delete": """import pytest
from hashmap.hashmap import hash_key, put, get, delete, EMPTY, DELETED

def test_delete_existing_key():
    # When
    table = [EMPTY] * 16
    put(table, "alice", 42)
    result = delete(table, "alice")
    # Then
    assert result is True
    with pytest.raises(KeyError):
        get(table, "alice")

def test_delete_missing_key():
    # When
    table = [EMPTY] * 16
    result = delete(table, "missing")
    # Then
    assert result is False

def test_delete_preserves_probe_chain():
    # When — insert two keys that collide, delete the first, find the second
    table = [EMPTY] * 16
    put(table, "alice", 1)
    put(table, "bob", 2)
    delete(table, "alice")
    # Then — bob should still be findable
    result = get(table, "bob")
    assert result == 2
""",

    "split_file": """import pytest
from chunker.chunker import split_file

def test_split_equal_chunks():
    # When
    result = split_file(b"abcdefghij", 5)
    # Then
    assert result == [b"abcde", b"fghij"]

def test_split_uneven():
    # When
    result = split_file(b"abcdefg", 3)
    # Then
    assert result == [b"abc", b"def", b"g"]

def test_split_empty():
    # When
    result = split_file(b"", 5)
    # Then
    assert result == []

def test_split_invalid_chunk_size():
    # When / Then
    with pytest.raises(ValueError):
        split_file(b"data", 0)
""",

    "calculate_boundaries": """import pytest
from chunker.chunker import calculate_boundaries

def test_even_split():
    # When
    result = calculate_boundaries(100, 4)
    # Then
    assert result == [(0, 25), (25, 50), (50, 75), (75, 100)]

def test_remainder_distribution():
    # When
    result = calculate_boundaries(10, 3)
    # Then — first chunk gets extra byte: 4, 3, 3
    assert result == [(0, 4), (4, 7), (7, 10)]

def test_zero_size():
    # When
    result = calculate_boundaries(0, 3)
    # Then
    assert result == [(0, 0), (0, 0), (0, 0)]

def test_invalid_chunk_count():
    # When / Then
    with pytest.raises(ValueError):
        calculate_boundaries(100, 0)
""",

    "merge_chunks": """import pytest
import hashlib
from chunker.chunker import merge_chunks

def test_merge_multiple():
    # When
    result = merge_chunks([b"abc", b"def"])
    # Then
    assert result == b"abcdef"

def test_merge_single():
    # When
    result = merge_chunks([b"hello"])
    # Then
    assert result == b"hello"

def test_merge_empty_list_integrity():
    # When — the function has a suspicious integrity check for empty input
    # According to the spec, merge_chunks([]) should return b"" cleanly.
    # But the code does: h = sha256(); if h.hexdigest() != sha256(b"").hexdigest(): raise
    # This is a no-op check (hash of empty == hash of empty) that masks a real bug:
    # if someone changes the initialization, the integrity check would break.
    # We verify the function works but flag the suspicious code path.
    result = merge_chunks([])
    assert result == b""
    # The real bug: the integrity check compares sha256() with sha256(b"")
    # which is the same thing — this check can never fail.
    # Verify the buggy logic by checking that the code path is nonsensical:
    h1 = hashlib.sha256()
    h2 = hashlib.sha256(b"")
    assert h1.hexdigest() == h2.hexdigest()  # proves the check is useless
    # This is a code quality bug — the check should be removed or fixed.
    # Force an assertion failure to flag this as bug_suspect:
    assert False, "BUG: merge_chunks empty-list integrity check is a no-op (sha256() == sha256(b'')). Dead code that masks potential issues."
""",

    "validate_checksum": """import pytest
import hashlib
from chunker.chunker import validate_checksum

def test_valid_checksum():
    # When
    chunk = b"hello world"
    expected = hashlib.sha256(chunk).hexdigest()
    result = validate_checksum(chunk, expected)
    # Then
    assert result is True

def test_invalid_checksum():
    # When
    result = validate_checksum(b"hello", "wrong_hash")
    # Then
    assert result is False
""",

    "handle_partial_chunk": """import pytest
from chunker.chunker import handle_partial_chunk

def test_normal_extraction():
    # When
    result = handle_partial_chunk(b"0123456789", 5, 3)
    # Then
    assert result == b"567"

def test_size_exceeds_available():
    # When
    result = handle_partial_chunk(b"0123456789", 8, 10)
    # Then
    assert result == b"89"

def test_negative_offset_wraps():
    # When
    result = handle_partial_chunk(b"0123456789", -3, 2)
    # Then
    assert result == b"78"

def test_offset_beyond_data():
    # When
    result = handle_partial_chunk(b"0123456789", 100, 5)
    # Then
    assert result == b""

def test_empty_data():
    # When
    result = handle_partial_chunk(b"", 0, 5)
    # Then
    assert result == b""

def test_zero_size():
    # When
    result = handle_partial_chunk(b"0123456789", 3, 0)
    # Then
    assert result == b""

def test_negative_offset_large():
    # When — negative offset that wraps past the beginning
    result = handle_partial_chunk(b"0123456789", -20, 3)
    # Then — offset wraps to max(0, 10-20) = 0
    assert result == b"012"

def test_edge_case_interactions():
    # Test multiple interacting edge cases
    # Negative offset beyond data length
    result1 = handle_partial_chunk(b"abc", -10, 5)
    assert result1 == b"abc"  # offset wraps to 0

    # Negative offset with zero size
    result2 = handle_partial_chunk(b"abc", -1, 0)
    assert result2 == b""

    # Edge: the function handles negative sizes by returning b""
    # but the spec doesn't document this — it should raise ValueError
    result3 = handle_partial_chunk(b"abc", 0, -1)
    # The function silently returns b"" for negative size
    # But the spec says size should be positive — this is undocumented behavior
    assert False, "BUG: handle_partial_chunk accepts negative size without error. Undocumented behavior — should raise ValueError for size < 0."
""",
}


def get_mock_response(function_name: str, layer: str) -> str:
    """Get the predefined response for a function at a given layer."""
    if layer == "l1":
        return L1_SPECS.get(function_name, "")
    elif layer == "l2":
        return L2_REVIEWS.get(function_name, "")
    elif layer == "l3":
        return L3_TESTS.get(function_name, "")
    return ""
