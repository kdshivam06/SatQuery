"""Deterministic fallback router — always produces a valid ExecutionPlan.

Implements all 6 workflow routing rules from the spec. Used as primary router
when ROUTER_MODE=fallback, or as safety net when the LLM router fails.
"""

from __future__ import annotations

import os

from backend.agent.planner_schema import ExecutionPlan, ExecutionStep, ParallelGroup, SkippedTool
from backend.tools.registry import TOOL_REGISTRY


def fallback_route(router_input: dict) -> ExecutionPlan:
    """Generate a deterministic execution plan from the router input."""

    query = router_input.get("query", "").lower()
    summary = router_input.get("input_summary", {})
    configuration = summary.get("configuration", "single")
    modalities = summary.get("modalities", [])
    available = set(router_input.get("available_tools", []))
    bands = summary.get("available_bands", {})

    intent = _classify_intent(query, configuration, modalities)
    skipped: list[SkippedTool] = []

    # ── Build parallel groups based on workflow ───────────

    if intent == "cross_modal_analysis":
        plan = _cross_modal_plan(available, modalities, bands, skipped)
    elif intent == "change_analysis":
        plan = _change_analysis_plan(available, skipped)
    elif intent == "grounding":
        plan = _grounding_plan(available, modalities, bands, skipped)
    elif intent == "sar_text_inference":
        plan = _sar_text_plan(available, skipped)
    elif intent == "retrieval":
        plan = _retrieval_plan(available, modalities, skipped)
    elif intent == "captioning":
        plan = _captioning_plan(available, skipped)
    else:  # single_image_vqa
        plan = _vqa_plan(available, skipped)

    # Always skip disabled tools with reason
    _add_disabled_skips(available, skipped)

    return ExecutionPlan(
        workflow=intent,
        intent=intent,
        requires_visual_output=True,
        parallel_groups=plan,
        skipped_tools=skipped,
    )


# ── Workflow builders ─────────────────────────────────────


def _preprocess_group(available: set[str]) -> ParallelGroup:
    steps = []
    for tool_name in ("metadata_reader", "preview_generator"):
        if tool_name in available:
            steps.append(ExecutionStep(step_id=tool_name, tool=tool_name, resource_lane="cpu"))
    return ParallelGroup(group_id="g1_preprocess", can_run_parallel=True, steps=steps)


def _vqa_plan(available: set[str], skipped: list) -> list[ParallelGroup]:
    groups = [_preprocess_group(available)]
    specialist_steps = []
    geochat_configured = bool(
        os.getenv("GEOCHAT_SPACE_ID")
        or os.getenv("GEOCHAT_ENDPOINT")
        or os.getenv("HF_TOKEN")
    )
    if "geochat_vqa_caption_tool" in available and geochat_configured:
        specialist_steps.append(ExecutionStep(
            step_id="geochat_vqa", tool="geochat_vqa_caption_tool",
            depends_on=["preview_generator"], resource_lane="remote_api",
        ))
    elif "rsllava_vqa_caption_tool" in available:
        specialist_steps.append(ExecutionStep(
            step_id="rsllava_vqa", tool="rsllava_vqa_caption_tool",
            depends_on=["preview_generator"], resource_lane="remote_api",
        ))
    if "custom_sar_optical_dual_encoder_tool" in available:
        specialist_steps.append(ExecutionStep(
            step_id="dual_encoder", tool="custom_sar_optical_dual_encoder_tool",
            depends_on=["metadata_reader"], resource_lane="local_gpu_light",
        ))
    if specialist_steps:
        groups.append(ParallelGroup(group_id="g2_specialists", can_run_parallel=True, steps=specialist_steps))
    return groups


def _captioning_plan(available: set[str], skipped: list) -> list[ParallelGroup]:
    return _vqa_plan(available, skipped)  # Same flow


def _grounding_plan(available: set[str], modalities: list, bands: dict, skipped: list) -> list[ParallelGroup]:
    groups = [_preprocess_group(available)]

    evidence_steps = []
    has_ms = "multispectral" in modalities
    has_sar = "sar" in modalities
    optical_bands = bands.get("multispectral", []) + bands.get("optical", [])

    if has_ms and "ndwi_water_detector" in available:
        evidence_steps.append(ExecutionStep(step_id="ndwi", tool="ndwi_water_detector", depends_on=["metadata_reader"], resource_lane="cpu"))
    if has_sar and "sar_water_detector" in available:
        evidence_steps.append(ExecutionStep(step_id="sar_water", tool="sar_water_detector", depends_on=["metadata_reader"], resource_lane="cpu"))
    if "segearth_text_guided_segmentation_tool" in available:
        evidence_steps.append(ExecutionStep(step_id="segearth", tool="segearth_text_guided_segmentation_tool", depends_on=["preview_generator"], resource_lane="remote_api"))

    if evidence_steps:
        groups.append(ParallelGroup(group_id="g2_evidence", can_run_parallel=True, steps=evidence_steps))

    # Area + overlay
    post_steps = []
    if "area_calculator" in available:
        deps = [s.step_id for s in evidence_steps] if evidence_steps else ["metadata_reader"]
        post_steps.append(ExecutionStep(step_id="area", tool="area_calculator", depends_on=deps, resource_lane="cpu"))
    if "overlay_generator" in available:
        deps = [s.step_id for s in evidence_steps] if evidence_steps else ["preview_generator"]
        post_steps.append(ExecutionStep(step_id="overlay", tool="overlay_generator", depends_on=deps, resource_lane="cpu"))
    if post_steps:
        groups.append(ParallelGroup(group_id="g3_post", can_run_parallel=True, steps=post_steps))

    return groups


