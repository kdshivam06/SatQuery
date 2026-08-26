"""Heuristic modality detection for remote-sensing assets."""

from __future__ import annotations

from .models import AssetMetadata, Modality, ModalityDetection


SAR_HINTS = {
    "sar",
    "sentinel-1",
    "sentinel1",
    "s1",
    "risat",
    "vv",
    "vh",
    "hh",
    "hv",
    "sigma0",
    "backscatter",
}

S2_HINTS = {
    "sentinel-2",
    "sentinel2",
    "s2",
    "multispectral",
    "msi",
    "b01",
    "b02",
    "b03",
    "b04",
    "b08",
    "nir",
    "swir",
}

OPTICAL_HINTS = {
    "optical",
    "rgb",
    "cartosat",
    "planet",
    "landsat",
    "aerial",
}


def detect_modality(metadata: AssetMetadata) -> ModalityDetection:
    """Return a best-effort modality label with confidence and reasons."""

    text = _searchable_text(metadata)
    reasons: list[str] = []

    sar_hits = sorted(hint for hint in SAR_HINTS if hint in text)
    s2_hits = sorted(hint for hint in S2_HINTS if hint in text)
    optical_hits = sorted(hint for hint in OPTICAL_HINTS if hint in text)

    if sar_hits:
        reasons.append(f"SAR keywords found: {', '.join(sar_hits[:5])}")
        return ModalityDetection(Modality.SAR, min(0.95, 0.65 + 0.05 * len(sar_hits)), reasons)

    if s2_hits:
        reasons.append(f"Sentinel-2 or multispectral keywords found: {', '.join(s2_hits[:5])}")
        return ModalityDetection(
            Modality.MULTISPECTRAL,
            min(0.95, 0.65 + 0.04 * len(s2_hits)),
            reasons,
        )

    if metadata.band_count is not None:
        if metadata.band_count >= 4:
            reasons.append(f"{metadata.band_count} bands suggests multispectral imagery")
            return ModalityDetection(Modality.MULTISPECTRAL, 0.72, reasons)

        if metadata.band_count in {1, 2}:
            reasons.append(f"{metadata.band_count} band(s) can indicate SAR or grayscale optical")
            return ModalityDetection(Modality.UNKNOWN, 0.45, reasons)

        if metadata.band_count == 3:
            reasons.append("Three bands suggests RGB optical imagery")
            return ModalityDetection(Modality.OPTICAL, 0.7, reasons)

    if optical_hits:
        reasons.append(f"Optical keywords found: {', '.join(optical_hits[:5])}")
        return ModalityDetection(Modality.OPTICAL, 0.65, reasons)

    reasons.append("No reliable modality signal found")
    return ModalityDetection(Modality.UNKNOWN, 0.25, reasons)


def _searchable_text(metadata: AssetMetadata) -> str:
    fields = [
        metadata.filename,
        " ".join(desc or "" for desc in metadata.band_descriptions),
        " ".join(f"{key} {value}" for key, value in metadata.tags.items()),
    ]
    return " ".join(fields).replace("_", "-").lower()
