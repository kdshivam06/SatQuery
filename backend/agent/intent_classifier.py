"""Rule-based intent classification for reliable prototype routing."""

from __future__ import annotations


def classify_intent(query: str, manifest: dict, mode: str = "auto") -> str:
    """Classify the user's query and input configuration into a workflow."""

    if mode and mode != "auto":
        mode_map = {
            "single": "single_image_vqa",
            "vqa": "single_image_vqa",
            "caption": "captioning",
            "captioning": "captioning",
            "grounding": "grounding",
            "mask": "grounding",
            "cross_modal": "cross_modal_analysis",
            "sar_optical": "cross_modal_analysis",
            "temporal": "change_analysis",
            "change": "change_analysis",
            "retrieval": "retrieval",
        }
        if mode in mode_map:
            return mode_map[mode]

    q = query.lower()
    assets = manifest.get("assets", [])
    modalities = [asset.get("modality", {}).get("modality") for asset in assets]
    has_pair = len(assets) >= 2
    has_sar_and_optical = "sar" in modalities and any(m in modalities for m in ("optical", "multispectral"))

    if any(term in q for term in ("change", "changed", "before", "after", "increase", "decrease", "temporal")):
        return "change_analysis"
    if any(term in q for term in ("highlight", "show", "segment", "mask", "locate", "where")):
        return "grounding"
    if any(term in q for term in ("retrieve", "similar", "match", "corresponding")):
        return "retrieval"
    if has_pair and has_sar_and_optical:
        return "cross_modal_analysis"
    if any(term in q for term in ("describe", "caption", "summarize", "land-cover", "land cover", "major objects")):
        return "captioning"
    return "single_image_vqa"
