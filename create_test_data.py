"""Generate synthetic SAR + Optical test data for SatQuery pipeline testing.

Creates a benv1-style patch pair with realistic band names.
Run: python create_test_data.py
"""

import numpy as np
from pathlib import Path

def create_test_patches():
    ROOT = Path("data/test_samples")
    
    # ── Sentinel-2 (multispectral) patch ──
    s2_dir = ROOT / "S2A_MSIL2A_TEST_PATCH"
    s2_dir.mkdir(parents=True, exist_ok=True)
    
    H, W = 120, 120
    s2_bands = {
        "B02": np.random.uniform(0.02, 0.15, (H, W)),   # Blue
        "B03": np.random.uniform(0.03, 0.18, (H, W)),   # Green
        "B04": np.random.uniform(0.02, 0.14, (H, W)),   # Red
        "B08": np.random.uniform(0.10, 0.50, (H, W)),   # NIR
        "B05": np.random.uniform(0.03, 0.20, (H, W)),   # Red Edge 1
        "B06": np.random.uniform(0.05, 0.30, (H, W)),   # Red Edge 2
        "B07": np.random.uniform(0.07, 0.40, (H, W)),   # Red Edge 3
        "B8A": np.random.uniform(0.10, 0.45, (H, W)),   # NIR narrow
        "B11": np.random.uniform(0.05, 0.35, (H, W)),   # SWIR 1
        "B12": np.random.uniform(0.03, 0.25, (H, W)),   # SWIR 2
    }
    
    # Add a water body (low NIR, high Green relative to NIR)
    water_mask = np.zeros((H, W), dtype=bool)
    water_mask[30:60, 40:80] = True
    for band_name, arr in s2_bands.items():
        if band_name == "B08":  # NIR drops in water
            arr[water_mask] *= 0.1
        elif band_name == "B03":  # Green stays moderate
            arr[water_mask] *= 0.8
    
    for band_name, arr in s2_bands.items():
        np.save(s2_dir / f"{s2_dir.name}_{band_name}.npy", arr.astype(np.float32))
    
    print(f"Created S2 patch: {s2_dir} ({len(s2_bands)} bands)")
    
    # ── Sentinel-1 (SAR) patch ──
    s1_dir = ROOT / "S1A_IW_GRDH_TEST_PATCH"
    s1_dir.mkdir(parents=True, exist_ok=True)
    
    s1_bands = {
        "VV": np.random.uniform(-25, -5, (H, W)),   # VV polarization (dB)
        "VH": np.random.uniform(-30, -10, (H, W)),  # VH polarization (dB)
    }
    
    # Water shows low backscatter in SAR
    for band_name, arr in s1_bands.items():
        arr[water_mask] = np.random.uniform(-28, -20, water_mask.sum())
    
    for band_name, arr in s1_bands.items():
        np.save(s1_dir / f"{s1_dir.name}_{band_name}.npy", arr.astype(np.float32))
    
    print(f"Created S1 patch: {s1_dir} ({len(s1_bands)} bands)")
    
    # ── Also create a simple GeoTIFF for upload testing ──
    try:
        from PIL import Image
        rgb = np.stack([
            (s2_bands["B04"] * 255 / 0.14).clip(0, 255),
            (s2_bands["B03"] * 255 / 0.18).clip(0, 255),
            (s2_bands["B02"] * 255 / 0.15).clip(0, 255),
        ]).astype(np.uint8)
        img = Image.fromarray(rgb.transpose(1, 2, 0), mode="RGB")
        tif_path = ROOT / "test_optical.tif"
        img.save(tif_path)
        print(f"Created test TIFF: {tif_path}")
    except ImportError:
        print("Pillow not installed — skipped TIFF creation")
    
    print(f"\nAll test data at: {ROOT.resolve()}")
    print(f"\nTo test via API:")
    print(f'  curl -X POST http://localhost:8000/api/analyze/paths \\')
    print(f'    -H "Content-Type: application/json" \\')
    print(f'    -d \'{{"query":"detect water bodies","paths":["{s1_dir}","{s2_dir}"]}}\'')

if __name__ == "__main__":
    create_test_patches()
