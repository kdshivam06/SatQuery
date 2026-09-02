"""LLM-based router – uses HF Inference API (free) for smart JSON routing.

Falls back to the deterministic router on parse failure.
"""

from __future__ import annotations

import json
import logging
import os

from backend.agent.fallback_router import fallback_route
from backend.agent.planner_schema import ExecutionPlan

logger = logging.getLogger(__name__)

ROUTER_MODE = os.getenv("ROUTER_MODE", "fallback")
# Remote model for routing (free via HF Inference API — no local GPU needed)
ROUTER_LLM_MODEL_ID = os.getenv("ROUTER_LLM_MODEL_ID", "Qwen/Qwen2.5-72B-Instruct")

SYSTEM_PROMPT = """You are the SatQuery AI Router.

Your job is to convert a user query and image metadata into a strict JSON execution plan.

You do not answer the user directly.
You do not run tools.
You only select, sequence, and configure tools from the provided registry.

Rules:
1. Output valid JSON only. No markdown fences, no explanation text.
2. Select the minimum tools required to satisfy the query.
3. Always include metadata_reader and preview_generator in the first group.
4. Prefer static geospatial function tools for measurable evidence when applicable.
5. Use the custom SAR-optical dual encoder as the primary cross-modal tool for SAR-optical pair matching, pair validation, and similarity confidence.
6. Use CROMA as an additional SAR-optical feature tool when the input is a SAR-optical pair and local GPU light resources are available.
7. Use RS-LLaVA (rsllava_vqa_caption_tool) for single-image remote-sensing VQA, captioning, scene description, and optical semantic reasoning.
8. Use TEOChat for bi-temporal change VQA or change description.
9. Use SegEarth-OV only when text-guided segmentation or masks are explicitly required and the endpoint is enabled.
10. Use SARCLIP only for SAR image-text inference or zero-shot SAR classification. Do not use SARCLIP for primary SAR-optical retrieval.
11. Skip unavailable or disabled tools and include a clear skipped_tools reason.
12. Do not generate hidden reasoning text. Only generate the execution plan JSON.
13. Include dependencies so the executor can run independent tools in parallel.
14. Always include audit-friendly tool names, parameters, and resource lanes.
15. If required metadata or modality information is missing, route to metadata_reader, preview_generator first.
16. Never invent a tool not present in the registry.

Output format:
{
  "workflow": "<workflow_name>",
  "intent": "<intent>",
  "requires_visual_output": true,
  "parallel_groups": [
    {
      "group_id": "<id>",
      "can_run_parallel": true,
      "steps": [
        {"step_id": "<id>", "tool": "<tool_name>", "depends_on": [], "resource_lane": "<lane>", "params": {}}
      ]
    }
  ],
  "skipped_tools": [{"tool": "<name>", "reason": "<reason>"}]
}"""


def route(router_input: dict) -> ExecutionPlan:
    """Route using LLM if configured, otherwise use deterministic fallback."""

    if ROUTER_MODE == "fallback":
        logger.info("Using deterministic fallback router (ROUTER_MODE=fallback).")
        return fallback_route(router_input)

    if ROUTER_MODE in ("llm", "llm_with_fallback"):
        llm_error = "Unknown Error"
        try:
            plan = _llm_route(router_input)
            if plan:
                logger.info("LLM router produced a valid execution plan.")
                return plan
        except Exception as exc:
            llm_error = str(exc)
            logger.warning("LLM router failed: %s. Falling back to deterministic router.", exc)

        if ROUTER_MODE == "llm_with_fallback":
            logger.info("Falling back to deterministic router.")
            return fallback_route(router_input)

        raise RuntimeError(f"LLM router failed and no fallback is configured (ROUTER_MODE=llm). Details: {llm_error}")

    logger.info("Unknown ROUTER_MODE=%s, using fallback.", ROUTER_MODE)
    return fallback_route(router_input)


