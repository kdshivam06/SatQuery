"""Demo mode API routes – serves hardcoded scenarios for UI demonstration."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException
from backend.api.demo_scenarios import DEMO_SCENARIOS, DEMO_BY_TOOL, DEMO_BY_ID

router = APIRouter(prefix="/api/demo", tags=["demo"])


@router.get("/scenarios")
async def list_scenarios():
    """Return all demo scenarios (lightweight — no audit steps)."""
    return {
        "scenarios": [
            {
                "id": s["id"],
                "query": s["query"],
                "tool": s["tool"],
                "model": s["model"],
                "role": s["role"],
                "workflow": s["workflow"],
            }
            for s in DEMO_SCENARIOS
        ]
    }


@router.get("/scenarios/{demo_id}")
async def get_scenario(demo_id: str):
    """Return full scenario including answer, audit steps, evidence."""
    scenario = DEMO_BY_ID.get(demo_id)
    if not scenario:
        raise HTTPException(status_code=404, detail=f"Demo scenario '{demo_id}' not found.")
    return scenario


@router.get("/by-tool/{tool_name}")
async def get_scenario_by_tool(tool_name: str):
    """Return the demo scenario for a specific tool name."""
    scenario = DEMO_BY_TOOL.get(tool_name)
    if not scenario:
        raise HTTPException(status_code=404, detail=f"No demo scenario for tool '{tool_name}'.")
    return scenario
