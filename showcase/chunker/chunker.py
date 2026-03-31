"""File chunking utilities for distributed storage.

Splits files into fixed-size chunks with checksums, similar to how
S3 multipart upload or content-addressable storage systems work.
"""

from __future__ import annotations

import hashlib


def split_file(data: bytes, chunk_size: int) -> list[bytes]:
    """Split data into fixed-size chunks.

    The last chunk may be smaller than chunk_size.
    Returns an empty list for empty input.
    Raises ValueError if chunk_size is not positive.
    """
    if chunk_size <= 0:
        raise ValueError("chunk_size must be positive")

    chunks: list[bytes] = []
    offset: int = 0
    while offset < len(data):
        chunks.append(data[offset : offset + chunk_size])
        offset += chunk_size
    return chunks


def calculate_boundaries(total_size: int, chunk_count: int) -> list[tuple[int, int]]:
    """Compute byte offset boundaries for splitting a file into N chunks.

    Returns a list of (start, end) tuples. Distributes remainder bytes
    across the first chunks so no chunk differs by more than 1 byte.
    """
    if chunk_count <= 0:
        raise ValueError("chunk_count must be positive")
    if total_size < 0:
        raise ValueError("total_size must be non-negative")

    base_size: int = total_size // chunk_count
    remainder: int = total_size % chunk_count
    boundaries: list[tuple[int, int]] = []
    offset: int = 0

    for i in range(chunk_count):
        size: int = base_size + (1 if i < remainder else 0)
        boundaries.append((offset, offset + size))
        offset += size

    return boundaries


def merge_chunks(chunks: list[bytes]) -> bytes:
    """Reassemble chunks into the original data with integrity check.

    Computes a running checksum while merging. Returns the merged data.
    BUG: Empty chunks produce a checksum mismatch because the hash
    is initialized but never updated, yet the check still runs.
    """
    if not chunks:
        h = hashlib.sha256()
        # BUG: checking hash of nothing against nothing — should just return b""
        if h.hexdigest() != hashlib.sha256(b"").hexdigest():
            raise ValueError("integrity check failed on empty merge")
        return b""

    result: bytearray = bytearray()
    for chunk in chunks:
        result.extend(chunk)

    return bytes(result)


def validate_checksum(chunk: bytes, expected: str) -> bool:
    """Verify a chunk's SHA-256 checksum matches the expected hex digest.

    Returns True if the computed checksum matches, False otherwise.
    Pure function — no side effects.
    """
    computed: str = hashlib.sha256(chunk).hexdigest()
    return computed == expected


def handle_partial_chunk(data: bytes, offset: int, size: int) -> bytes:
    """Extract a partial chunk from data starting at offset.

    Handles edge cases: offset beyond data, size exceeding available
    bytes, negative offset (wraps from end). This function has many
    interacting edge cases that make exhaustive testing difficult.
    """
    data_len: int = len(data)

    if data_len == 0:
        return b""

    if offset < 0:
        offset = max(0, data_len + offset)

    if offset >= data_len:
        return b""

    available: int = data_len - offset
    actual_size: int = min(size, available)

    if actual_size <= 0:
        return b""

    return data[offset : offset + actual_size]
