# SatQuery AI

This repository currently contains the Member 2 geospatial ingestion slice for
the SatQuery AI prototype.

## Member 2 Scope

- Read GeoTIFF/TIFF metadata with CRS, transform, bounds, resolution, bands, and nodata.
- Read PNG/JPEG benchmark images as non-georeferenced assets.
- Detect likely modality: SAR, optical, multispectral, or unknown.
- Normalize raster bands with 2%-98% percentile clipping.
- Generate PNG previews for the frontend.
- Check CRS, bounds, resolution, dimensions, and affine transform alignment for paired inputs.
- Export metadata JSON, ingestion manifests, optional PDF reports, and GeoTIFF copies.

## Setup

```powershell
pip install -r requirements.txt
```

`rasterio` is required for GeoTIFF/TIFF reading. `numpy` and `Pillow` are
required for normalization and preview/PDF export.

Recommended local setup:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

## Data

Start small:

```powershell
.\.venv\Scripts\python.exe scripts\download_datasets.py --preset prototype-small
```

This downloads BigEarthNet.txt annotations plus VRSBench evaluation JSON files.
It does not download the full BigEarthNet imagery archives. Those are roughly
59 GiB for Sentinel-2 and 51 GiB for Sentinel-1, so fetch them only when the
team is ready for full training or evaluation.

## CLI

```powershell
python -m backend.geospatial.cli data\S1_patch.tif data\S2_patch.tif --output-dir runs\demo --pdf
```

For metadata and alignment only:

```powershell
python -m backend.geospatial.cli data\S1_patch.tif data\S2_patch.tif --output-dir runs\demo --no-previews
```

The main output is `runs\demo\ingestion_manifest.json`, which the FastAPI
controller can pass to the agentic router.

For a real `benv1_14k` pair, select and ingest by CSV row:

```powershell
.\.venv\Scripts\python.exe scripts\select_benv1_pair.py --index 0 --ingest --pdf --output-dir runs\benv1_pair_0
```

Or select by Sentinel-2 patch ID:

```powershell
.\.venv\Scripts\python.exe scripts\select_benv1_pair.py `
  --s2-id S2A_MSIL2A_20170803T094031_58_90 `
  --ingest `
  --output-dir runs\benv1_pair_58_90
```

## Member 2 Handoff Contract

Member 2 gives the backend one manifest per upload/run:

```text
runs\<run_id>\ingestion_manifest.json
```

That manifest contains:

- asset metadata: width, height, CRS, transform, bounds, resolution, bands, dtype, nodata
- detected modality: `sar`, `optical`, `multispectral`, or `unknown`
- preview paths for the frontend
- pair alignment result when two files are uploaded
- model-ready `.npy` paths for Member 5/6 model wrappers
- any ingestion errors

Real `benv1_14k` sample command:

```powershell
.\.venv\Scripts\python.exe -m backend.geospatial.cli `
  data\raw\real_samples\benv1_14k\s1\S1A_IW_GRDH_1SDV_20170802T163325_34TCR_58_90 `
  data\raw\real_samples\benv1_14k\s2\S2A_MSIL2A_20170803T094031_58_90 `
  --output-dir runs\real_benv1_14k_sample `
  --pdf
```

Expected outputs:

```text
runs\real_benv1_14k_sample\ingestion_manifest.json
runs\real_benv1_14k_sample\metadata\*.json
runs\real_benv1_14k_sample\model_inputs\*.npy
runs\real_benv1_14k_sample\model_inputs\*.json
runs\real_benv1_14k_sample\previews\*.png
runs\real_benv1_14k_sample\reports\ingestion_report.pdf
```

To validate with real data, provide any small pair of co-registered GeoTIFFs:

- Sentinel-1 SAR: VV/VH bands
- Sentinel-2 or optical/multispectral: RGB/NIR bands
- Same CRS, bounds, pixel size, and dimensions if it is a paired workflow

## BigEarthNet v2 Pretrained Band Orders

For the Hugging Face `BIFOLD-BigEarthNetv2-0/*-v0.2.0` pretrained models, use:

```text
S1 only: VV, VH
S2 only: B02, B03, B04, B05, B06, B07, B08, B8A, B11, B12
S1+S2:   VV, VH, B02, B03, B04, B05, B06, B07, B08, B8A, B11, B12
```

Older `v0.1.1` weights use a different order and should not be mixed with the
`v0.2.0` preprocessing contract.

## Pretrained Model Adapter

Member 2 exports channel-first arrays such as:

```text
S1:     (2, 120, 120)
S2:     (10, 120, 120)
S1+S2:  (12, 120, 120)
```

The model adapter prepares those for pretrained wrappers:

```text
S1:     (1, 2, 224, 224)
S2:     (1, 10, 224, 224)
S1+S2:  (1, 12, 224, 224)
```

Example:

```python
from backend.modeling.bigearthnet_adapter import prepare_bigearthnet_input

prepared = prepare_bigearthnet_input(
    "runs/benv1_pair_0/model_inputs/s1_s2_v0.2.0.npy",
    "runs/benv1_pair_0/model_inputs/prepared_for_bigearthnet.npy",
    sensor="all",
)
```

The optional `BigEarthNetPretrainedClassifier` wrapper is ready for Member 5/6,
but loading the actual Hugging Face model still requires PyTorch plus the
official BigEarthNet v2/reBEN model code.

## Backend API

Run the prototype backend:

```powershell
.\.venv\Scripts\python.exe -m uvicorn backend.main:app --reload --port 8000
```

Useful endpoints:

```text
GET  /health
POST /api/analyze
POST /api/analyze/paths
POST /api/analyze/benv1
GET  /api/runs/{run_id}
GET  /api/runs/{run_id}/trace
GET  /api/runs/{run_id}/outputs/{relative_path}
GET  /api/runs/{run_id}/report
```

Real `benv1_14k` API example:

```powershell
Invoke-RestMethod `
  -Method Post `
  -Uri http://127.0.0.1:8000/api/analyze/benv1 `
  -ContentType "application/json" `
  -Body '{"query":"Use the optical and SAR images together to identify built-up and water-covered regions.","index":0}'
```

The API returns a `run_id`; poll:

```powershell
Invoke-RestMethod http://127.0.0.1:8000/api/runs/<run_id>
```