def _llm_route(router_input: dict) -> ExecutionPlan | None:
    """Call the HF Inference API to route the query into an ExecutionPlan."""
    import httpx

    token = os.getenv("HF_TOKEN", "")
    if not token:
        raise ValueError("HF_TOKEN not set — cannot use LLM router via HF Inference API.")

    # Build a concise user message (avoid sending massive manifests)
    compact_input = {
        "query": router_input.get("query", ""),
        "input_summary": router_input.get("input_summary", {}),
        "available_tools": router_input.get("available_tools", []),
    }
    user_message = json.dumps(compact_input, indent=2)

    payload = {
        "model": ROUTER_LLM_MODEL_ID,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_message},
        ],
        "max_tokens": int(os.getenv("ROUTER_LLM_MAX_TOKENS", "1024")),
        "temperature": float(os.getenv("ROUTER_LLM_TEMPERATURE", "0.1")),
    }

    base_url = os.getenv(
        "HF_INFERENCE_BASE_URL",
        "https://router.huggingface.co/v1/chat/completions",
    )
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

    logger.info("Calling HF Inference API for routing (%s)...", ROUTER_LLM_MODEL_ID)
    response = httpx.post(base_url, headers=headers, json=payload, timeout=60)

    if response.is_error:
        raise RuntimeError(
            f"HF router API HTTP {response.status_code}: {response.text[:500]}"
        )

    data = response.json()
    choices = data.get("choices", [])
    if not choices:
        raise RuntimeError(f"HF router API returned no choices: {data}")

    generated = choices[0].get("message", {}).get("content", "")
    logger.info("LLM router raw output length: %d chars", len(generated))

    # Extract JSON from response
    plan_json = _extract_json(generated)
    if plan_json is None:
        logger.warning("LLM output did not contain valid JSON. Raw output: %s", generated[:500])
        raise ValueError(f"LLM output did not contain valid JSON. Raw: {generated[:300]}")

    # Normalize the LLM output to fix common structural issues
    plan_json = _fix_parallel_groups(plan_json)

    try:
        return ExecutionPlan.model_validate(plan_json)
    except Exception as exc:
        logger.warning("LLM JSON failed Pydantic validation: %s", exc)
        raise ValueError(f"LLM JSON failed Pydantic validation: {exc}") from exc


def _fix_parallel_groups(plan_json: dict) -> dict:
    """Normalize LLM output to fix common structural issues.

    The LLM sometimes puts bare step dicts directly in the
    parallel_groups list instead of wrapping them in proper group objects
    with group_id, can_run_parallel, and steps fields.
    """
    groups = plan_json.get("parallel_groups")
    if not isinstance(groups, list) or not groups:
        return plan_json

    fixed_groups = []
    for i, item in enumerate(groups):
        if not isinstance(item, dict):
            continue

        # Already a proper group (has group_id and steps)
        if "group_id" in item and "steps" in item:
            fixed_groups.append(item)
        # Bare step dict (has step_id and tool but no group_id)
        elif "step_id" in item and "tool" in item:
            fixed_groups.append({
                "group_id": f"auto_group_{i}",
                "can_run_parallel": False,
                "steps": [item],
            })
        else:
            # Unknown format, keep as-is and let Pydantic handle validation
            fixed_groups.append(item)

    plan_json["parallel_groups"] = fixed_groups

    # Also fix skipped_tools if it's nested inside the last group
    if "skipped_tools" not in plan_json or not plan_json["skipped_tools"]:
        plan_json["skipped_tools"] = []

    logger.debug("Fixed parallel_groups: %d groups after normalization.", len(fixed_groups))
    return plan_json


def _extract_json(text: str) -> dict | None:
    """Try to extract a JSON object from LLM output text."""
    # Try direct parse
    try:
        return json.loads(text.strip())
    except json.JSONDecodeError:
        pass

    # Try to find JSON block in markdown fences
    import re
    match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(1))
        except json.JSONDecodeError:
            pass

    # Try to find first { ... } block
    start = text.find("{")
    end = text.rfind("}")
    if start != -1 and end > start:
        try:
            return json.loads(text[start:end + 1])
        except json.JSONDecodeError:
            pass

    return None
