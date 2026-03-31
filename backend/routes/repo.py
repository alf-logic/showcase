"""Routes for loading and parsing a git repository."""

from __future__ import annotations

import ast
import shutil
import subprocess
import tempfile
from pathlib import Path

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router: APIRouter = APIRouter(prefix="/repo", tags=["repo"])

# Store the cloned repo path for later use by other stages.
_cloned_repo: dict[str, Path] = {}


class LoadRequest(BaseModel):
    repo_url: str


class FunctionInfo(BaseModel):
    name: str
    file: str
    line: int
    args: list[str]


class FileNode(BaseModel):
    name: str
    path: str
    type: str  # "file" or "directory"
    children: list["FileNode"] | None = None
    functions: list[FunctionInfo] | None = None


class LoadResponse(BaseModel):
    repo_name: str
    tree: list[FileNode]
    clone_path: str


def _clone_repo(repo_url: str) -> Path:
    """Clone a git repo (or copy a local path) into a temp directory."""
    tmp_dir: Path = Path(tempfile.mkdtemp(prefix="fv-demo-"))
    source: Path = Path(repo_url)

    if source.is_dir():
        # Local path — clone it
        clone_target: Path = tmp_dir / source.name
        subprocess.run(
            ["git", "clone", str(source), str(clone_target)],
            check=True,
            capture_output=True,
            text=True,
        )
        return clone_target
    else:
        # Remote URL
        repo_name: str = repo_url.rstrip("/").split("/")[-1].removesuffix(".git")
        clone_target = tmp_dir / repo_name
        subprocess.run(
            ["git", "clone", repo_url, str(clone_target)],
            check=True,
            capture_output=True,
            text=True,
        )
        return clone_target


def _extract_functions(filepath: Path) -> list[FunctionInfo]:
    """Parse a Python file and extract top-level function definitions."""
    try:
        source: str = filepath.read_text(encoding="utf-8")
        tree = ast.parse(source, filename=str(filepath))
    except (SyntaxError, UnicodeDecodeError):
        return []

    functions: list[FunctionInfo] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef):
            args: list[str] = []
            for arg in node.args.args:
                args.append(arg.arg)
            functions.append(
                FunctionInfo(
                    name=node.name,
                    file=str(filepath),
                    line=node.lineno,
                    args=args,
                )
            )
    return functions


def _build_tree(root: Path, base: Path) -> list[FileNode]:
    """Recursively build a file tree with function info for Python files."""
    nodes: list[FileNode] = []

    entries = sorted(root.iterdir(), key=lambda p: (p.is_file(), p.name))
    for entry in entries:
        if entry.name.startswith(".") or entry.name == "__pycache__":
            continue

        rel_path: str = str(entry.relative_to(base))

        if entry.is_dir():
            children: list[FileNode] = _build_tree(entry, base)
            if children:  # skip empty dirs
                nodes.append(
                    FileNode(
                        name=entry.name,
                        path=rel_path,
                        type="directory",
                        children=children,
                    )
                )
        elif entry.suffix == ".py" and entry.name != "__init__.py":
            functions: list[FunctionInfo] = _extract_functions(entry)
            # Make file paths relative
            for fn in functions:
                fn.file = rel_path
            nodes.append(
                FileNode(
                    name=entry.name,
                    path=rel_path,
                    type="file",
                    functions=functions,
                )
            )

    return nodes


@router.post("/load")
async def load_repo(req: LoadRequest) -> LoadResponse:
    """Clone the repo, parse Python files, return the file tree with functions."""
    try:
        clone_path: Path = _clone_repo(req.repo_url)
    except subprocess.CalledProcessError as exc:
        raise HTTPException(
            status_code=400,
            detail=f"Failed to clone repository: {exc.stderr}",
        )

    repo_name: str = clone_path.name
    tree: list[FileNode] = _build_tree(clone_path, clone_path)

    # Store for later stages
    _cloned_repo["current"] = clone_path

    return LoadResponse(
        repo_name=repo_name,
        tree=tree,
        clone_path=str(clone_path),
    )


@router.get("/file/{file_path:path}")
async def get_file(file_path: str) -> dict[str, str]:
    """Return the contents of a file in the cloned repo."""
    if "current" not in _cloned_repo:
        raise HTTPException(status_code=400, detail="No repo loaded")

    full_path: Path = _cloned_repo["current"] / file_path
    if not full_path.is_file():
        raise HTTPException(status_code=404, detail="File not found")

    return {"content": full_path.read_text(encoding="utf-8"), "path": file_path}