def _cross_modal_plan(available: set[str], modalities: list, bands: dict, skipped: list) -> list[ParallelGroup]:
    groups = [_preprocess_group(available)]
    geochat_configured = bool(
        os.getenv("GEOCHAT_SPACE_ID")
        or os.getenv("GEOCHAT_ENDPOINT")
        or os.getenv("HF_TOKEN")
    )

    # Validation
    val_steps = []
    # Alignment is done during ingestion, but we note it here
    groups.append(ParallelGroup(group_id="g2_validation", can_run_parallel=False, steps=val_steps) if val_steps else ParallelGroup(group_id="g2_validation"))

    # Specialists
    specialist_steps = []
    if "custom_sar_optical_dual_encoder_tool" in available:
        specialist_steps.append(ExecutionStep(step_id="dual_encoder", tool="custom_sar_optical_dual_encoder_tool", depends_on=["metadata_reader"], resource_lane="local_gpu_light"))
    if "croma_cross_modal_feature_tool" in available:
        specialist_steps.append(ExecutionStep(step_id="croma", tool="croma_cross_modal_feature_tool", depends_on=["metadata_reader"], resource_lane="local_gpu_light"))
    if "geochat_vqa_caption_tool" in available and geochat_configured:
        specialist_steps.append(ExecutionStep(
            step_id="geochat_vqa", tool="geochat_vqa_caption_tool",
            depends_on=["preview_generator"], resource_lane="remote_api",
        ))
    elif "rsllava_vqa_caption_tool" in available:
        specialist_steps.append(ExecutionStep(step_id="rsllava_vqa", tool="rsllava_vqa_caption_tool", depends_on=["preview_generator"], resource_lane="remote_api"))

    # Static evidence
    evidence_steps = []
    optical_bands = bands.get("multispectral", []) + bands.get("optical", [])
    has_ms = "multispectral" in modalities
    has_sar = "sar" in modalities

    if has_ms and "ndwi_water_detector" in available:
        evidence_steps.append(ExecutionStep(step_id="ndwi", tool="ndwi_water_detector", depends_on=["metadata_reader"], resource_lane="cpu"))
    if has_ms and "mndwi_water_detector" in available and "B11" in optical_bands:
        evidence_steps.append(ExecutionStep(step_id="mndwi", tool="mndwi_water_detector", depends_on=["metadata_reader"], resource_lane="cpu"))
    if has_ms and "ndbi_builtup_detector" in available and "B11" in optical_bands:
        evidence_steps.append(ExecutionStep(step_id="ndbi", tool="ndbi_builtup_detector", depends_on=["metadata_reader"], resource_lane="cpu"))
    if has_ms and "ndvi_vegetation_detector" in available:
        evidence_steps.append(ExecutionStep(step_id="ndvi", tool="ndvi_vegetation_detector", depends_on=["metadata_reader"], resource_lane="cpu"))
    if has_sar and "sar_water_detector" in available:
        evidence_steps.append(ExecutionStep(step_id="sar_water", tool="sar_water_detector", depends_on=["metadata_reader"], resource_lane="cpu"))
    if has_sar and "sar_builtup_detector" in available:
        evidence_steps.append(ExecutionStep(step_id="sar_builtup", tool="sar_builtup_detector", depends_on=["metadata_reader"], resource_lane="cpu"))

    if specialist_steps or evidence_steps:
        groups.append(ParallelGroup(group_id="g3_specialists", can_run_parallel=True, steps=specialist_steps + evidence_steps))

    # Fusion: mask fusion + overlay
    fusion_steps = []
    mask_producers = [s.step_id for s in evidence_steps]
    if len(mask_producers) >= 2 and "mask_fusion_tool" in available:
        fusion_steps.append(ExecutionStep(step_id="mask_fusion", tool="mask_fusion_tool", depends_on=mask_producers, resource_lane="cpu"))
    if "area_calculator" in available:
        area_deps = ["mask_fusion"] if fusion_steps else mask_producers[:1] if mask_producers else ["metadata_reader"]
        fusion_steps.append(ExecutionStep(step_id="area", tool="area_calculator", depends_on=area_deps, resource_lane="cpu"))
    if "overlay_generator" in available:
        overlay_deps = ["mask_fusion"] if fusion_steps else mask_producers[:1] if mask_producers else ["preview_generator"]
        fusion_steps.append(ExecutionStep(step_id="overlay", tool="overlay_generator", depends_on=overlay_deps, resource_lane="cpu"))
    if fusion_steps:
        groups.append(ParallelGroup(group_id="g4_fusion", can_run_parallel=False, steps=fusion_steps))

    # Skip SARCLIP
    skipped.append(SkippedTool(tool="sarclip_sar_text_tool", reason="Skipped: query requires SAR-optical joint analysis, not SAR-to-text."))

    return groups


