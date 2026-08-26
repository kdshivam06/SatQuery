# Data

Large datasets are intentionally ignored by git.

Recommended prototype order:

1. Download BigEarthNet.txt annotations.
2. Download VRSBench evaluation JSON files.
3. Download only the image split you need for the demo.
4. Download full BigEarthNet-S1/S2 imagery only when you have disk, time, and training hardware ready.

Use:

```powershell
.\.venv\Scripts\python.exe scripts\download_datasets.py --preset ben-txt
.\.venv\Scripts\python.exe scripts\download_datasets.py --preset vrsbench-eval
```

Large imagery downloads:

```powershell
.\.venv\Scripts\python.exe scripts\download_datasets.py --preset vrsbench-val-images
```

BigEarthNet imagery is hosted by the official BigEarthNet project on Zenodo:

- Sentinel-2 v2.0: about 59 GiB
- Sentinel-1 v2.0: about 51 GiB

For the prototype, do not download both full imagery archives until the model
training/evaluation pipeline is ready.
