"""Shared helper functions used by multiple static tools."""

from __future__ import annotations

from pathlib import Path

from backend.geospatial.dependencies import require_module


# ── Spectral index helpers ───────────────────────────────


def safe_normalized_index(band_a, band_b):
    """Compute (A - B) / (A + B) avoiding division by zero."""
    np = require_module("numpy", "numpy")
    denom = band_a + band_b
    return np.divide(
        band_a - band_b,
        denom,
        out=np.zeros_like(band_a, dtype="float32"),
        where=np.abs(denom) > 1e-6,
    )


# ── Mask / coverage helpers ──────────────────────────────


def coverage_percent(mask) -> float:
    np = require_module("numpy", "numpy")
    return round(float(np.asarray(mask).mean() * 100.0), 2)


def confidence_from_coverage(coverage: float) -> float:
    if coverage <= 0.0:
        return 0.35
    if coverage >= 80.0:
        return 0.6
    return round(min(0.9, 0.55 + coverage / 200.0), 2)


def mask_to_area_sq_m(mask, resolution: tuple[float, float] | None) -> float | None:
    """Convert a boolean mask to area in square metres using pixel resolution."""
    if resolution is None:
        return None
    np = require_module("numpy", "numpy")
    pixel_area = abs(resolution[0]) * abs(resolution[1])
    return round(float(np.asarray(mask).sum()) * pixel_area, 2)


# ── Otsu threshold ───────────────────────────────────────


def otsu_threshold(array) -> float:
    np = require_module("numpy", "numpy")
    values = np.asarray(array, dtype="float32")
    hist, bin_edges = np.histogram(values, bins=128)
    total = values.size
    sum_total = float((hist * bin_edges[:-1]).sum())
    weight_bg = 0.0
    sum_bg = 0.0
    max_var = -1.0
    threshold = float(values.mean())

    for idx, count in enumerate(hist):
        weight_bg += count
        if weight_bg == 0:
            continue
        weight_fg = total - weight_bg
        if weight_fg == 0:
            break
        sum_bg += float(count * bin_edges[idx])
        mean_bg = sum_bg / weight_bg
        mean_fg = (sum_total - sum_bg) / weight_fg
        var = weight_bg * weight_fg * (mean_bg - mean_fg) ** 2
        if var > max_var:
            max_var = var
            threshold = float(bin_edges[idx])
    return threshold


# ── Image I/O helpers ────────────────────────────────────


def write_mask_png(mask, output_path: str | Path) -> str:
    """Save a boolean mask as a uint8 PNG and return the path string."""
    np = require_module("numpy", "numpy")
    Image = require_module("PIL.Image", "Pillow")
    out = Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    mask_u8 = (np.asarray(mask).astype("uint8") * 255)
    Image.fromarray(mask_u8, mode="L").save(out)
    return str(out)


def write_overlay_png(
    mask,
    preview_path: str | Path,
    output_path: str | Path,
    color: tuple[int, int, int],
    *,
    alpha: int = 115,
) -> str:
    """Blend a coloured mask over a preview image and save as PNG."""
    np = require_module("numpy", "numpy")
    Image = require_module("PIL.Image", "Pillow")
    out = Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)

    preview = Image.open(preview_path).convert("RGBA")
    mask_u8 = (np.asarray(mask).astype("uint8") * 255)
    mask_image = Image.fromarray(mask_u8, mode="L").resize(preview.size)
    overlay = Image.new("RGBA", preview.size, (*color, 0))
    alpha_channel = mask_image.point(lambda v: alpha if v > 0 else 0)
    overlay.putalpha(alpha_channel)
    blended = Image.alpha_composite(preview, overlay)
    blended.save(out)
    return str(out)


def write_mask_and_overlay(
    run_dir: str | Path,
    mask,
    filename: str,
    label: str,
    color: tuple[int, int, int],
    *,
    preview_path: str | None = None,
) -> list[dict]:
    """Write mask + optional overlay, returning artifact dicts."""
    out_dir = Path(run_dir) / "tool_outputs"
    out_dir.mkdir(parents=True, exist_ok=True)
    mask_path = out_dir / filename

    artifacts = []
    saved = write_mask_png(mask, mask_path)
    artifacts.append({"type": "mask", "label": label, "path": saved})

    if preview_path:
        overlay_path = mask_path.with_name(mask_path.stem + "_overlay.png")
        saved_overlay = write_overlay_png(mask, preview_path, overlay_path, color)
        artifacts.append({"type": "overlay", "label": label, "path": saved_overlay})

    return artifacts


# ── Asset lookup helpers ─────────────────────────────────


def find_asset(manifest: dict, modality: str) -> dict | None:
    """Find the first asset matching a modality string."""
    return next(
        (
            asset
            for asset in manifest.get("assets", [])
            if asset.get("modality", {}).get("modality") == modality
        ),
        None,
    )


def get_preview_path(asset: dict | None) -> str | None:
    if asset is None:
        return None
    return asset.get("preview", {}).get("preview_path")


def get_model_input_path(asset: dict | None) -> str | None:
    if asset is None:
        return None
    mi = asset.get("model_input")
    if mi is None:
        return None
    return mi.get("model_input_path")


def get_band_order(asset: dict | None) -> list[str]:
    if asset is None:
        return []
    mi = asset.get("model_input")
    if mi is None:
        return []
    return mi.get("band_order", [])


def get_resolution(manifest: dict) -> tuple[float, float] | None:
    """Return pixel resolution from the first asset that has it."""
    for asset in manifest.get("assets", []):
        meta = asset.get("metadata", {})
        res = meta.get("resolution")
        if res and len(res) == 2:
            return (float(res[0]), float(res[1]))
    return None
