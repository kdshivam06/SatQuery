"""Filesystem-backed run/session store for the prototype backend."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4


TERMINAL_STATUSES = {"completed", "failed"}


class RunStore:
    """Small JSON store for run state, traces, artifacts, and reports."""

    def __init__(self, root_dir: str | Path = "runs/api"):
        self.root_dir = Path(root_dir)
        self.root_dir.mkdir(parents=True, exist_ok=True)

    def create_run(self, query: str, *, mode: str = "auto") -> dict:
        run_id = f"run_{uuid4().hex[:12]}"
        run_dir = self.run_dir(run_id)
        run_dir.mkdir(parents=True, exist_ok=True)
        state = {
            "run_id": run_id,
            "status": "queued",
            "query": query,
            "mode": mode,
            "created_at": _now(),
            "updated_at": _now(),
            "current_step": None,
            "progress": 0.0,
            "answer": None,
            "confidence": None,
            "visual_outputs": [],
            "artifacts": [],
            "trace": [],
            "manifest": None,
            "error": None,
        }
        self.save_state(run_id, state)
        return state

    def run_dir(self, run_id: str) -> Path:
        _validate_run_id(run_id)
        return self.root_dir / run_id

    def state_path(self, run_id: str) -> Path:
        return self.run_dir(run_id) / "state.json"

    def get_state(self, run_id: str) -> dict:
        path = self.state_path(run_id)
        if not path.exists():
            raise KeyError(f"Unknown run_id: {run_id}")
        return json.loads(path.read_text(encoding="utf-8"))

    def save_state(self, run_id: str, state: dict) -> dict:
        state["updated_at"] = _now()
        path = self.state_path(run_id)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(state, indent=2), encoding="utf-8")
        return state

    def update(self, run_id: str, **changes) -> dict:
        state = self.get_state(run_id)
        state.update(changes)
        return self.save_state(run_id, state)

    def append_trace(self, run_id: str, event: dict) -> dict:
        state = self.get_state(run_id)
        state.setdefault("trace", []).append({"timestamp": _now(), **event})
        return self.save_state(run_id, state)

    def list_runs(self, limit: int = 25) -> list[dict]:
        states = []
        for state_path in sorted(self.root_dir.glob("run_*/state.json"), reverse=True):
            states.append(json.loads(state_path.read_text(encoding="utf-8")))
            if len(states) >= limit:
                break
        return states


def _now() -> str:
    return datetime.now(UTC).isoformat()


def _validate_run_id(run_id: str) -> None:
    if not run_id.startswith("run_") or not run_id.replace("run_", "").isalnum():
        raise ValueError(f"Invalid run_id: {run_id}")
