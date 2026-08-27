"""LLM-based router – uses Qwen3 or similar to produce strict JSON execution plans.

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
ROUTER_LLM_MODEL_ID = os.getenv("ROUTER_LLM_MODEL_ID", "Qwen/Qwen2.5-1.5B-Instruct")

SYSTEM_PROMPT = """You are the SatQuery AI Router.

Your job is to convert a user query and image metadata into a strict JSON execution plan.

You do not answer the user directly.
You do not run tools.
You only select, sequence, and configure tools from the provided registry.

Rules:
1. Output valid JSON only.
2. Select the minimum tools required to satisfy the query.
3. Prefer static geospatial function tools for measurable evidence when applicable.
4. Use the custom SAR-optical dual encoder as the primary cross-modal tool for SAR-optical pair matching, pair validation, and similarity confidence.
5. Use CROMA as an additional SAR-optical feature tool when the input is a SAR-optical pair and local GPU light resources are available.
6. Use RS-LLaVA for single-image remote-sensing VQA, captioning, scene description, and optical semantic reasoning.
7. Use TEOChat for bi-temporal change VQA or change description.
8. Use SegEarth-OV only when text-guided segmentation or masks are explicitly required and the endpoint is enabled.
9. Use SARCLIP only for SAR image-text inference or zero-shot SAR classification. Do not use SARCLIP for primary SAR-optical retrieval.
10. Skip unavailable or disabled tools and include a clear skipped_tools reason.
11. Do not generate hidden reasoning text. Only generate the execution plan JSON.
12. Include dependencies so the executor can run independent tools in parallel.
13. Always include audit-friendly tool names, parameters, and resource lanes.
14. If required metadata or modality information is missing, route to metadata_reader, preview_generator first.
15. Never invent a tool not present in the registry.

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
        try:
            plan = _llm_route(router_input)
            if plan:
                logger.info("LLM router produced a valid execution plan.")
                return plan
        except Exception as exc:
            logger.warning("LLM router failed: %s. Falling back to deterministic router.", exc)

        if ROUTER_MODE == "llm_with_fallback":
            logger.info("Falling back to deterministic router.")
            return fallback_route(router_input)

        raise RuntimeError("LLM router failed and no fallback is configured (ROUTER_MODE=llm).")

    logger.info("Unknown ROUTER_MODE=%s, using fallback.", ROUTER_MODE)
    return fallback_route(router_input)


def _llm_route(router_input: dict) -> ExecutionPlan | None:
    """Call the LLM and parse its JSON output into an ExecutionPlan."""
    try:
        from backend.geospatial.dependencies import require_module
        transformers = require_module("transformers", "transformers")
    except Exception:
        logger.warning("transformers not installed; cannot use LLM router.")
        return None

    try:
        tokenizer = transformers.AutoTokenizer.from_pretrained(ROUTER_LLM_MODEL_ID)
        model = transformers.AutoModelForCausalLM.from_pretrained(
            ROUTER_LLM_MODEL_ID,
            torch_dtype="auto",
            device_map="auto",
        )
    except Exception as exc:
        logger.warning("Failed to load LLM model %s: %s", ROUTER_LLM_MODEL_ID, exc)
        return None

    user_message = json.dumps(router_input, indent=2)
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": user_message},
    ]

    text = tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
    inputs = tokenizer([text], return_tensors="pt").to(model.device)

    import torch
    with torch.no_grad():
        outputs = model.generate(
            **inputs,
            max_new_tokens=int(os.getenv("ROUTER_LLM_MAX_TOKENS", "2048")),
            temperature=float(os.getenv("ROUTER_LLM_TEMPERATURE", "0.1")),
            do_sample=True,
        )

    generated = tokenizer.decode(outputs[0][inputs["input_ids"].shape[-1]:], skip_special_tokens=True)

    # Extract JSON from response
    plan_json = _extract_json(generated)
    if plan_json is None:
        logger.warning("LLM output did not contain valid JSON.")
        return None

    try:
        return ExecutionPlan.model_validate(plan_json)
    except Exception as exc:
        logger.warning("LLM JSON failed Pydantic validation: %s", exc)
        return None


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