def _change_analysis_plan(available: set[str], skipped: list) -> list[ParallelGroup]:
    groups = [_preprocess_group(available)]

    change_steps = []
    if "change_map_generator" in available:
        change_steps.append(ExecutionStep(step_id="change_map", tool="change_map_generator", depends_on=["preview_generator"], resource_lane="cpu"))
    if "teochat_change_vqa_tool" in available:
        change_steps.append(ExecutionStep(step_id="teochat", tool="teochat_change_vqa_tool", depends_on=["preview_generator"], resource_lane="remote_api"))
    if change_steps:
        groups.append(ParallelGroup(group_id="g2_change", can_run_parallel=True, steps=change_steps))

    post = []
    if "overlay_generator" in available:
        deps = ["change_map"] if "change_map_generator" in available else ["preview_generator"]
        post.append(ExecutionStep(step_id="overlay", tool="overlay_generator", depends_on=deps, resource_lane="cpu"))
    if post:
        groups.append(ParallelGroup(group_id="g3_post", can_run_parallel=True, steps=post))

    return groups


def _sar_text_plan(available: set[str], skipped: list) -> list[ParallelGroup]:
    groups = [_preprocess_group(available)]
    steps = []
    if "sarclip_sar_text_tool" in available:
        steps.append(ExecutionStep(step_id="sarclip", tool="sarclip_sar_text_tool", depends_on=["preview_generator"], resource_lane="remote_api"))
    if "sar_water_detector" in available:
        steps.append(ExecutionStep(step_id="sar_water", tool="sar_water_detector", depends_on=["metadata_reader"], resource_lane="cpu"))
    if "sar_builtup_detector" in available:
        steps.append(ExecutionStep(step_id="sar_builtup", tool="sar_builtup_detector", depends_on=["metadata_reader"], resource_lane="cpu"))
    if steps:
        groups.append(ParallelGroup(group_id="g2_sar_text", can_run_parallel=True, steps=steps))
    return groups


def _retrieval_plan(available: set[str], modalities: list, skipped: list) -> list[ParallelGroup]:
    groups = [_preprocess_group(available)]
    steps = []
    has_sar = "sar" in modalities
    has_optical = any(m in modalities for m in ("optical", "multispectral"))

    if has_sar and has_optical and "custom_sar_optical_dual_encoder_tool" in available:
        steps.append(ExecutionStep(step_id="dual_encoder", tool="custom_sar_optical_dual_encoder_tool", depends_on=["metadata_reader"], resource_lane="local_gpu_light"))
    if has_optical and "remoteclip_optical_retrieval_tool" in available:
        steps.append(ExecutionStep(step_id="remoteclip", tool="remoteclip_optical_retrieval_tool", depends_on=["preview_generator"], resource_lane="local_gpu_light"))

    if not steps:
        skipped.append(SkippedTool(tool="retrieval", reason="No retrieval gallery/index configured."))
    else:
        groups.append(ParallelGroup(group_id="g2_retrieval", can_run_parallel=True, steps=steps))
    return groups


# ── Intent classification ─────────────────────────────────


def _classify_intent(query: str, configuration: str, modalities: list) -> str:
    q = query.lower()

    if any(t in q for t in ("change", "changed", "before", "after", "increase", "decrease", "temporal")):
        return "change_analysis"
    if any(t in q for t in ("highlight", "show", "segment", "mask", "locate", "where")):
        return "grounding"
    if any(t in q for t in ("retrieve", "similar", "match", "corresponding")):
        return "retrieval"
    if any(t in q for t in ("classify sar", "sar show", "sar text", "match this text to sar")):
        return "sar_text_inference"

    if configuration == "cross_modal_pair":
        return "cross_modal_analysis"
    if configuration == "temporal_pair":
        return "change_analysis"

    if any(t in q for t in ("describe", "caption", "summarize", "land-cover", "land cover", "major objects")):
        return "captioning"

    return "single_image_vqa"


def _add_disabled_skips(available: set[str], skipped: list[SkippedTool]):
    """Add skip entries for tools that exist in registry but are disabled."""
    all_names = {"segearth_text_guided_segmentation_tool", "sarclip_sar_text_tool"}
    existing_skipped = {s.tool for s in skipped}
    for name in all_names:
        if name not in available and name not in existing_skipped:
            tool = TOOL_REGISTRY.get(name)
            if tool and not getattr(tool, "enabled", True):
                skipped.append(SkippedTool(tool=name, reason=f"{name} is disabled in configuration."))
