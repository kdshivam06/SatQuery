"""Fuse tool outputs into the user-visible final response."""

from __future__ import annotations


def fuse_outputs(query: str, intent: str, manifest: dict, plan: dict, results: dict[str, dict]) -> dict:
    """Create final answer, confidence, evidence, visual outputs, and trace."""

    successful = [result for result in results.values() if result.get("status") == "success"]
    confidences = [
        float(result["confidence"])
        for result in successful
        if result.get("confidence") is not None
    ]
    confidence = round(sum(confidences) / len(confidences), 2) if confidences else 0.5
    evidence = [result.get("summary", "") for result in successful if result.get("summary")]
    visual_outputs = _collect_visual_outputs(results)

    answer = _answer_for_intent(query, intent, manifest, results, confidence)
    return {
        "answer": answer,
        "confidence": confidence,
        "evidence": evidence,
        "visual_outputs": visual_outputs,
        "trace": {
            "workflow": intent,
            "parallel_groups": plan.get("parallel_groups", []),
            "selected_tools": [
                {
                    "name": result.get("tool_name"),
                    "status": result.get("status"),
                    "runtime_ms": result.get("runtime_ms"),
                    "confidence": result.get("confidence"),
                    "summary": result.get("summary"),
                }
                for result in results.values()
            ],
        },
    }


def _answer_for_intent(query: str, intent: str, manifest: dict, results: dict[str, dict], confidence: float) -> str:
    labels = _labels_from_manifest(manifest)

    if intent == "cross_modal_analysis":
        water = _mask_area(results, "ndwi_water") or _mask_area(results, "sar_water")
        built = _mask_area(results, "ndbi_builtup") or _mask_area(results, "sar_builtup")
        return (
            "The SAR and multispectral inputs are spatially compatible, so the system used both modalities. "
            f"Detected label context: {', '.join(labels) if labels else 'not available'}. "
            f"Water evidence covers about {water:.2f}% of the patch and built-up evidence about {built:.2f}%."
        )

    if intent == "grounding":
        water = _mask_area(results, "ndwi_water") or _mask_area(results, "sar_water")
        return f"The likely water/target region has been converted into a visual mask. Estimated mask coverage is {water:.2f}% of the patch."

    if intent == "change_analysis":
        changed = _mask_area(results, "change_map")
        return f"The bi-temporal change workflow generated a spatial change mask. Estimated changed area is {changed:.2f}% of the compared patch area."

    if intent == "retrieval":
        return "The retrieval workflow prepared the uploaded scene for SAR/optical matching and ranked-match integration."

    if labels:
        return f"This remote-sensing scene is associated with: {', '.join(labels)}. The answer was produced through the RS model wrapper and metadata evidence."
    return f"The scene was processed successfully for query: {query}. Confidence: {confidence:.2f}."


def _labels_from_manifest(manifest: dict) -> list[str]:
    labels: list[str] = []
    for asset in manifest.get("assets", []):
        labels_metadata = asset.get("metadata", {}).get("tags", {}).get("labels_metadata", {})
        for label in labels_metadata.get("labels", []):
            if label not in labels:
                labels.append(label)
    return labels


def _mask_area(results: dict[str, dict], step_id: str) -> float:
    output = results.get(step_id, {}).get("outputs", {})
    return float(output.get("coverage_percent") or 0.0)


def _collect_visual_outputs(results: dict[str, dict]) -> list[dict]:
    outputs: list[dict] = []
    for result in results.values():
        for artifact in result.get("artifacts", []):
            if artifact.get("type") in {"mask", "overlay", "preview"}:
                outputs.append(artifact)
    return outputs
