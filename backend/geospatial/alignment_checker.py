"""CRS and pixel-grid compatibility checks for paired inputs."""

from __future__ import annotations

from math import isclose

from .models import AlignmentIssue, AlignmentResult, AssetMetadata


def check_alignment(
    asset_a: AssetMetadata,
    asset_b: AssetMetadata,
    *,
    bounds_tolerance: float = 1e-6,
    resolution_tolerance: float = 1e-6,
    transform_tolerance: float = 1e-6,
) -> AlignmentResult:
    """Check whether two assets are spatially compatible.

    The result is intentionally strict for prototype routing. If either file is
    missing CRS metadata, the pair is considered not safely co-registered.
    """

    issues: list[AlignmentIssue] = []
    checked_fields: list[str] = []

    checked_fields.append("crs")
    if not asset_a.crs or not asset_b.crs:
        issues.append(
            AlignmentIssue(
                "crs",
                "error",
                "One or both assets are missing CRS metadata.",
            )
        )
    elif asset_a.crs != asset_b.crs:
        issues.append(
            AlignmentIssue(
                "crs",
                "error",
                f"CRS mismatch: {asset_a.crs} != {asset_b.crs}.",
            )
        )

    checked_fields.append("dimensions")
    if asset_a.width != asset_b.width or asset_a.height != asset_b.height:
        issues.append(
            AlignmentIssue(
                "dimensions",
                "error",
                f"Dimension mismatch: {asset_a.width}x{asset_a.height} != "
                f"{asset_b.width}x{asset_b.height}.",
            )
        )

    checked_fields.append("resolution")
    if asset_a.resolution and asset_b.resolution:
        if not _tuple_close(asset_a.resolution, asset_b.resolution, resolution_tolerance):
            issues.append(
                AlignmentIssue(
                    "resolution",
                    "warning",
                    f"Resolution mismatch: {asset_a.resolution} != {asset_b.resolution}.",
                )
            )
    else:
        issues.append(
            AlignmentIssue(
                "resolution",
                "warning",
                "One or both assets are missing pixel resolution metadata.",
            )
        )

    checked_fields.append("bounds")
    if asset_a.bounds and asset_b.bounds:
        if not _tuple_close(asset_a.bounds.as_tuple(), asset_b.bounds.as_tuple(), bounds_tolerance):
            issues.append(
                AlignmentIssue(
                    "bounds",
                    "warning",
                    f"Bounds mismatch: {asset_a.bounds.as_tuple()} != {asset_b.bounds.as_tuple()}.",
                )
            )
    else:
        issues.append(
            AlignmentIssue(
                "bounds",
                "warning",
                "One or both assets are missing geospatial bounds.",
            )
        )

    checked_fields.append("transform")
    if asset_a.transform and asset_b.transform:
        if not _tuple_close(asset_a.transform.values, asset_b.transform.values, transform_tolerance):
            issues.append(
                AlignmentIssue(
                    "transform",
                    "warning",
                    "Affine transform mismatch; pixel grids may not align exactly.",
                )
            )
    else:
        issues.append(
            AlignmentIssue(
                "transform",
                "warning",
                "One or both assets are missing affine transform metadata.",
            )
        )

    score = _alignment_score(issues)
    compatible = score >= 0.8 and not any(issue.severity == "error" for issue in issues)
    return AlignmentResult(
        compatible=compatible,
        score=score,
        issues=issues,
        checked_fields=checked_fields,
    )


def _tuple_close(left: tuple[float, ...], right: tuple[float, ...], tolerance: float) -> bool:
    return len(left) == len(right) and all(
        isclose(a, b, rel_tol=0.0, abs_tol=tolerance) for a, b in zip(left, right)
    )


def _alignment_score(issues: list[AlignmentIssue]) -> float:
    score = 1.0
    for issue in issues:
        if issue.severity == "error":
            score -= 0.35
        elif issue.severity == "warning":
            score -= 0.12
    return round(max(0.0, score), 2)
