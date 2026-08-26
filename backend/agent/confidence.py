"""Weighted confidence fusion for final answer generation."""

from __future__ import annotations


def calculate_final_confidence(tool_results: dict[str, dict]) -> float:
    """Compute a weighted average confidence from all tool results.

    Static tools get lower weight, models get higher weight.
    The custom dual encoder gets the highest weight.
    """
    if not tool_results:
        return 0.5

    weighted_sum = 0.0
    total_weight = 0.0

    weights = {
        "static_function": 1.0,
        "pretrained_model": 2.0,
        "custom_model": 3.0,
    }

    for name, result in tool_results.items():
        if result.get("status") != "success":
            continue

        conf = result.get("confidence")
        if conf is None:
            continue

        # Look up weight based on tool type (default to 1.0)
        from backend.tools.registry import TOOL_REGISTRY
        tool = TOOL_REGISTRY.get(name)
        ttype = getattr(tool, "tool_type", "static_function") if tool else "static_function"

        w = weights.get(ttype, 1.0)
        weighted_sum += conf * w
        total_weight += w

    if total_weight == 0:
        return 0.5

    return round(min(0.99, max(0.01, weighted_sum / total_weight)), 2)
