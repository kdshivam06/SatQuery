"""Typed data objects shared by the ingestion pipeline."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any


class AssetFormat(str, Enum):
    PATCH_FOLDER = "patch_folder"
    GEOTIFF = "geotiff"
    TIFF = "tiff"
    PNG = "png"
    JPEG = "jpeg"
    UNKNOWN = "unknown"


class Modality(str, Enum):
    SAR = "sar"
    OPTICAL = "optical"
    MULTISPECTRAL = "multispectral"
    UNKNOWN = "unknown"


@dataclass(slots=True)
class RasterBounds:
    left: float
    bottom: float
    right: float
    top: float

    def as_tuple(self) -> tuple[float, float, float, float]:
        return (self.left, self.bottom, self.right, self.top)


@dataclass(slots=True)
class RasterTransform:
    values: tuple[float, float, float, float, float, float]


@dataclass(slots=True)
class BandInfo:
    index: int
    dtype: str | None = None
    description: str | None = None
    nodata: float | int | None = None


@dataclass(slots=True)
class AssetMetadata:
    path: str
    filename: str
    format: AssetFormat
    width: int | None = None
    height: int | None = None
    band_count: int | None = None
    dtypes: list[str] = field(default_factory=list)
    crs: str | None = None
    bounds: RasterBounds | None = None
    transform: RasterTransform | None = None
    resolution: tuple[float, float] | None = None
    nodata: float | int | None = None
    band_descriptions: list[str | None] = field(default_factory=list)
    bands: list[BandInfo] = field(default_factory=list)
    tags: dict[str, Any] = field(default_factory=dict)

    @property
    def has_geospatial_metadata(self) -> bool:
        return bool(self.crs and self.bounds and self.transform)

    @classmethod
    def from_path(cls, path: str | Path, asset_format: AssetFormat) -> "AssetMetadata":
        p = Path(path)
        return cls(path=str(p), filename=p.name, format=asset_format)

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["format"] = self.format.value
        return data


@dataclass(slots=True)
class ModalityDetection:
    modality: Modality
    confidence: float
    reasons: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "modality": self.modality.value,
            "confidence": self.confidence,
            "reasons": self.reasons,
        }


@dataclass(slots=True)
class AlignmentIssue:
    field: str
    severity: str
    message: str

    def to_dict(self) -> dict[str, str]:
        return asdict(self)


@dataclass(slots=True)
class AlignmentResult:
    compatible: bool
    score: float
    issues: list[AlignmentIssue] = field(default_factory=list)
    checked_fields: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "compatible": self.compatible,
            "score": self.score,
            "issues": [issue.to_dict() for issue in self.issues],
            "checked_fields": self.checked_fields,
        }


@dataclass(slots=True)
class PreviewResult:
    preview_path: str
    source_path: str
    width: int
    height: int
    selected_bands: list[int]
    normalization: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class ModelInputResult:
    model_input_path: str
    metadata_path: str
    source_path: str
    sensor: str
    model_version: str
    array_shape: tuple[int, ...]
    dtype: str
    band_order: list[str]
    normalization: dict[str, Any]
    resampling: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class IngestedAsset:
    metadata: AssetMetadata
    modality: ModalityDetection
    preview: PreviewResult | None = None
    model_input: ModelInputResult | None = None
    errors: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "metadata": self.metadata.to_dict(),
            "modality": self.modality.to_dict(),
            "preview": self.preview.to_dict() if self.preview else None,
            "model_input": self.model_input.to_dict() if self.model_input else None,
            "errors": self.errors,
        }
