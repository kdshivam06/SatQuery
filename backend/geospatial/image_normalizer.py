"""Percentile-based normalization for model tensors and visual previews."""

from __future__ import annotations

from typing import Any

from .dependencies import require_module


def percentile_clip_normalize(
    array: Any,
    *,
    lower_percentile: float = 2.0,
    upper_percentile: float = 98.0,
    output_dtype: str = "uint8",
    nodata: float | int | None = None,
):
    """Clip an array by percentile and scale it to uint8 or float32.

    This is the Member 2 core normalization rule: raw 16-bit rasters are clipped
    to their 2nd and 98th percentiles, then converted into preview/model ranges.
    """

    np = require_module("numpy", "numpy")
    arr = np.asarray(array).astype("float32")
    valid_mask = np.isfinite(arr)
    if nodata is not None:
        valid_mask &= arr != float(nodata)

    valid = arr[valid_mask]
    if valid.size == 0:
        return np.zeros_like(arr, dtype=output_dtype)

    low = float(np.percentile(valid, lower_percentile))
    high = float(np.percentile(valid, upper_percentile))
    if high <= low:
        scaled = np.zeros_like(arr, dtype="float32")
    else:
        scaled = (np.clip(arr, low, high) - low) / (high - low)
        scaled = np.where(valid_mask, scaled, 0.0)

    if output_dtype == "float32":
        return scaled.astype("float32")
    if output_dtype == "uint8":
        return (scaled * 255.0).round().astype("uint8")
    raise ValueError(f"Unsupported output dtype: {output_dtype}")


def normalize_raster_bands(
    path: str,
    band_indexes: list[int],
    *,
    output_dtype: str = "float32",
):
    """Read selected raster bands and normalize each band independently."""

    rasterio = require_module("rasterio", "rasterio")
    np = require_module("numpy", "numpy")

    with rasterio.open(path) as src:
        bands = [
            percentile_clip_normalize(src.read(index), output_dtype=output_dtype, nodata=src.nodata)
            for index in band_indexes
        ]

    return np.stack(bands, axis=0)
