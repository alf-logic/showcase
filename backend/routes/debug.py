"""Debug endpoints for git graph and agent conversations."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException

from db import DB

router: APIRouter = APIRouter(prefix="/debug", tags=["debug"])


@router.get("/git-graph/{run_id}")
async def git_graph(run_id: str) -> dict:
    """Return git operations for visualization."""
    db: DB = DB()
    run = db.get_run(run_id)
    if not run:
        db.close()
        raise HTTPException(status_code=404, detail="Run not found")

    ops = db.get_git_operations(run_id)
    db.close()
    return {"run_id": run_id, "operations": ops}


@router.get("/conversations/{run_id}/{function_id}")
async def conversations(run_id: str, function_id: str) -> dict:
    """Return agent conversation logs for a function."""
    db: DB = DB()
    logs = db.get_agent_logs(function_id)
    db.close()
    return {"run_id": run_id, "function_id": function_id, "logs": logs}


@router.get("/conversations/{run_id}")
async def all_conversations(run_id: str) -> dict:
    """Return all agent conversations for a run, grouped by function."""
    db: DB = DB()
    run = db.get_run(run_id)
    if not run:
        db.close()
        raise HTTPException(status_code=404, detail="Run not found")

    functions = db.get_functions_for_run(run_id)
    result: dict[str, list] = {}
    for fn in functions:
        logs = db.get_agent_logs(fn["id"])
        result[fn["name"]] = logs
    db.close()
    return {"run_id": run_id, "conversations": result}
