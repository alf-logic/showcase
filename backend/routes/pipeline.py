"""Pipeline API routes — start pipeline and stream progress via SSE."""

from __future__ import annotations

import asyncio
import threading
from collections.abc import AsyncIterator
from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from db import DB
from pipeline import run_pipeline
from routes.repo import _cloned_repo
from streaming import format_sse

router: APIRouter = APIRouter(prefix="/pipeline", tags=["pipeline"])

# In-memory event queues per run_id
_event_queues: dict[str, list[dict[str, Any]]] = {}
_pipeline_done: dict[str, bool] = {}


class StartRequest(BaseModel):
    model: str = "gpt-4o-mini"
    budget_limit: float = 2.0


class StartResponse(BaseModel):
    run_id: str
    status: str


def _run_pipeline_thread(run_id: str, clone_path: str, model: str) -> None:
    """Run the pipeline in a background thread (blocking LLM calls)."""
    db: DB = DB()
    events: list[dict[str, Any]] = _event_queues[run_id]

    def on_event(event: dict[str, Any]) -> None:
        events.append(event)

    try:
        run_pipeline(db, run_id, clone_path, model=model, on_event=on_event)
    except Exception as exc:
        events.append({"type": "pipeline_error", "error": str(exc)})
    finally:
        _pipeline_done[run_id] = True
        db.close()


@router.post("/start")
async def pipeline_start(req: StartRequest) -> StartResponse:
    """Start the pipeline for the currently loaded repo."""
    if "current" not in _cloned_repo:
        raise HTTPException(status_code=400, detail="No repo loaded. Call POST /api/repo/load first.")

    clone_path: str = str(_cloned_repo["current"])

    # Create run in DB
    db: DB = DB()
    run_id: str = db.create_run(
        repo_url=clone_path,
        clone_path=clone_path,
        budget_limit=req.budget_limit,
    )
    db.close()

    # Set up event queue
    _event_queues[run_id] = []
    _pipeline_done[run_id] = False

    # Start pipeline in background thread
    thread: threading.Thread = threading.Thread(
        target=_run_pipeline_thread,
        args=(run_id, clone_path, req.model),
        daemon=True,
    )
    thread.start()

    return StartResponse(run_id=run_id, status="started")


@router.get("/stream/{run_id}")
async def pipeline_stream(run_id: str) -> StreamingResponse:
    """SSE stream of pipeline events."""
    if run_id not in _event_queues:
        raise HTTPException(status_code=404, detail="Run not found")

    async def event_generator() -> AsyncIterator[str]:
        sent: int = 0
        while True:
            events: list[dict[str, Any]] = _event_queues[run_id]
            while sent < len(events):
                event: dict[str, Any] = events[sent]
                event_type: str = event.get("type", "message")
                yield format_sse(event_type, event)
                sent += 1

            if _pipeline_done.get(run_id, False) and sent >= len(events):
                yield format_sse("done", {"message": "Pipeline complete"})
                break

            await asyncio.sleep(0.3)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.get("/results/{run_id}")
async def pipeline_results(run_id: str) -> dict:
    """Get the final results for a pipeline run."""
    db: DB = DB()
    run = db.get_run(run_id)
    if not run:
        db.close()
        raise HTTPException(status_code=404, detail="Run not found")

    functions = db.get_functions_for_run(run_id)
    git_ops = db.get_git_operations(run_id)
    db.close()

    return {
        "run": run,
        "functions": functions,
        "git_operations_count": len(git_ops),
    }
