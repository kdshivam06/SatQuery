"""Ingestion helpers for BigEarthNet-style patch folders."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from .dependencies import require_module
from .image_normalizer import percentile_clip_normalize
from .models import AssetFormat, AssetMetadata, BandInfo, PreviewResult, RasterBounds, RasterTransform


KNOWN_BANDS = {
    "VV",
    "VH",
    "HH",
    "HV",
    "B01",
    "B02",
    "B03",
    "B04",
    "B05",
    "B06",
    "B07",
    "B08",
    "B8A",
    "B09",
    "B10",
    "B11",
    "B12",
}

S1_PREVIEW_ORDER = ("VV", "VH", "VV")
S2_RGB_PREVIEW_ORDER = ("B04", "B03", "B02")


def read_patch_folder_metadata(path: str | Path) -> AssetMetadata:
    """Read metadata for a folder containing one TIFF per satellite band."""

    rasterio = require_module("rasterio", "rasterio")
    p = Path(path)
    band_files = discover_band_files(p)
    if not band_files:
        raise FileNotFoundError(f"No band TIFF files found in patch folder: {p}")

    reference_band = _choose_reference_band(band_files)
    metadata = AssetMetadata.from_path(p, AssetFormat.PATCH_FOLDER)
    metadata.band_count = len(band_files)
    metadata.tags = {
        "PATCH_FOLDER": True,
        "band_files": {band: str(file_path) for band, file_path in band_files.items()},
    }
    metadata.tags.update(_read_patch_metadata_json(p))

    with rasterio.open(reference_band) as src:
        metadata.width = int(src.width)
        metadata.height = int(src.height)
        metadata.crs = src.crs.to_string() if src.crs else None
        metadata.bounds = RasterBounds(
            left=float(src.bounds.left),
            bottom=float(src.bounds.bottom),
            right=float(src.bounds.right),
            top=float(src.bounds.top),
        )
        metadata.transform = RasterTransform(tuple(float(v) for v in src.transform[:6]))
        metadata.resolution = (float(abs(src.res[0])), float(abs(src.res[1])))
        metadata.nodata = src.nodata

    ordered_band_names = order_band_names(band_files)
    dtypes: list[str] = []
    bands: list[BandInfo] = []
    for index, band_name in enumerate(ordered_band_names, start=1):
        with rasterio.open(band_files[band_name]) as src:
            dtype = str(src.dtypes[0])
            dtypes.append(dtype)
            bands.append(
                BandInfo(
                    index=index,
                    dtype=dtype,
                    description=band_name,
                    nodata=src.nodata,
                )
            )

    metadata.dtypes = dtypes
    metadata.band_descriptions = ordered_band_names
    metadata.bands = bands
    return metadata


def generate_patch_folder_preview(
    path: str | Path,
    output_path: str | Path,
    *,
    metadata: AssetMetadata | None = None,
    max_size: int = 1024,
) -> PreviewResult:
    """Generate a preview from a patch folder's real band TIFFs."""

    rasterio = require_module("rasterio", "rasterio")
    np = require_module("numpy", "numpy")
    Image = require_module("PIL.Image", "Pillow")

    p = Path(path)
    out = Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)

    band_files = discover_band_files(p)
    preview_band_names = _select_patch_preview_band_names(band_files)
    if not preview_band_names:
        raise ValueError(f"Could not select preview bands from patch folder: {p}")

    arrays = []
    selected_indexes = []
    ordered_names = order_band_names(band_files)
    for band_name in preview_band_names:
        with rasterio.open(band_files[band_name]) as src:
            arrays.append(percentile_clip_normalize(src.read(1), output_dtype="uint8", nodata=src.nodata))
            selected_indexes.append(ordered_names.index(band_name) + 1)

    if len(arrays) == 1:
        image_array = arrays[0]
        mode = "L"
    else:
        while len(arrays) < 3:
            arrays.append(arrays[-1])
        image_array = np.stack(arrays[:3], axis=-1)
        mode = "RGB"

    image = Image.fromarray(image_array, mode=mode)
    image.thumbnail((max_size, max_size))
    image.save(out, format="PNG")

    return PreviewResult(
        preview_path=str(out),
        source_path=str(p),
        width=image.width,
        height=image.height,
        selected_bands=selected_indexes,
        normalization={
            "method": "patch_folder_percentile_clip",
            "lower_percentile": 2.0,
            "upper_percentile": 98.0,
            "band_names": list(preview_band_names),
        },
    )


def discover_band_files(path: str | Path) -> dict[str, Path]:
    """Find single-band TIFF files and infer their band names from filenames."""

    p = Path(path)
    band_files: dict[str, Path] = {}
    for file_path in sorted(p.glob("*.tif")) + sorted(p.glob("*.tiff")):
        band_name = infer_band_name(file_path)
        if band_name:
            band_files[band_name] = file_path
    return band_files


def infer_band_name(path: str | Path) -> str | None:
    stem = Path(path).stem.upper()
    matches = re.findall(r"(?:^|_)(VV|VH|HH|HV|B0[1-9]|B10|B11|B12|B8A)(?:_|$)", stem)
    for match in reversed(matches):
        if match in KNOWN_BANDS:
            return match
    return None


def order_band_names(band_files: dict[str, Path]) -> list[str]:
    preferred = [
        "VV",
        "VH",
        "B01",
        "B02",
        "B03",
        "B04",
        "B05",
        "B06",
        "B07",
        "B08",
        "B8A",
        "B09",
        "B10",
        "B11",
        "B12",
    ]
    return [band for band in preferred if band in band_files] + sorted(
        band for band in band_files if band not in preferred
    )


def _choose_reference_band(band_files: dict[str, Path]) -> Path:
    for band_name in ("B02", "B03", "B04", "B08", "VV", "VH"):
        if band_name in band_files:
            return band_files[band_name]
    return next(iter(band_files.values()))


def _select_patch_preview_band_names(band_files: dict[str, Path]) -> tuple[str, ...]:
    if all(band in band_files for band in S2_RGB_PREVIEW_ORDER):
        return S2_RGB_PREVIEW_ORDER
    if all(band in band_files for band in ("VV", "VH")):
        return S1_PREVIEW_ORDER
    if "VV" in band_files:
        return ("VV",)
    if "VH" in band_files:
        return ("VH",)
    ordered = order_band_names(band_files)
    return tuple(ordered[:3])


def _read_patch_metadata_json(path: Path) -> dict[str, Any]:
    metadata_files = sorted(path.glob("*labels_metadata.json"))
    if not metadata_files:
        return {}
    try:
        return {"labels_metadata": json.loads(metadata_files[0].read_text(encoding="utf-8"))}
    except json.JSONDecodeError:
        return {"labels_metadata_error": f"Could not parse {metadata_files[0].name}"}
