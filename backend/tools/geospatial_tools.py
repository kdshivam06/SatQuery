"""Deterministic geospatial tools for Member 4."""

from __future__ import annotations

from pathlib import Path

from backend.geospatial.dependencies import require_module


class MetadataSummaryTool:
    name = "metadata_summary"
    description = "Summarizes modalities, geospatial metadata, previews, and alignment."
    resource = "cpu"

    async def run(self, context: dict, params: dict, prior_results: dict) -> dict:
        manifest = context["manifest"]
        assets = manifest.get("assets", [])
        modalities = [asset.get("modality", {}).get("modality") for asset in assets]
        alignment = manifest.get("alignment")
        summary = f"Read {len(assets)} asset(s): {', '.join(modalities)}."
        if alignment:
            summary += f" Pair alignment compatible={alignment.get('compatible')} score={alignment.get('score')}."
        return {
            "status": "success",
            "outputs": {
                "asset_count": len(assets),
                "modalities": modalities,
                "alignment": alignment,
            },
            "confidence": 0.95 if assets else 0.2,
            "summary": summary,
            "artifacts": _preview_artifacts(manifest),
        }


class PairCompatibilityTool:
    name = "pair_compatibility"
    description = "Reports CRS/pixel-grid compatibility for paired analysis."
    resource = "cpu"

    async def run(self, context: dict, params: dict, prior_results: dict) -> dict:
        alignment = context["manifest"].get("alignment")
        if not alignment:
            return {
                "status": "skipped",
                "outputs": {"reason": "No pair alignment result available."},
                "confidence": 0.0,
                "summary": "Pair compatibility skipped because fewer than two assets were provided.",
                "artifacts": [],
            }
        compatible = bool(alignment.get("compatible"))
        score = float(alignment.get("score") or 0.0)
        return {
            "status": "success",
            "outputs": alignment,
            "confidence": score,
            "summary": f"Pair compatibility score is {score:.2f}; compatible={compatible}.",
            "artifacts": [],
        }


class SpectralIndexTool:
    """Compute NDVI/NDWI/NDBI from the S2 model stack."""

    resource = "cpu"

    def __init__(self, name: str, numerator: tuple[str, str], threshold: float, label: str, color: tuple[int, int, int]):
        self.name = name
        self.description = f"Computes {name} mask from Sentinel-2 bands."
        self.numerator = numerator
        self.threshold = threshold
        self.label = label
        self.color = color

    async def run(self, context: dict, params: dict, prior_results: dict) -> dict:
        s2_asset = _find_asset(context["manifest"], "multispectral")
        if not s2_asset or not s2_asset.get("model_input"):
            return _skipped(self.name, "No multispectral model input is available.")

        np = require_module("numpy", "numpy")
        model_input = s2_asset["model_input"]
        band_order = model_input["band_order"]
        missing = [band for band in self.numerator if band not in band_order]
        if missing:
            return _skipped(self.name, f"Missing required bands: {missing}")

        arr = np.load(model_input["model_input_path"])
        band_a = arr[band_order.index(self.numerator[0])]
        band_b = arr[band_order.index(self.numerator[1])]
        index = _safe_index(band_a, band_b)
        mask = index > self.threshold

        paths = _write_mask_and_overlay(
            context,
            mask,
            f"{self.name}.png",
            self.label,
            self.color,
            preview_path=s2_asset.get("preview", {}).get("preview_path"),
        )
        coverage = _coverage_percent(mask)
        return {
            "status": "success",
            "outputs": {
                "index": self.name,
                "formula": f"({self.numerator[0]} - {self.numerator[1]}) / ({self.numerator[0]} + {self.numerator[1]})",
                "threshold": self.threshold,
                "coverage_percent": coverage,
            },
            "confidence": _confidence_from_coverage(coverage),
            "summary": f"{self.label} mask covers about {coverage:.2f}% of the patch.",
            "artifacts": paths,
        }


class SarWaterTool:
    name = "sar_water"
    description = "Detects low-backscatter water-like regions from Sentinel-1 VV/VH."
    resource = "cpu"

    async def run(self, context: dict, params: dict, prior_results: dict) -> dict:
        s1_asset = _find_asset(context["manifest"], "sar")
        if not s1_asset or not s1_asset.get("model_input"):
            return _skipped(self.name, "No SAR model input is available.")

        np = require_module("numpy", "numpy")
        arr = np.load(s1_asset["model_input"]["model_input_path"])
        score = arr.mean(axis=0)
        threshold = _otsu_threshold(score)
        mask = score < threshold
        coverage = _coverage_percent(mask)
        artifacts = _write_mask_and_overlay(
            context,
            mask,
            f"{self.name}.png",
            "SAR water/flood evidence",
            (0, 120, 255),
            preview_path=s1_asset.get("preview", {}).get("preview_path"),
        )
        return {
            "status": "success",
            "outputs": {"threshold": float(threshold), "coverage_percent": coverage},
            "confidence": _confidence_from_coverage(coverage),
            "summary": f"SAR low-backscatter water evidence covers about {coverage:.2f}% of the patch.",
            "artifacts": artifacts,
        }


