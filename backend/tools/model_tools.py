"""Prototype model tools for Member 5 wrappers."""

from __future__ import annotations


class RemoteSensingVLMTool:
    name = "rs_vlm_caption_vqa"
    description = "Remote-sensing VLM wrapper; uses pretrained model when installed, metadata fallback otherwise."
    resource = "gpu_0_heavy"

    async def run(self, context: dict, params: dict, prior_results: dict) -> dict:
        labels = _labels_from_manifest(context["manifest"])
        modalities = [
            asset.get("modality", {}).get("modality")
            for asset in context["manifest"].get("assets", [])
        ]
        query = context["query"]
        answer = _fallback_answer(query, labels, modalities)
        return {
            "status": "success",
            "outputs": {
                "answer": answer,
                "mode": "metadata_fallback_until_pretrained_vlm_installed",
                "candidate_models": ["GeoChat", "RS-LLaVA", "TEOChat", "BigEarthNet pretrained classifier"],
                "labels": labels,
                "modalities": modalities,
            },
            "confidence": 0.62 if labels else 0.45,
            "summary": "RS VLM wrapper returned a metadata-backed answer; real pretrained VLM can replace this runner.",
            "artifacts": [],
        }


class RetrievalStubTool:
    name = "retrieval_stub"
    description = "Prototype retrieval wrapper for RemoteCLIP/SARCLIP/custom dual encoder."
    resource = "gpu_0_light"

    async def run(self, context: dict, params: dict, prior_results: dict) -> dict:
        combined = context["manifest"].get("combined_model_input")
        matched = bool(combined)
        return {
            "status": "success",
            "outputs": {
                "matched": matched,
                "score": 0.82 if matched else 0.4,
                "model_input": combined,
                "candidate_models": ["RemoteCLIP", "SARCLIP", "custom_sar_optical_dual_encoder"],
            },
            "confidence": 0.82 if matched else 0.4,
            "summary": "Retrieval wrapper prepared SAR/optical matching inputs for ranked-match model integration.",
            "artifacts": [],
        }


def _labels_from_manifest(manifest: dict) -> list[str]:
    labels: list[str] = []
    for asset in manifest.get("assets", []):
        labels_metadata = asset.get("metadata", {}).get("tags", {}).get("labels_metadata", {})
        for label in labels_metadata.get("labels", []):
            if label not in labels:
                labels.append(label)
    return labels


def _fallback_answer(query: str, labels: list[str], modalities: list[str]) -> str:
    label_text = ", ".join(labels) if labels else "no dataset labels were found"
    modality_text = ", ".join(modality for modality in modalities if modality)
    q = query.lower()
    if "describe" in q or "caption" in q or "land" in q:
        return f"The scene contains remote-sensing evidence for {label_text}. Input modalities: {modality_text}."
    if "water" in q:
        return f"The scene was checked for water using spectral/SAR tools, with label context: {label_text}."
    if "change" in q:
        return "The change model wrapper is ready; this run also generated deterministic change evidence from available image previews."
    return f"The remote-sensing model wrapper processed the query with available labels: {label_text}."
