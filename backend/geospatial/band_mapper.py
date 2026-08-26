"""Band selection helpers for visual previews and pretrained model inputs."""

from __future__ import annotations

from .models import AssetMetadata, Modality


SENTINEL2_RGB_BY_INDEX = [4, 3, 2]
SENTINEL2_FALSE_COLOR_BY_INDEX = [8, 4, 3]

BIGEARTHNET_V2_S1_BANDS_V020 = ("VV", "VH")
BIGEARTHNET_V2_S2_BANDS_V020 = (
    "B02",
    "B03",
    "B04",
    "B05",
    "B06",
    "B07",
    "B08",
    "B8A",
    "B11",
    "B12",
)
BIGEARTHNET_V2_ALL_BANDS_V020 = BIGEARTHNET_V2_S1_BANDS_V020 + BIGEARTHNET_V2_S2_BANDS_V020

BIGEARTHNET_V2_S1_BANDS_V011 = ("VH", "VV")
BIGEARTHNET_V2_S2_BANDS_V011 = (
    "B02",
    "B03",
    "B04",
    "B08",
    "B05",
    "B06",
    "B07",
    "B11",
    "B12",
    "B8A",
)
BIGEARTHNET_V2_ALL_BANDS_V011 = BIGEARTHNET_V2_S2_BANDS_V011 + BIGEARTHNET_V2_S1_BANDS_V011


def select_preview_bands(metadata: AssetMetadata, modality: Modality | str) -> list[int]:
    """Choose 1-based band indexes for preview generation."""

    band_count = metadata.band_count or 0
    modality_value = modality.value if isinstance(modality, Modality) else modality

    if band_count <= 0:
        return []

    if modality_value == Modality.MULTISPECTRAL.value and band_count >= 8:
        return SENTINEL2_RGB_BY_INDEX

    if modality_value == Modality.SAR.value:
        return [1, 2, 1] if band_count >= 2 else [1]

    if band_count >= 3:
        return [1, 2, 3]

    return [1]


def get_bigearthnet_pretrained_band_order(
    sensor: str,
    *,
    model_version: str = "v0.2.0",
) -> tuple[str, ...]:
    """Return the official band order for BigEarthNet v2 pretrained weights."""

    normalized_sensor = sensor.lower().replace("+", "_").replace("-", "_")
    normalized_version = model_version.lower()

    if normalized_version == "v0.2.0":
        if normalized_sensor in {"s1", "sentinel_1", "sar"}:
            return BIGEARTHNET_V2_S1_BANDS_V020
        if normalized_sensor in {"s2", "sentinel_2", "optical", "multispectral"}:
            return BIGEARTHNET_V2_S2_BANDS_V020
        if normalized_sensor in {"all", "s1_s2", "s1_s2_all"}:
            return BIGEARTHNET_V2_ALL_BANDS_V020

    if normalized_version == "v0.1.1":
        if normalized_sensor in {"s1", "sentinel_1", "sar"}:
            return BIGEARTHNET_V2_S1_BANDS_V011
        if normalized_sensor in {"s2", "sentinel_2", "optical", "multispectral"}:
            return BIGEARTHNET_V2_S2_BANDS_V011
        if normalized_sensor in {"all", "s1_s2", "s1_s2_all"}:
            return BIGEARTHNET_V2_ALL_BANDS_V011

    raise ValueError(f"Unsupported BigEarthNet band order: sensor={sensor}, version={model_version}")


def plan_available_model_bands(
    metadata: AssetMetadata,
    required_band_order: tuple[str, ...],
) -> dict:
    """Map required model bands to available 1-based raster band indexes."""

    available = {
        _normalize_band_name(band.description): band.index
        for band in metadata.bands
        if band.description
    }
    missing: list[str] = []
    mapped: list[dict[str, int | str]] = []

    for band_name in required_band_order:
        normalized = _normalize_band_name(band_name)
        index = available.get(normalized)
        if index is None:
            missing.append(band_name)
        else:
            mapped.append({"band": band_name, "index": index})

    return {
        "required_order": list(required_band_order),
        "mapped": mapped,
        "missing": missing,
        "complete": not missing,
    }


def _normalize_band_name(value: str) -> str:
    text = value.upper().replace("_", " ").replace("-", " ")
    for token in text.split():
        if token in {"VV", "VH", "HH", "HV"}:
            return token
        if token.startswith("B") and token[1:].replace("A", "").isdigit():
            return token
    return text.strip()
