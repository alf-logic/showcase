"""SSE streaming helpers for pipeline events."""

from __future__ import annotations

import json


def format_sse(event_type: str, data: dict) -> str:
    """Format a server-sent event string."""
    return f"event: {event_type}\ndata: {json.dumps(data)}\n\n"
