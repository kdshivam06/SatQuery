"""File save/serve helpers for API uploads and artifacts."""

from __future__ import annotations

from pathlib import Path
from shutil import copyfileobj
from typing import BinaryIO


def save_upload_file(uploaded: BinaryIO, filename: str, output_dir: str | Path) -> str:
    safe_name = Path(filename).name
    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / safe_name
    with out_path.open("wb") as handle:
        copyfileobj(uploaded, handle)
    return str(out_path)


def resolve_run_file(run_dir: str | Path, relative_path: str) -> Path:
    root = Path(run_dir).resolve()
    target = (root / relative_path).resolve()
    if root != target and root not in target.parents:
        raise ValueError(f"File path escapes run directory: {relative_path}")
    if not target.exists() or not target.is_file():
        raise FileNotFoundError(relative_path)
    return target
