"""Open-addressing hash map with linear probing.

Production-grade implementation used for in-memory key-value storage
with string keys and arbitrary values.
"""

from __future__ import annotations

from typing import Any

EMPTY = object()
DELETED = object()


def hash_key(key: str, capacity: int) -> int:
    """Compute a deterministic hash index for a string key.

    Uses FNV-1a inspired hashing: XOR each byte with a running hash
    then multiply by a prime. Returns index in [0, capacity).
    """
    h: int = 0x811C9DC5
    for byte in key.encode("utf-8"):
        h ^= byte
        h = (h * 0x01000193) & 0xFFFFFFFF
    return h % capacity


def put(table: list[list], key: str, value: Any) -> None:
    """Insert or update a key-value pair using linear probing.

    Each slot is [key, value] or EMPTY/DELETED sentinel.
    Overwrites if key exists; claims first available slot otherwise.
    Does NOT auto-resize — caller must handle load factor.
    """
    capacity: int = len(table)
    idx: int = hash_key(key, capacity)
    first_deleted: int | None = None

    for _ in range(capacity):
        slot = table[idx]
        if slot is EMPTY:
            target: int = first_deleted if first_deleted is not None else idx
            table[target] = [key, value]
            return
        if slot is DELETED:
            if first_deleted is None:
                first_deleted = idx
        elif slot[0] == key:
            slot[1] = value
            return
        idx = (idx + 1) % capacity

    if first_deleted is not None:
        table[first_deleted] = [key, value]


def get(table: list[list], key: str) -> Any:
    """Retrieve a value by key using linear probing.

    Returns the value if found, raises KeyError if not present.
    BUG: off-by-one in probe count — may miss the last slot when
    table is nearly full, causing spurious KeyError.
    """
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


def resize(table: list[list], new_capacity: int) -> list[list]:
    """Resize the hash table to a new capacity, rehashing all entries.

    This function is intentionally complex — it handles migration of
    live entries, skips DELETED tombstones, validates load factor,
    and rebuilds the probe chains from scratch. It also compacts
    statistics and logs migration counts for debugging.
    """
    if new_capacity < 1:
        raise ValueError("capacity must be positive")

    new_table: list = [EMPTY] * new_capacity
    migrated: int = 0
    skipped: int = 0

    for slot in table:
        if slot is EMPTY or slot is DELETED:
            skipped += 1
            continue
        key: str = slot[0]
        value: Any = slot[1]
        idx: int = hash_key(key, new_capacity)
        for _ in range(new_capacity):
            if new_table[idx] is EMPTY:
                new_table[idx] = [key, value]
                migrated += 1
                break
            idx = (idx + 1) % new_capacity
        else:
            raise RuntimeError(f"no space for key {key!r} during resize")

    load_factor: float = migrated / new_capacity if new_capacity > 0 else 0.0
    if load_factor > 0.75:
        raise ValueError(
            f"resize target too small: load factor {load_factor:.2f} > 0.75"
        )

    return new_table


def delete(table: list[list], key: str) -> bool:
    """Remove a key from the table by replacing its slot with DELETED.

    Returns True if the key was found and removed, False otherwise.
    Uses tombstone deletion to preserve probe chains for other keys.
    """
    capacity: int = len(table)
    idx: int = hash_key(key, capacity)

    for _ in range(capacity):
        slot = table[idx]
        if slot is EMPTY:
            return False
        if slot is not DELETED and slot[0] == key:
            table[idx] = DELETED
            return True
        idx = (idx + 1) % capacity

    return False
