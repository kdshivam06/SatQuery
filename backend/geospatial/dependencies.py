"""Optional dependency loading helpers.

The prototype should import even on machines that have not installed GDAL,
rasterio, NumPy, or Pillow yet. Functions that actually need those packages
raise a clear setup error at the point of use.
"""

from __future__ import annotations

from importlib import import_module

from .raster_env import configure_rasterio_environment


class MissingDependencyError(RuntimeError):
    """Raised when an optional geospatial dependency is required but missing."""


def require_module(module_name: str, install_hint: str | None = None):
    """Import an optional module or raise a user-friendly error."""

    try:
        if module_name == "rasterio":
            configure_rasterio_environment()
        return import_module(module_name)
    except ImportError as exc:
        hint = install_hint or module_name
        raise MissingDependencyError(
            f"Optional dependency '{module_name}' is required for this operation. "
            f"Install it with: pip install {hint}"
        ) from exc
