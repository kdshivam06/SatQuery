"""Workflow planner for SatQuery AI."""

from __future__ import annotations


def create_execution_plan(intent: str, manifest: dict) -> dict:
    """Create an observable tool execution plan."""

    common = [
        {"id": "metadata_summary", "tool": "metadata_summary", "depends_on": [], "resource": "cpu"},
    ]

    if intent == "captioning":
        steps = common + [
            {"id": "rs_vlm", "tool": "rs_vlm_caption_vqa", "depends_on": ["metadata_summary"], "resource": "cpu"},
        ]
    elif intent == "single_image_vqa":
        steps = common + [
            {"id": "rs_vlm", "tool": "rs_vlm_caption_vqa", "depends_on": ["metadata_summary"], "resource": "cpu"},
        ]
    elif intent == "grounding":
        steps = common + [
            {"id": "ndwi_water", "tool": "ndwi_water", "depends_on": ["metadata_summary"], "resource": "cpu"},
            {"id": "sar_water", "tool": "sar_water", "depends_on": ["metadata_summary"], "resource": "cpu"},
            {"id": "rs_vlm", "tool": "rs_vlm_caption_vqa", "depends_on": ["metadata_summary"], "resource": "cpu"},
        ]
    elif intent == "cross_modal_analysis":
        steps = common + [
            {"id": "pair_compatibility", "tool": "pair_compatibility", "depends_on": ["metadata_summary"], "resource": "cpu"},
            {"id": "ndwi_water", "tool": "ndwi_water", "depends_on": ["metadata_summary"], "resource": "cpu"},
            {"id": "ndbi_builtup", "tool": "ndbi_builtup", "depends_on": ["metadata_summary"], "resource": "cpu"},
            {"id": "sar_water", "tool": "sar_water", "depends_on": ["metadata_summary"], "resource": "cpu"},
            {"id": "sar_builtup", "tool": "sar_builtup", "depends_on": ["metadata_summary"], "resource": "cpu"},
            {"id": "rs_vlm", "tool": "rs_vlm_caption_vqa", "depends_on": ["metadata_summary"], "resource": "cpu"},
        ]
    elif intent == "change_analysis":
        steps = common + [
            {"id": "change_map", "tool": "change_map", "depends_on": ["metadata_summary"], "resource": "cpu"},
            {"id": "rs_vlm", "tool": "rs_vlm_caption_vqa", "depends_on": ["metadata_summary"], "resource": "cpu"},
        ]
    elif intent == "retrieval":
        steps = common + [
            {"id": "retrieval", "tool": "retrieval_stub", "depends_on": ["metadata_summary"], "resource": "cpu"},
        ]
    else:
        steps = common

    return {
        "workflow": intent,
        "steps": steps,
        "parallel_groups": _parallel_groups(steps),
    }


def _parallel_groups(steps: list[dict]) -> list[list[str]]:
    groups: list[list[str]] = []
    remaining = {step["id"]: step for step in steps}
    completed: set[str] = set()
    while remaining:
        ready = [
            step_id
            for step_id, step in remaining.items()
            if all(dep in completed for dep in step.get("depends_on", []))
        ]
        if not ready:
            groups.append(list(remaining))
            break
        groups.append([remaining[step_id]["tool"] for step_id in ready])
        completed.update(ready)
        for step_id in ready:
            del remaining[step_id]
    return groups
