"""Rasterio/GDAL environment isolation for Windows-heavy GIS setups."""

from __future__ import annotations

import importlib.util
import os
from pathlib import Path


def configure_rasterio_environment() -> None:
    """Prefer rasterio's bundled PROJ data over unrelated global GIS installs."""

    spec = importlib.util.find_spec("rasterio")
    if not spec or not spec.origin:
        return

    rasterio_dir = Path(spec.origin).parent
    proj_dir = rasterio_dir / "proj_data"
    gdal_dir = rasterio_dir / "gdal_data"

    if proj_dir.exists():
        os.environ["PROJ_LIB"] = str(proj_dir)
        os.environ["PROJ_DATA"] = str(proj_dir)

    if gdal_dir.exists():
        os.environ["GDAL_DATA"] = str(gdal_dir)
