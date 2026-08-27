"""Answer fusion – synthesises evidence from all tool results into a final answer."""

from __future__ import annotations

from backend.agent.confidence import calculate_final_confidence


def fuse_results(
    query: str,
    tool_results: dict[str, dict],
    *,
    workflow: str = "",
) -> dict:
    """Combine tool outputs into a unified answer payload.

    Returns dict with: answer, confidence, evidence, visual_outputs.
    """

    final_confidence = calculate_final_confidence(tool_results)
    if _vlm_was_skipped(tool_results):
        final_confidence = min(final_confidence, 0.5)
    evidence = _build_evidence_list(tool_results)
    visual_outputs = _collect_visual_outputs(tool_results)
    answer = _synthesise_answer(query, tool_results, workflow, evidence, final_confidence)

    return {
        "answer": answer,
        "confidence": final_confidence,
        "evidence": evidence,
        "visual_outputs": visual_outputs,
    }


def _vlm_was_skipped(tool_results: dict[str, dict]) -> bool:
    """Prevent static preprocessing from masking an unavailable VLM."""
    vlm_names = {
        "geochat_vqa_caption_tool",
        "rsllava_vqa_caption_tool",
        "teochat_change_vqa_tool",
    }
    return any(
        name in vlm_names and result.get("status") == "skipped"
        for name, result in tool_results.items()
    )


# ── Evidence list ─────────────────────────────────────────


def _build_evidence_list(tool_results: dict[str, dict]) -> list[str]:
    """Build a human-readable list of evidence from tool summaries."""
    evidence = []
    for name, result in tool_results.items():
        status = result.get("status", "unknown")
        summary = result.get("summary", "")
        if status == "success" and summary:
            evidence.append(f"[{name}] {summary}")
        elif status == "skipped":
            reason = result.get("reason", result.get("outputs", {}).get("reason", ""))
            evidence.append(f"[{name}] Skipped: {reason}")
    return evidence


# ── Visual outputs ────────────────────────────────────────


def _collect_visual_outputs(tool_results: dict[str, dict]) -> list[dict]:
    """Collect all visual artifacts (overlays, masks, previews) from tool results."""
    visuals = []
    for name, result in tool_results.items():
        if result.get("status") != "success":
            continue
        for artifact in result.get("artifacts", []):
            atype = artifact.get("type", "")
            if atype in ("overlay", "mask", "preview"):
                visuals.append({
                    "type": atype,
                    "label": artifact.get("label", name),
                    "url": artifact.get("path", ""),
                })
    return visuals


# ── Answer synthesis ──────────────────────────────────────


def _synthesise_answer(
    query: str,
    tool_results: dict[str, dict],
    workflow: str,
    evidence: list[str],
    confidence: float,
) -> str:
    """Build a text answer from all available evidence."""

    parts = []

    # VLM answers (GeoChat, RS-LLaVA, TEOChat)
    for vlm_tool in ("geochat_vqa_caption_tool", "rsllava_vqa_caption_tool", "teochat_change_vqa_tool"):
        result = tool_results.get(vlm_tool, {})
        if result.get("status") == "success":
            answer = result.get("outputs", {}).get("answer", "")
            if answer:
                parts.append(answer)

    # Dual encoder / CROMA labels
    dual = tool_results.get("custom_sar_optical_dual_encoder_tool", {})
    if dual.get("status") == "success":
        labels = dual.get("outputs", {}).get("agreed_labels", [])
        if labels:
            parts.append(f"Land-cover classification: {', '.join(labels[:6])}.")
        similarity = dual.get("outputs", {}).get("similarity")
        if similarity is not None:
            parts.append(f"Cross-modal similarity: {similarity:.2f}.")

    # Spectral index summaries
    for tool_name in ("ndvi_vegetation_detector", "ndwi_water_detector", "mndwi_water_detector",
                       "ndbi_builtup_detector", "sar_water_detector", "sar_builtup_detector"):
        result = tool_results.get(tool_name, {})
        if result.get("status") == "success":
            cov = result.get("outputs", {}).get("coverage_percent")
            area = result.get("outputs", {}).get("area_sq_m")
            index_name = tool_name.replace("_detector", "").replace("_", " ").upper()
            if cov is not None:
                area_str = f", area ≈ {area:.0f} m²" if area else ""
                parts.append(f"{index_name}: {cov:.1f}% coverage{area_str}.")

    # Change map
    change = tool_results.get("change_map_generator", {})
    if change.get("status") == "success":
        cov = change.get("outputs", {}).get("coverage_percent")
        if cov is not None:
            parts.append(f"Change detection: {cov:.1f}% of the image shows significant change.")

    # Mask fusion
    fusion = tool_results.get("mask_fusion_tool", {})
    if fusion.get("status") == "success":
        cov = fusion.get("outputs", {}).get("coverage_percent")
        method = fusion.get("outputs", {}).get("method", "union")
        if cov is not None:
            parts.append(f"Fused evidence ({method}): {cov:.1f}% coverage.")

    # Area calculator
    area_result = tool_results.get("area_calculator", {})
    if area_result.get("status") == "success":
        area = area_result.get("outputs", {}).get("area_sq_m")
        area_km = area_result.get("outputs", {}).get("area_sq_km")
        if area:
            parts.append(f"Computed area: {area:.1f} m² ({area_km:.4f} km²).")

    # Build final answer
    if not parts:
        vlm_failures = [
            result.get("reason", "unavailable")
            for name, result in tool_results.items()
            if name in {"geochat_vqa_caption_tool", "rsllava_vqa_caption_tool", "teochat_change_vqa_tool"}
            and result.get("status") == "skipped"
        ]
        vlm_status = f"VLM inference was attempted but unavailable: {vlm_failures[0]}" if vlm_failures else "No VLM tool was selected."
        return (
            f"Analysis complete (workflow: {workflow}). "
            f"{vlm_status} Deterministic geospatial tools "
            f"produced evidence with {confidence:.0%} overall confidence. "
            f"See the visual outputs and tool trace for detailed results."
        )

    return " ".join(parts)