class SarBuiltupTool:
    name = "sar_builtup"
    description = "Detects high-backscatter built-up/metallic evidence from Sentinel-1 VV/VH."
    resource = "cpu"

    async def run(self, context: dict, params: dict, prior_results: dict) -> dict:
        s1_asset = _find_asset(context["manifest"], "sar")
        if not s1_asset or not s1_asset.get("model_input"):
            return _skipped(self.name, "No SAR model input is available.")

        np = require_module("numpy", "numpy")
        arr = np.load(s1_asset["model_input"]["model_input_path"])
        score = arr.mean(axis=0)
        threshold = float(np.percentile(score, 85))
        mask = score > threshold
        coverage = _coverage_percent(mask)
        artifacts = _write_mask_and_overlay(
            context,
            mask,
            f"{self.name}.png",
            "SAR built-up evidence",
            (255, 190, 0),
            preview_path=s1_asset.get("preview", {}).get("preview_path"),
        )
        return {
            "status": "success",
            "outputs": {"threshold": threshold, "coverage_percent": coverage},
            "confidence": _confidence_from_coverage(coverage),
            "summary": f"SAR high-backscatter built-up evidence covers about {coverage:.2f}% of the patch.",
            "artifacts": artifacts,
        }


class ChangeMapTool:
    name = "change_map"
    description = "Generates a simple pixel-difference change mask from two previews."
    resource = "cpu"

    async def run(self, context: dict, params: dict, prior_results: dict) -> dict:
        previews = [
            asset.get("preview", {}).get("preview_path")
            for asset in context["manifest"].get("assets", [])
            if asset.get("preview")
        ]
        if len(previews) < 2:
            return _skipped(self.name, "At least two previews are required for change detection.")

        np = require_module("numpy", "numpy")
        Image = require_module("PIL.Image", "Pillow")
        a = Image.open(previews[0]).convert("L")
        b = Image.open(previews[1]).convert("L").resize(a.size)
        diff = np.abs(np.asarray(a, dtype="float32") - np.asarray(b, dtype="float32"))
        threshold = float(diff.mean() + diff.std())
        mask = diff > threshold
        coverage = _coverage_percent(mask)
        artifacts = _write_mask_and_overlay(
            context,
            mask,
            "change_map.png",
            "Change evidence",
            (255, 40, 80),
            preview_path=previews[1],
        )
        return {
            "status": "success",
            "outputs": {"threshold": threshold, "coverage_percent": coverage},
            "confidence": _confidence_from_coverage(coverage),
            "summary": f"Pixel-difference change evidence covers about {coverage:.2f}% of the compared patch.",
            "artifacts": artifacts,
        }


def _preview_artifacts(manifest: dict) -> list[dict]:
    artifacts = []
    for asset in manifest.get("assets", []):
        preview = asset.get("preview")
        if preview:
            artifacts.append(
                {
                    "type": "preview",
                    "label": asset.get("metadata", {}).get("filename", "preview"),
                    "path": preview["preview_path"],
                }
            )
    return artifacts


def _find_asset(manifest: dict, modality: str) -> dict | None:
    return next(
        (
            asset
            for asset in manifest.get("assets", [])
            if asset.get("modality", {}).get("modality") == modality
        ),
        None,
    )


def _safe_index(a, b):
    np = require_module("numpy", "numpy")
    denom = a + b
    return np.divide(a - b, denom, out=np.zeros_like(a, dtype="float32"), where=np.abs(denom) > 1e-6)


def _coverage_percent(mask) -> float:
    np = require_module("numpy", "numpy")
    return round(float(np.asarray(mask).mean() * 100.0), 2)


def _confidence_from_coverage(coverage: float) -> float:
    if coverage <= 0.0:
        return 0.35
    if coverage >= 80.0:
        return 0.6
    return round(min(0.9, 0.55 + coverage / 200.0), 2)


def _otsu_threshold(array) -> float:
    np = require_module("numpy", "numpy")
    values = np.asarray(array, dtype="float32")
    hist, bin_edges = np.histogram(values, bins=128)
    total = values.size
    sum_total = float((hist * bin_edges[:-1]).sum())
    weight_background = 0.0
    sum_background = 0.0
    max_variance = -1.0
    threshold = float(values.mean())

    for idx, count in enumerate(hist):
        weight_background += count
        if weight_background == 0:
            continue
        weight_foreground = total - weight_background
        if weight_foreground == 0:
            break
        sum_background += float(count * bin_edges[idx])
        mean_background = sum_background / weight_background
        mean_foreground = (sum_total - sum_background) / weight_foreground
        variance = weight_background * weight_foreground * (mean_background - mean_foreground) ** 2
        if variance > max_variance:
            max_variance = variance
            threshold = float(bin_edges[idx])
    return threshold


def _write_mask_and_overlay(
    context: dict,
    mask,
    filename: str,
    label: str,
    color: tuple[int, int, int],
    *,
    preview_path: str | None,
) -> list[dict]:
    np = require_module("numpy", "numpy")
    Image = require_module("PIL.Image", "Pillow")

    out_dir = Path(context["run_dir"]) / "tool_outputs"
    out_dir.mkdir(parents=True, exist_ok=True)
    mask_path = out_dir / filename
    mask_u8 = (np.asarray(mask).astype("uint8") * 255)
    Image.fromarray(mask_u8, mode="L").save(mask_path)

    artifacts = [{"type": "mask", "label": label, "path": str(mask_path)}]
    if preview_path:
        preview = Image.open(preview_path).convert("RGBA")
        mask_image = Image.fromarray(mask_u8, mode="L").resize(preview.size)
        overlay = Image.new("RGBA", preview.size, (*color, 0))
        alpha = mask_image.point(lambda value: 115 if value > 0 else 0)
        overlay.putalpha(alpha)
        blended = Image.alpha_composite(preview, overlay)
        overlay_path = mask_path.with_name(mask_path.stem + "_overlay.png")
        blended.save(overlay_path)
        artifacts.append({"type": "overlay", "label": label, "path": str(overlay_path)})
    return artifacts


def _skipped(tool_name: str, reason: str) -> dict:
    return {
        "status": "skipped",
        "outputs": {"reason": reason},
        "confidence": 0.0,
        "summary": f"{tool_name} skipped: {reason}",
        "artifacts": [],
    }
