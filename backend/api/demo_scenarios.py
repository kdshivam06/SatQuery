"""Demo scenarios – one per tool in the SatQuery registry.

Each scenario has:
  - query : the user-facing query that exercises this tool
  - tool  : the canonical tool name from registry.py
  - model : human-readable model / algorithm name
  - role  : one-line description of what the model does
  - audit_steps : ordered list of log steps (shown with time-delay in UI)
  - answer : the hardcoded final answer string
  - evidence: supporting evidence bullets
  - confidence: float 0–1
  - workflow: workflow tag string
"""

from __future__ import annotations

DEMO_SCENARIOS: list[dict] = [
    # ── 1. metadata_reader ────────────────────────────────────────────────
    {
        "id": "demo_metadata_reader",
        "query": "What are the spatial resolution, coordinate system, and band count of this satellite image?",
        "tool": "metadata_reader",
        "model": "MetadataReader (rasterio)",
        "role": "Reads GeoTIFF metadata — CRS, transform, bounds, resolution, bands, dtype, nodata.",
        "workflow": "metadata_inspection",
        "audit_steps": [
            {"delay": 0.4,  "step": "router",   "msg": "Query intent classified → metadata_inspection"},
            {"delay": 0.8,  "step": "routing",  "msg": "Selecting tool: metadata_reader (static_function / cpu)"},
            {"delay": 1.2,  "step": "execute",  "msg": "metadata_reader · Opening GeoTIFF with rasterio …"},
            {"delay": 2.0,  "step": "execute",  "msg": "metadata_reader · Parsing CRS, affine transform, band info …"},
            {"delay": 2.8,  "step": "execute",  "msg": "metadata_reader · Extracting nodata, dtype, spatial extent …"},
            {"delay": 3.4,  "step": "fusion",   "msg": "Fusing metadata summary → final answer"},
            {"delay": 3.9,  "step": "complete", "msg": "Run complete · confidence 0.98"},
        ],
        "answer": (
            "Image metadata analysis complete.\n\n"
            "• CRS: EPSG:32643 (WGS 84 / UTM Zone 43N)\n"
            "• Spatial resolution: 10 m × 10 m\n"
            "• Dimensions: 1200 × 1200 pixels (12 km × 12 km footprint)\n"
            "• Bands: 10 (B02, B03, B04, B05, B06, B07, B08, B8A, B11, B12)\n"
            "• Dtype: float32\n"
            "• Nodata: NaN\n"
            "• Bounds: [73.42°E – 73.54°E, 18.51°N – 18.62°N]\n"
            "• Affine transform: scale=(10.0, -10.0), origin=(73.42, 18.62)"
        ),
        "evidence": [
            "rasterio.open() succeeded — valid GeoTIFF structure confirmed",
            "CRS EPSG:32643 validated — UTM projection with metre units",
            "Band count 10 matches Sentinel-2 L2A multispectral product specification",
        ],
        "confidence": 0.98,
    },

    # ── 2. preview_generator ──────────────────────────────────────────────
    {
        "id": "demo_preview_generator",
        "query": "Generate an RGB preview thumbnail of this satellite patch for visual inspection.",
        "tool": "preview_generator",
        "model": "PreviewGenerator (Pillow / numpy)",
        "role": "Normalises raster bands (2%–98% percentile clip) and exports a PNG preview.",
        "workflow": "preview_generation",
        "audit_steps": [
            {"delay": 0.3,  "step": "router",   "msg": "Query intent → preview_generation"},
            {"delay": 0.7,  "step": "routing",  "msg": "Selecting tool: preview_generator (static_function / cpu)"},
            {"delay": 1.1,  "step": "execute",  "msg": "preview_generator · Reading band stack …"},
            {"delay": 1.8,  "step": "execute",  "msg": "preview_generator · Applying 2%–98% percentile normalisation …"},
            {"delay": 2.5,  "step": "execute",  "msg": "preview_generator · Compositing RGB (B04, B03, B02) …"},
            {"delay": 3.0,  "step": "execute",  "msg": "preview_generator · Saving PNG thumbnail to runs/ …"},
            {"delay": 3.5,  "step": "fusion",   "msg": "Preview artifact registered in manifest"},
            {"delay": 3.9,  "step": "complete", "msg": "Run complete · confidence 0.97"},
        ],
        "answer": (
            "RGB preview generated successfully.\n\n"
            "• Output file: runs/api/<run_id>/previews/rgb_preview.png\n"
            "• Composite: Red=B04, Green=B03, Blue=B02 (true-colour)\n"
            "• Normalisation: 2%–98% percentile clip applied per band\n"
            "• Dimensions: 512 × 512 px (downsampled from 1200 × 1200)\n"
            "• Scene quality: Cloud cover < 5%, excellent visibility\n"
            "The preview is now available for downstream VLM tools."
        ),
        "evidence": [
            "Bands B04/B03/B02 found in multispectral stack",
            "Percentile normalisation applied — dynamic range optimised",
            "PNG saved to manifest preview_path",
        ],
        "confidence": 0.97,
    },

    # ── 3. ndvi_vegetation_detector ───────────────────────────────────────
    {
        "id": "demo_ndvi",
        "query": "Show me the vegetation health across this agricultural scene using NDVI.",
        "tool": "ndvi_vegetation_detector",
        "model": "NDVITool (numpy spectral index)",
        "role": "Computes NDVI = (NIR − Red) / (NIR + Red) to map vegetation density and health.",
        "workflow": "vegetation_analysis",
        "audit_steps": [
            {"delay": 0.3,  "step": "router",   "msg": "Query intent → vegetation_analysis"},
            {"delay": 0.7,  "step": "routing",  "msg": "Selecting tool: ndvi_vegetation_detector (static_function / cpu)"},
            {"delay": 1.2,  "step": "execute",  "msg": "ndvi_vegetation_detector · Loading NIR (B08) and Red (B04) bands …"},
            {"delay": 2.0,  "step": "execute",  "msg": "ndvi_vegetation_detector · Computing NDVI index …"},
            {"delay": 2.7,  "step": "execute",  "msg": "ndvi_vegetation_detector · Thresholding: bare<0.2 | sparse 0.2–0.4 | dense>0.4 …"},
            {"delay": 3.2,  "step": "execute",  "msg": "ndvi_vegetation_detector · Rendering colour-map overlay …"},
            {"delay": 3.7,  "step": "fusion",   "msg": "Fusing NDVI statistics → answer"},
            {"delay": 4.1,  "step": "complete", "msg": "Run complete · confidence 0.93"},
        ],
        "answer": (
            "NDVI vegetation analysis complete.\n\n"
            "• Dense vegetation (NDVI > 0.40): 34.2% of scene → healthy crops / forest\n"
            "• Sparse vegetation (0.20–0.40): 28.7% → transitional / stressed vegetation\n"
            "• Bare soil / urban (NDVI < 0.20): 37.1% → non-vegetated surfaces\n"
            "• Peak NDVI: 0.82 (north-east quadrant — dense canopy)\n"
            "• Mean NDVI: 0.41 — moderate overall vegetation health\n\n"
            "Interpretation: The agricultural parcels in the south show NDVI 0.55–0.70, "
            "indicating active crop growth. Patches with NDVI < 0.25 suggest harvested or fallow fields."
        ),
        "evidence": [
            "NIR band B08 (842 nm) and Red band B04 (665 nm) loaded",
            "NDVI computed over 1.44M pixels",
            "Dense vegetation cover: 34.2% of scene",
        ],
        "confidence": 0.93,
    },

    # ── 4. ndwi_water_detector ────────────────────────────────────────────
    {
        "id": "demo_ndwi",
        "query": "Detect and map water bodies in this Sentinel-2 scene.",
        "tool": "ndwi_water_detector",
        "model": "NDWITool (McFeeters 1996)",
        "role": "Computes NDWI = (Green − NIR) / (Green + NIR) to identify open water surfaces.",
        "workflow": "water_detection",
        "audit_steps": [
            {"delay": 0.3,  "step": "router",   "msg": "Query intent → water_detection"},
            {"delay": 0.7,  "step": "routing",  "msg": "Selecting tool: ndwi_water_detector (static_function / cpu)"},
            {"delay": 1.1,  "step": "execute",  "msg": "ndwi_water_detector · Loading Green (B03) and NIR (B08) …"},
            {"delay": 1.9,  "step": "execute",  "msg": "ndwi_water_detector · Computing NDWI index …"},
            {"delay": 2.6,  "step": "execute",  "msg": "ndwi_water_detector · Applying threshold > 0.0 for open water …"},
            {"delay": 3.2,  "step": "execute",  "msg": "ndwi_water_detector · Generating water mask overlay …"},
            {"delay": 3.7,  "step": "fusion",   "msg": "Fusing water statistics → answer"},
            {"delay": 4.0,  "step": "complete", "msg": "Run complete · confidence 0.91"},
        ],
        "answer": (
            "NDWI water body detection complete.\n\n"
            "• Water pixels detected: 18.6% of scene (2,687,904 m²)\n"
            "• Primary water body: large reservoir in central-west sector\n"
            "• Secondary bodies: 3 small irrigation ponds identified (NE quadrant)\n"
            "• Max NDWI value: 0.74 — deep, clear water\n"
            "• Turbid water (NDWI 0.0–0.3): 4.1% of scene\n\n"
            "The primary reservoir spans ~2.1 km² and appears stable. "
            "Seasonal comparison recommended to assess water-level change."
        ),
        "evidence": [
            "Green band B03 and NIR band B08 extracted",
            "NDWI > 0.0 threshold applied — standard McFeeters criterion",
            "Water area: 2.69 km²",
        ],
        "confidence": 0.91,
    },

    # ── 5. mndwi_water_detector ───────────────────────────────────────────
    {
        "id": "demo_mndwi",
        "query": "Use MNDWI to separate water from built-up areas in this urban coastal scene.",
        "tool": "mndwi_water_detector",
        "model": "MNDWITool (Xu 2006)",
        "role": "Computes MNDWI = (Green − SWIR) / (Green + SWIR) — better separation of water from urban areas.",
        "workflow": "water_detection",
        "audit_steps": [
            {"delay": 0.3,  "step": "router",   "msg": "Query intent → water_detection (urban context → MNDWI preferred)"},
            {"delay": 0.8,  "step": "routing",  "msg": "Selecting tool: mndwi_water_detector (static_function / cpu)"},
            {"delay": 1.3,  "step": "execute",  "msg": "mndwi_water_detector · Loading Green (B03) and SWIR (B11) …"},
            {"delay": 2.1,  "step": "execute",  "msg": "mndwi_water_detector · Computing MNDWI = (B03−B11)/(B03+B11) …"},
            {"delay": 2.8,  "step": "execute",  "msg": "mndwi_water_detector · Suppressing built-up false positives …"},
            {"delay": 3.3,  "step": "execute",  "msg": "mndwi_water_detector · Generating refined water mask …"},
            {"delay": 3.8,  "step": "fusion",   "msg": "Fusing MNDWI results → answer"},
            {"delay": 4.2,  "step": "complete", "msg": "Run complete · confidence 0.92"},
        ],
        "answer": (
            "MNDWI water extraction (urban-suppressed) complete.\n\n"
            "• Water coverage: 22.4% of scene — higher than NDWI (18.6%) due to fewer false negatives\n"
            "• Built-up false positives eliminated: ~3.8% reduction vs standard NDWI\n"
            "• Coastal water body identified along southern boundary: 5.8 km²\n"
            "• Turbid estuarine zone (MNDWI 0.0–0.2): 2.3% of scene\n\n"
            "MNDWI is more reliable in this urban-coastal context as SWIR strongly absorbs "
            "water while remaining highly reflective over concrete/rooftops."
        ),
        "evidence": [
            "SWIR band B11 (1610 nm) used — superior water/urban contrast",
            "MNDWI suppressed 3.8% urban false-positive area vs NDWI",
            "Coastal water extent: 5.8 km²",
        ],
        "confidence": 0.92,
    },

    # ── 6. ndbi_builtup_detector ──────────────────────────────────────────
    {
        "id": "demo_ndbi",
        "query": "Map the urban built-up extent and estimate the impervious surface area.",
        "tool": "ndbi_builtup_detector",
        "model": "NDBITool (Zha 2003)",
        "role": "Computes NDBI = (SWIR − NIR) / (SWIR + NIR) to detect urban and impervious surfaces.",
        "workflow": "urban_analysis",
        "audit_steps": [
            {"delay": 0.3,  "step": "router",   "msg": "Query intent → urban_analysis"},
            {"delay": 0.7,  "step": "routing",  "msg": "Selecting tool: ndbi_builtup_detector (static_function / cpu)"},
            {"delay": 1.2,  "step": "execute",  "msg": "ndbi_builtup_detector · Loading SWIR (B11) and NIR (B08) …"},
            {"delay": 2.0,  "step": "execute",  "msg": "ndbi_builtup_detector · Computing NDBI = (B11−B08)/(B11+B08) …"},
            {"delay": 2.7,  "step": "execute",  "msg": "ndbi_builtup_detector · Applying built-up threshold > 0.0 …"},
            {"delay": 3.3,  "step": "execute",  "msg": "ndbi_builtup_detector · Generating urban mask …"},
            {"delay": 3.8,  "step": "fusion",   "msg": "Fusing NDBI statistics → answer"},
            {"delay": 4.1,  "step": "complete", "msg": "Run complete · confidence 0.89"},
        ],
        "answer": (
            "NDBI urban built-up detection complete.\n\n"
            "• Built-up / impervious surface: 41.3% of scene (5,947,200 m²)\n"
            "• High-density urban core (NDBI > 0.20): 18.7% — dense rooftops/roads\n"
            "• Mixed built-up (NDBI 0.0–0.20): 22.6% — suburban/industrial mix\n"
            "• Peak NDBI: 0.54 — industrial rooftop cluster in NW sector\n\n"
            "Estimated impervious surface area: ~5.95 km² across the 12 km² scene. "
            "High heat retention expected in the NW industrial cluster."
        ),
        "evidence": [
            "SWIR B11 and NIR B08 bands loaded",
            "NDBI > 0 threshold applied per Zha (2003)",
            "Built-up extent: 41.3% of scene",
        ],
        "confidence": 0.89,
    },

    # ── 7. sar_water_detector ─────────────────────────────────────────────
    {
        "id": "demo_sar_water",
        "query": "Detect flooded areas in this Sentinel-1 SAR image after the monsoon event.",
        "tool": "sar_water_detector",
        "model": "SARWaterTool (backscatter threshold)",
        "role": "Detects water / flooded regions from SAR backscatter using adaptive thresholding.",
        "workflow": "flood_mapping",
        "audit_steps": [
            {"delay": 0.3,  "step": "router",   "msg": "Query intent → flood_mapping (SAR modality detected)"},
            {"delay": 0.8,  "step": "routing",  "msg": "Selecting tool: sar_water_detector (static_function / cpu)"},
            {"delay": 1.3,  "step": "execute",  "msg": "sar_water_detector · Loading SAR VV polarisation band …"},
            {"delay": 2.1,  "step": "execute",  "msg": "sar_water_detector · Applying speckle filter (Lee 5×5) …"},
            {"delay": 2.9,  "step": "execute",  "msg": "sar_water_detector · Adaptive threshold − 14 dB (Otsu-adapted) …"},
            {"delay": 3.5,  "step": "execute",  "msg": "sar_water_detector · Generating flood extent mask …"},
            {"delay": 4.0,  "step": "fusion",   "msg": "Fusing SAR water results → answer"},
            {"delay": 4.4,  "step": "complete", "msg": "Run complete · confidence 0.88"},
        ],
        "answer": (
            "SAR-based flood detection complete.\n\n"
            "• Flooded area detected: 14.8% of scene (2,131,200 m²)\n"
            "• Primary flood extent: southern agricultural belt — consistent with low-lying terrain\n"
            "• Backscatter threshold: −14 dB (VV polarisation)\n"
            "• Urban shadow artefacts masked: 1.2% of scene excluded\n"
            "• SAR penetrates cloud cover — detection unaffected by monsoon cloud\n\n"
            "Post-monsoon flood inundation estimated at ~2.1 km². Flood waters are primarily "
            "affecting paddy fields. Emergency response recommendation: prioritise southern quadrant."
        ),
        "evidence": [
            "SAR VV band loaded (Sentinel-1 GRD, IW mode)",
            "Lee speckle filter applied to reduce noise",
            "Flood extent: 2.13 km² at −14 dB threshold",
        ],
        "confidence": 0.88,
    },

    # ── 8. sar_builtup_detector ───────────────────────────────────────────
    {
        "id": "demo_sar_builtup",
        "query": "Identify built-up and urban structures in this Sentinel-1 SAR acquisition.",
        "tool": "sar_builtup_detector",
        "model": "SARBuiltupTool (high-backscatter clustering)",
        "role": "Detects urban/built-up areas from SAR using high backscatter intensity signatures.",
        "workflow": "urban_analysis",
        "audit_steps": [
            {"delay": 0.3,  "step": "router",   "msg": "Query intent → urban_analysis (SAR modality)"},
            {"delay": 0.7,  "step": "routing",  "msg": "Selecting tool: sar_builtup_detector (static_function / cpu)"},
            {"delay": 1.2,  "step": "execute",  "msg": "sar_builtup_detector · Loading VV + VH dual-polarisation …"},
            {"delay": 2.0,  "step": "execute",  "msg": "sar_builtup_detector · Computing VV/VH ratio for double-bounce …"},
            {"delay": 2.8,  "step": "execute",  "msg": "sar_builtup_detector · High-backscatter cluster detection (>−4 dB) …"},
            {"delay": 3.4,  "step": "execute",  "msg": "sar_builtup_detector · Morphological cleanup (closing 3×3) …"},
            {"delay": 3.9,  "step": "fusion",   "msg": "Fusing SAR built-up results → answer"},
            {"delay": 4.3,  "step": "complete", "msg": "Run complete · confidence 0.87"},
        ],
        "answer": (
            "SAR built-up area detection complete.\n\n"
            "• Built-up structures detected: 32.1% of scene\n"
            "• Double-bounce scatterers (dense urban): 15.4% — high-rise / industrial buildings\n"
            "• Low-density built-up (VV > −4 dB): 16.7% — residential / semi-urban\n"
            "• VV/VH ratio peak: 8.3 dB (NE corner — aligned building grid, likely industrial estate)\n\n"
            "SAR-based detection is cloud-independent and captures 3D structural scatter. "
            "The double-bounce signature strongly indicates orthogonal building-to-ground interaction."
        ),
        "evidence": [
            "VV + VH dual-polarisation loaded (Sentinel-1)",
            "Double-bounce ratio computed (VV/VH > 8 dB)",
            "Built-up extent: 32.1% of scene",
        ],
        "confidence": 0.87,
    },

    # ── 9. change_map_generator ───────────────────────────────────────────
    {
        "id": "demo_change_map",
        "query": "Show what changed between the pre-event and post-event SAR images.",
        "tool": "change_map_generator",
        "model": "ChangeMapTool (log-ratio differencing)",
        "role": "Generates change maps by differencing paired temporal SAR or optical images.",
        "workflow": "change_detection",
        "audit_steps": [
            {"delay": 0.3,  "step": "router",   "msg": "Query intent → change_detection (bi-temporal pair detected)"},
            {"delay": 0.8,  "step": "routing",  "msg": "Selecting tool: change_map_generator (static_function / cpu)"},
            {"delay": 1.3,  "step": "execute",  "msg": "change_map_generator · Loading pre-event image (T1) …"},
            {"delay": 1.8,  "step": "execute",  "msg": "change_map_generator · Loading post-event image (T2) …"},
            {"delay": 2.5,  "step": "execute",  "msg": "change_map_generator · Computing log-ratio: log10(T2/T1) …"},
            {"delay": 3.2,  "step": "execute",  "msg": "change_map_generator · Applying ±1.5σ change threshold …"},
            {"delay": 3.8,  "step": "execute",  "msg": "change_map_generator · Rendering gain/loss change map …"},
            {"delay": 4.3,  "step": "fusion",   "msg": "Fusing change statistics → answer"},
            {"delay": 4.7,  "step": "complete", "msg": "Run complete · confidence 0.90"},
        ],
        "answer": (
            "Bi-temporal change detection complete.\n\n"
            "• Total changed area: 23.8% of scene\n"
            "• Positive change (increased backscatter / DN): 11.2% → new construction, vegetation growth\n"
            "• Negative change (decreased backscatter / DN): 12.6% → flood, deforestation, demolition\n"
            "• Change hotspot: SE quadrant — consistent with post-event flooding (dark patch, −3.4 dB)\n"
            "• Stable area: 76.2% — no significant change detected\n\n"
            "Log-ratio change map generated. The SE flooding pattern is spatially coherent "
            "and exceeds 2σ — high confidence of real surface change."
        ),
        "evidence": [
            "T1 (pre-event) and T2 (post-event) images aligned",
            "Log-ratio differencing applied: log10(T2/T1)",
            "23.8% scene change at ±1.5σ threshold",
        ],
        "confidence": 0.90,
    },

    # ── 10. mask_fusion_tool ──────────────────────────────────────────────
    {
        "id": "demo_mask_fusion",
        "query": "Combine the water mask and vegetation mask to identify wetland regions.",
        "tool": "mask_fusion_tool",
        "model": "MaskFusionTool (boolean logical ops)",
        "role": "Fuses multiple binary masks (AND/OR/XOR) to produce composite land-cover classifications.",
        "workflow": "multi_mask_fusion",
        "audit_steps": [
            {"delay": 0.3,  "step": "router",   "msg": "Query intent → multi_mask_fusion"},
            {"delay": 0.7,  "step": "routing",  "msg": "Selecting tool: mask_fusion_tool (static_function / cpu)"},
            {"delay": 1.0,  "step": "execute",  "msg": "mask_fusion_tool · Loading NDWI water mask …"},
            {"delay": 1.5,  "step": "execute",  "msg": "mask_fusion_tool · Loading NDVI vegetation mask …"},
            {"delay": 2.2,  "step": "execute",  "msg": "mask_fusion_tool · Computing intersection (water AND vegetation) …"},
            {"delay": 3.0,  "step": "execute",  "msg": "mask_fusion_tool · Filtering isolated pixels (min area 500 m²) …"},
            {"delay": 3.5,  "step": "fusion",   "msg": "Fusing combined mask statistics → answer"},
            {"delay": 3.9,  "step": "complete", "msg": "Run complete · confidence 0.94"},
        ],
        "answer": (
            "Mask fusion (water ∩ vegetation = wetland) complete.\n\n"
            "• Wetland regions identified: 6.4% of scene (921,600 m²)\n"
            "• Primary wetland cluster: northern river bend — 4.1 km²\n"
            "• Secondary patches: 3 isolated pockets along drainage channels\n"
            "• Fusion logic: NDWI > 0.0 AND NDVI > 0.2 (waterlogged vegetation)\n\n"
            "Wetland classification complete. The northern cluster matches a mapped "
            "mangrove zone from SWIR-NIR analysis. Recommend seasonal monitoring."
        ),
        "evidence": [
            "NDWI water mask and NDVI vegetation mask fused",
            "Intersection logic: water AND vegetation pixels",
            "Wetland area: 0.92 km²",
        ],
        "confidence": 0.94,
    },

    # ── 11. area_calculator ───────────────────────────────────────────────
    {
        "id": "demo_area_calculator",
        "query": "Calculate the exact area of the flooded region in square kilometres.",
        "tool": "area_calculator",
        "model": "AreaCalculatorTool (pixel-to-area projection)",
        "role": "Converts binary mask pixel counts to real-world area using CRS projection parameters.",
        "workflow": "area_estimation",
        "audit_steps": [
            {"delay": 0.3,  "step": "router",   "msg": "Query intent → area_estimation"},
            {"delay": 0.7,  "step": "routing",  "msg": "Selecting tool: area_calculator (static_function / cpu)"},
            {"delay": 1.0,  "step": "execute",  "msg": "area_calculator · Reading mask pixel count …"},
            {"delay": 1.6,  "step": "execute",  "msg": "area_calculator · Retrieving pixel size from affine transform (10 m × 10 m) …"},
            {"delay": 2.3,  "step": "execute",  "msg": "area_calculator · Computing geodesic area using CRS EPSG:32643 …"},
            {"delay": 2.9,  "step": "fusion",   "msg": "Fusing area calculation → answer"},
            {"delay": 3.3,  "step": "complete", "msg": "Run complete · confidence 0.99"},
        ],
        "answer": (
            "Area calculation complete.\n\n"
            "• Flooded pixel count: 21,312 pixels\n"
            "• Pixel resolution: 10 m × 10 m = 100 m² per pixel\n"
            "• Total flooded area: 2.131 km² (2,131,200 m²)\n"
            "• CRS: EPSG:32643 (metric projection — no distortion correction needed)\n"
            "• Confidence: Very high — pixel-perfect count from binary mask\n\n"
            "Area estimate: 2.13 km² flooded. This equals approximately 213 hectares or 526 acres."
        ),
        "evidence": [
            "21,312 positive mask pixels counted",
            "Pixel size 100 m² from affine transform",
            "Geodesic area in EPSG:32643 (metric) — no reprojection error",
        ],
        "confidence": 0.99,
    },

    # ── 12. overlay_generator ─────────────────────────────────────────────
    {
        "id": "demo_overlay",
        "query": "Overlay the water detection mask on top of the RGB image for visual presentation.",
        "tool": "overlay_generator",
        "model": "OverlayGeneratorTool (Pillow alpha composite)",
        "role": "Composites classification masks over RGB previews using configurable colours and opacity.",
        "workflow": "visualization",
        "audit_steps": [
            {"delay": 0.3,  "step": "router",   "msg": "Query intent → visualization / overlay"},
            {"delay": 0.7,  "step": "routing",  "msg": "Selecting tool: overlay_generator (static_function / cpu)"},
            {"delay": 1.0,  "step": "execute",  "msg": "overlay_generator · Loading RGB preview …"},
            {"delay": 1.5,  "step": "execute",  "msg": "overlay_generator · Loading water mask (binary, NDWI) …"},
            {"delay": 2.1,  "step": "execute",  "msg": "overlay_generator · Applying teal (#00BCD4) @ 60% opacity …"},
            {"delay": 2.8,  "step": "execute",  "msg": "overlay_generator · Alpha compositing layers …"},
            {"delay": 3.2,  "step": "execute",  "msg": "overlay_generator · Saving overlay PNG …"},
            {"delay": 3.7,  "step": "complete", "msg": "Run complete · confidence 0.96"},
        ],
        "answer": (
            "Water mask overlay generated successfully.\n\n"
            "• Output: runs/api/<run_id>/overlays/water_overlay.png\n"
            "• Overlay colour: teal (#00BCD4) at 60% opacity\n"
            "• Background: true-colour RGB composite (B04/B03/B02)\n"
            "• Masked pixels: 21,312 (18.6% of scene) — highlighted in teal\n\n"
            "The overlay is ready for report inclusion and visual inspection. "
            "Teal highlights correspond to NDWI > 0.0 water detections."
        ),
        "evidence": [
            "RGB preview and binary water mask loaded",
            "Alpha composite at 60% opacity",
            "Overlay PNG saved to runs directory",
        ],
        "confidence": 0.96,
    },

    # ── 13. custom_sar_optical_dual_encoder_tool ──────────────────────────
    {
        "id": "demo_dual_encoder",
        "query": "Match this SAR patch to the most similar optical scene in the database using cross-modal retrieval.",
        "tool": "custom_sar_optical_dual_encoder_tool",
        "model": "CustomDualEncoderTool (SatQuery dual-encoder)",
        "role": "Projects SAR and optical patches into a shared embedding space for cross-modal similarity matching.",
        "workflow": "cross_modal_retrieval",
        "audit_steps": [
            {"delay": 0.3,  "step": "router",   "msg": "Query intent → cross_modal_retrieval"},
            {"delay": 0.8,  "step": "routing",  "msg": "Selecting tool: custom_sar_optical_dual_encoder_tool (local_gpu_light)"},
            {"delay": 1.4,  "step": "execute",  "msg": "dual_encoder · Loading SAR encoder (VGG-style, VV/VH input) …"},
            {"delay": 2.2,  "step": "execute",  "msg": "dual_encoder · Loading optical encoder (ResNet-50 backbone) …"},
            {"delay": 3.0,  "step": "execute",  "msg": "dual_encoder · Encoding SAR patch → 512-dim embedding …"},
            {"delay": 3.8,  "step": "execute",  "msg": "dual_encoder · Encoding optical patch → 512-dim embedding …"},
            {"delay": 4.5,  "step": "execute",  "msg": "dual_encoder · Computing cosine similarity in shared space …"},
            {"delay": 5.1,  "step": "fusion",   "msg": "Fusing similarity score → answer"},
            {"delay": 5.5,  "step": "complete", "msg": "Run complete · confidence 0.84"},
        ],
        "answer": (
            "Cross-modal SAR↔Optical matching complete.\n\n"
            "• Cosine similarity score: 0.847 (high match)\n"
            "• SAR embedding norm: 0.982 (well-conditioned)\n"
            "• Optical embedding norm: 0.976\n"
            "• Top-1 match: Sentinel-2 patch S2A_58_90 (same geographic tile, co-registered)\n"
            "• Geometric alignment: RMS error < 0.5 pixels after co-registration\n\n"
            "The dual-encoder confirms strong cross-modal correspondence. "
            "The matched optical scene was acquired 18 hours after the SAR pass. "
            "Suitable for fusion analysis and change detection workflows."
        ),
        "evidence": [
            "SAR VV/VH and Optical B02–B12 encoded into 512-dim shared space",
            "Cosine similarity: 0.847 — high confidence match",
            "Co-registration error < 0.5 px",
        ],
        "confidence": 0.84,
    },

    # ── 14. croma_cross_modal_feature_tool ────────────────────────────────
    {
        "id": "demo_croma",
        "query": "Extract cross-modal SAR–optical feature embeddings using CROMA for similarity scoring.",
        "tool": "croma_cross_modal_feature_tool",
        "model": "CROMATool (CROMA-base pretrained)",
        "role": "Extracts contrastive SAR–optical features via the CROMA dual-stream transformer encoder.",
        "workflow": "cross_modal_feature_extraction",
        "audit_steps": [
            {"delay": 0.4,  "step": "router",   "msg": "Query intent → cross_modal_feature_extraction"},
            {"delay": 0.9,  "step": "routing",  "msg": "Selecting tool: croma_cross_modal_feature_tool (local_gpu_light)"},
            {"delay": 1.5,  "step": "execute",  "msg": "croma_tool · Loading CROMA-base checkpoint …"},
            {"delay": 2.5,  "step": "execute",  "msg": "croma_tool · Pre-processing SAR patch (120×120 → 224×224) …"},
            {"delay": 3.3,  "step": "execute",  "msg": "croma_tool · Pre-processing optical patch (10-band → normalised) …"},
            {"delay": 4.1,  "step": "execute",  "msg": "croma_tool · Forward pass through dual-stream transformer …"},
            {"delay": 5.0,  "step": "execute",  "msg": "croma_tool · Extracting [CLS] tokens from both branches …"},
            {"delay": 5.6,  "step": "fusion",   "msg": "Fusing CROMA features → answer"},
            {"delay": 6.0,  "step": "complete", "msg": "Run complete · confidence 0.86"},
        ],
        "answer": (
            "CROMA cross-modal feature extraction complete.\n\n"
            "• SAR feature vector: 768-dim [CLS] token from SAR stream\n"
            "• Optical feature vector: 768-dim [CLS] token from optical stream\n"
            "• Contrastive similarity: 0.863 (CROMA shared metric space)\n"
            "• Model: CROMA-base (pretrained on SEN1-2 dataset)\n"
            "• Inference time: 0.8 s (RTX 2050, fp16)\n\n"
            "CROMA features confirm strong SAR–optical correspondence. "
            "The contrastive score 0.863 exceeds the co-registration validation threshold of 0.75."
        ),
        "evidence": [
            "CROMA-base loaded from backend/models/croma/CROMA_base.pt",
            "768-dim [CLS] tokens extracted from both streams",
            "Contrastive similarity: 0.863",
        ],
        "confidence": 0.86,
    },

    # ── 15. remoteclip_optical_retrieval_tool ─────────────────────────────
    {
        "id": "demo_remoteclip",
        "query": "Find images from the database that match this description: agricultural fields with irrigation canals.",
        "tool": "remoteclip_optical_retrieval_tool",
        "model": "RemoteCLIPTool (RemoteCLIP-ViT-B-32)",
        "role": "Text-to-image retrieval for remote-sensing scenes using CLIP trained on RS datasets.",
        "workflow": "text_to_image_retrieval",
        "audit_steps": [
            {"delay": 0.4,  "step": "router",   "msg": "Query intent → text_to_image_retrieval"},
            {"delay": 0.8,  "step": "routing",  "msg": "Selecting tool: remoteclip_optical_retrieval_tool (local_gpu_light)"},
            {"delay": 1.4,  "step": "execute",  "msg": "remoteclip_tool · Loading RemoteCLIP-ViT-B-32 checkpoint …"},
            {"delay": 2.2,  "step": "execute",  "msg": "remoteclip_tool · Encoding text query → 512-dim CLIP embedding …"},
            {"delay": 3.0,  "step": "execute",  "msg": "remoteclip_tool · Encoding candidate optical patch …"},
            {"delay": 3.7,  "step": "execute",  "msg": "remoteclip_tool · Computing CLIP cosine similarity …"},
            {"delay": 4.2,  "step": "fusion",   "msg": "Fusing retrieval scores → answer"},
            {"delay": 4.6,  "step": "complete", "msg": "Run complete · confidence 0.82"},
        ],
        "answer": (
            "RemoteCLIP text-to-image retrieval complete.\n\n"
            "• Query: 'agricultural fields with irrigation canals'\n"
            "• CLIP similarity to query: 0.791 (strong semantic match)\n"
            "• Scene description match: confirmed — NDVI analysis shows 34% crop cover\n"
            "• Linear canal structures detected in band ratios (NW–SE orientation)\n"
            "• Top retrieval score vs null text: +0.24 improvement\n\n"
            "RemoteCLIP confirms the query semantically matches the uploaded scene. "
            "The model was trained on RSICD, UCM, and AID datasets — well-calibrated for this scene type."
        ),
        "evidence": [
            "RemoteCLIP-ViT-B-32 loaded from backend/models/remoteclip/",
            "Text embedding and image embedding cosine similarity: 0.791",
            "Scene confirmed: agricultural with canal structures",
        ],
        "confidence": 0.82,
    },

    # ── 16. geochat_vqa_caption_tool ──────────────────────────────────────
    {
        "id": "demo_geochat",
        "query": "Describe this satellite image in detail and identify all major land use categories.",
        "tool": "geochat_vqa_caption_tool",
        "model": "GeoChat (MBZUAI/geochat-7B)",
        "role": "Region-level VQA and free-text captioning for remote-sensing images via a 7B VLM.",
        "workflow": "vqa_captioning",
        "audit_steps": [
            {"delay": 0.4,  "step": "router",   "msg": "Query intent → vqa_captioning"},
            {"delay": 0.9,  "step": "routing",  "msg": "Selecting tool: geochat_vqa_caption_tool (remote_hf_api)"},
            {"delay": 1.5,  "step": "execute",  "msg": "geochat_tool · Encoding RGB preview as base64 …"},
            {"delay": 2.3,  "step": "execute",  "msg": "geochat_tool · Sending to HF Serverless API (MBZUAI/geochat-7B) …"},
            {"delay": 4.5,  "step": "execute",  "msg": "geochat_tool · Waiting for VLM response (7B inference) …"},
            {"delay": 6.8,  "step": "execute",  "msg": "geochat_tool · Parsing structured answer from VLM output …"},
            {"delay": 7.4,  "step": "fusion",   "msg": "Fusing GeoChat answer → final response"},
            {"delay": 7.9,  "step": "complete", "msg": "Run complete · confidence 0.78"},
        ],
        "answer": (
            "GeoChat VQA captioning complete.\n\n"
            "The scene depicts a mixed urban-agricultural landscape in a semi-arid region. "
            "Key land use categories identified:\n\n"
            "1. Urban/residential: ~38% — dense rooftop patterns visible in NE sector, "
            "grid street layout characteristic of planned development\n"
            "2. Agricultural cropland: ~31% — rectangular field parcels with variable NDVI, "
            "crop rows aligned N–S suggesting mechanised cultivation\n"
            "3. Bare soil / fallow: ~18% — light-toned compact soil typical of Rabi season\n"
            "4. Water body: ~8% — permanent reservoir with clear shoreline\n"
            "5. Vegetation/scrubland: ~5% — sparse natural cover along field boundaries\n\n"
            "No active deforestation detected. Road network density suggests peri-urban fringe."
        ),
        "evidence": [
            "GeoChat-7B inference via HF Serverless API",
            "5 land use categories identified",
            "VLM output parsed and structured",
        ],
        "confidence": 0.78,
    },

    # ── 17. rsllava_vqa_caption_tool ──────────────────────────────────────
    {
        "id": "demo_rsllava",
        "query": "What are the spectral and structural characteristics visible in this multispectral image?",
        "tool": "rsllava_vqa_caption_tool",
        "model": "RS-LLaVA (BigData-KSU/RS-llava-v1.5-7b-LoRA)",
        "role": "Remote-sensing VQA and scene understanding via a LoRA-finetuned LLaVA 7B model.",
        "workflow": "vqa_captioning",
        "audit_steps": [
            {"delay": 0.4,  "step": "router",   "msg": "Query intent → vqa_captioning (multispectral → RS-LLaVA preferred)"},
            {"delay": 0.9,  "step": "routing",  "msg": "Selecting tool: rsllava_vqa_caption_tool (remote_hf_api)"},
            {"delay": 1.5,  "step": "execute",  "msg": "rsllava_tool · Preparing optical preview for RS-LLaVA …"},
            {"delay": 2.3,  "step": "execute",  "msg": "rsllava_tool · Calling HF Serverless API (RS-llava-v1.5-7b-LoRA) …"},
            {"delay": 5.0,  "step": "execute",  "msg": "rsllava_tool · Running LoRA-adapted inference …"},
            {"delay": 7.2,  "step": "execute",  "msg": "rsllava_tool · Extracting spectral + structural answer …"},
            {"delay": 7.8,  "step": "fusion",   "msg": "Fusing RS-LLaVA answer → response"},
            {"delay": 8.3,  "step": "complete", "msg": "Run complete · confidence 0.76"},
        ],
        "answer": (
            "RS-LLaVA multispectral analysis complete.\n\n"
            "Spectral characteristics:\n"
            "• NIR (B08) shows high reflectance in vegetated parcels (ρ > 0.4) — "
            "healthy chlorophyll absorption signature\n"
            "• SWIR (B11) high over bare soil — diagnostic of clay-rich soil mineralogy\n"
            "• Blue (B02) low across scene — minimal atmospheric scattering at acquisition time\n\n"
            "Structural characteristics:\n"
            "• Rectangular field boundaries at 87° bearing — mechanised agricultural design\n"
            "• Linear road network of 3.2 m width — consistent with 10 m resolution sampling\n"
            "• Circular pivot irrigation patterns detected in SW sector (radius ~400 m)\n\n"
            "Interpretation: The multispectral signature is consistent with Kharif season crops "
            "in a loamy-clay soil environment with structured irrigation."
        ),
        "evidence": [
            "RS-LLaVA-v1.5-7b-LoRA inference on optical preview",
            "Spectral reflectance patterns analysed across 10 bands",
            "Structural features: fields, roads, pivot irrigation",
        ],
        "confidence": 0.76,
    },

    # ── 18. teochat_change_vqa_tool ───────────────────────────────────────
    {
        "id": "demo_teochat",
        "query": "Compare these two temporal satellite images and describe what changed over the past year.",
        "tool": "teochat_change_vqa_tool",
        "model": "TEOChat (jirvin16/TEOChat)",
        "role": "Bi-temporal change VQA — describes land cover changes between two temporal images.",
        "workflow": "change_detection",
        "audit_steps": [
            {"delay": 0.4,  "step": "router",   "msg": "Query intent → change_detection (bi-temporal pair → TEOChat)"},
            {"delay": 0.9,  "step": "routing",  "msg": "Selecting tool: teochat_change_vqa_tool (remote_hf_api)"},
            {"delay": 1.5,  "step": "execute",  "msg": "teochat_tool · Loading T1 preview (pre-change) …"},
            {"delay": 2.1,  "step": "execute",  "msg": "teochat_tool · Loading T2 preview (post-change) …"},
            {"delay": 2.8,  "step": "execute",  "msg": "teochat_tool · Sending bi-temporal pair to TEOChat HF Space …"},
            {"delay": 5.5,  "step": "execute",  "msg": "teochat_tool · Running temporal attention across both frames …"},
            {"delay": 7.8,  "step": "execute",  "msg": "teochat_tool · Parsing change description from VLM output …"},
            {"delay": 8.4,  "step": "fusion",   "msg": "Fusing TEOChat change description → answer"},
            {"delay": 8.9,  "step": "complete", "msg": "Run complete · confidence 0.80"},
        ],
        "answer": (
            "TEOChat bi-temporal change analysis complete.\n\n"
            "Changes detected between T1 (2023-06-15) and T2 (2024-06-20):\n\n"
            "1. Urban expansion: New construction visible in NE quadrant — approximately "
            "0.8 km² of agricultural land converted to residential plots\n"
            "2. Reservoir level change: Water body in SW reduced by ~15% (seasonal drawdown "
            "or extraction), shoreline recession ~120 m inward\n"
            "3. Crop pattern shift: T1 shows summer Kharif crops; T2 shows harvested "
            "stubble fields — consistent with seasonal cycle, not change of concern\n"
            "4. Road network addition: New 2.4 km paved road connecting NE settlement to highway\n\n"
            "Primary change driver: Urban encroachment on agricultural periphery. "
            "Recommend monitoring at 6-month intervals."
        ),
        "evidence": [
            "T1 and T2 bi-temporal previews processed by TEOChat",
            "4 change categories identified",
            "Urban expansion: 0.8 km² land conversion detected",
        ],
        "confidence": 0.80,
    },

    # ── 19. segearth_text_guided_segmentation_tool ────────────────────────
    {
        "id": "demo_segearth",
        "query": "Segment all agricultural field boundaries in this image using text-guided segmentation.",
        "tool": "segearth_text_guided_segmentation_tool",
        "model": "SegEarth-OV (Dingyi111/SegEarth-OV)",
        "role": "Open-vocabulary text-guided semantic segmentation of remote-sensing scenes.",
        "workflow": "text_guided_segmentation",
        "audit_steps": [
            {"delay": 0.4,  "step": "router",   "msg": "Query intent → text_guided_segmentation"},
            {"delay": 0.9,  "step": "routing",  "msg": "Selecting tool: segearth_text_guided_segmentation_tool (remote_hf_api)"},
            {"delay": 1.5,  "step": "execute",  "msg": "segearth_tool · Encoding query: 'agricultural field boundary' …"},
            {"delay": 2.3,  "step": "execute",  "msg": "segearth_tool · Sending image + text prompt to SegEarth-OV endpoint …"},
            {"delay": 4.8,  "step": "execute",  "msg": "segearth_tool · Running open-vocab decoder …"},
            {"delay": 6.5,  "step": "execute",  "msg": "segearth_tool · Post-processing segmentation masks …"},
            {"delay": 7.2,  "step": "execute",  "msg": "segearth_tool · Saving polygon boundaries …"},
            {"delay": 7.8,  "step": "fusion",   "msg": "Fusing segmentation masks → answer"},
            {"delay": 8.2,  "step": "complete", "msg": "Run complete · confidence 0.79"},
        ],
        "answer": (
            "SegEarth-OV text-guided segmentation complete.\n\n"
            "Text prompt: 'agricultural field boundary'\n\n"
            "• Segments detected: 47 distinct field parcels\n"
            "• Total agricultural area: 4.32 km² (30% of scene)\n"
            "• Average parcel size: 9.2 hectares\n"
            "• Boundary detection confidence: 0.79 (open-vocabulary)\n"
            "• Largest parcel: 28.4 ha (N sector, circular pivot irrigation)\n"
            "• Smallest parcel: 1.1 ha (smallholder plots, S boundary)\n\n"
            "Segmentation masks exported as PNG overlays. "
            "GeoJSON polygon boundaries saved to runs/<run_id>/segmentation/fields.geojson."
        ),
        "evidence": [
            "SegEarth-OV open-vocabulary segmentation applied",
            "47 field parcels detected",
            "Total agricultural area: 4.32 km²",
        ],
        "confidence": 0.79,
    },

    # ── 20. sarclip_sar_text_tool ─────────────────────────────────────────
    {
        "id": "demo_sarclip",
        "query": "Zero-shot classify this SAR image: is it showing a port, airport, or agricultural area?",
        "tool": "sarclip_sar_text_tool",
        "model": "SARCLIP (BiliSakura/SARCLIP-ViT-L-14)",
        "role": "Zero-shot SAR image-text classification using CLIP trained exclusively on SAR imagery.",
        "workflow": "sar_zero_shot_classification",
        "audit_steps": [
            {"delay": 0.4,  "step": "router",   "msg": "Query intent → sar_zero_shot_classification"},
            {"delay": 0.9,  "step": "routing",  "msg": "Selecting tool: sarclip_sar_text_tool (remote_hf_api)"},
            {"delay": 1.5,  "step": "execute",  "msg": "sarclip_tool · Encoding SAR image via ViT-L/14 image encoder …"},
            {"delay": 2.5,  "step": "execute",  "msg": "sarclip_tool · Encoding class labels as text embeddings …"},
            {"delay": 3.3,  "step": "execute",  "msg": "sarclip_tool · Computing softmax over class similarities …"},
            {"delay": 4.1,  "step": "execute",  "msg": "sarclip_tool · Ranking: [agricultural:0.71, port:0.18, airport:0.11] …"},
            {"delay": 4.7,  "step": "fusion",   "msg": "Fusing SARCLIP classification → answer"},
            {"delay": 5.1,  "step": "complete", "msg": "Run complete · confidence 0.71"},
        ],
        "answer": (
            "SARCLIP zero-shot SAR classification complete.\n\n"
            "Candidate classes: port / airport / agricultural area\n\n"
            "• Agricultural area: 71.3% probability ← WINNER\n"
            "• Port / harbour:    18.2%\n"
            "• Airport:           10.5%\n\n"
            "Classification: AGRICULTURAL AREA (zero-shot, no fine-tuning)\n\n"
            "SAR signature evidence:\n"
            "• Low uniform backscatter (−18 to −12 dB) — consistent with smooth crop surfaces\n"
            "• No high-intensity point scatterers — rules out metal structures (port/airport)\n"
            "• Rectangular field patterns in coherence image — agricultural geometry confirmed\n\n"
            "SARCLIP-ViT-L-14 trained on SAR-specific text-image pairs. "
            "Zero-shot accuracy on MSAR benchmark: 74.2% top-1."
        ),
        "evidence": [
            "SARCLIP-ViT-L-14 image encoder applied to SAR VV band",
            "Softmax over 3 class embeddings",
            "Agricultural area: 71.3% — dominant class",
        ],
        "confidence": 0.71,
    },
]

# Fast lookup by tool name
DEMO_BY_TOOL: dict[str, dict] = {s["tool"]: s for s in DEMO_SCENARIOS}
# Fast lookup by demo id
DEMO_BY_ID: dict[str, dict] = {s["id"]: s for s in DEMO_SCENARIOS}
