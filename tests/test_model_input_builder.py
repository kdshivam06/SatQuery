import json
import shutil
import tempfile
import unittest
from pathlib import Path

from backend.geospatial.model_input_builder import (
    build_combined_s1_s2_model_input,
    build_patch_model_input,
)


REAL_SAMPLE_ROOT = Path("data/raw/real_samples/benv1_14k")
S1_SAMPLE = REAL_SAMPLE_ROOT / "s1" / "S1A_IW_GRDH_1SDV_20170802T163325_34TCR_58_90"
S2_SAMPLE = REAL_SAMPLE_ROOT / "s2" / "S2A_MSIL2A_20170803T094031_58_90"


@unittest.skipUnless(S1_SAMPLE.exists() and S2_SAMPLE.exists(), "benv1_14k sample is not available")
class ModelInputBuilderTests(unittest.TestCase):
    def setUp(self):
        self.tmpdir = Path(tempfile.mkdtemp(prefix="satquery_model_input_test_"))

    def tearDown(self):
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_builds_s1_model_input(self):
        result = build_patch_model_input(S1_SAMPLE, self.tmpdir / "s1.npy", sensor="s1")

        self.assertEqual(result.array_shape, (2, 120, 120))
        self.assertEqual(result.band_order, ["VV", "VH"])
        self.assertTrue(Path(result.model_input_path).exists())
        self.assertTrue(Path(result.metadata_path).exists())

    def test_builds_s2_model_input_with_20m_resampling(self):
        result = build_patch_model_input(S2_SAMPLE, self.tmpdir / "s2.npy", sensor="s2")

        self.assertEqual(result.array_shape, (10, 120, 120))
        self.assertEqual(
            result.band_order,
            ["B02", "B03", "B04", "B05", "B06", "B07", "B08", "B8A", "B11", "B12"],
        )
        metadata = json.loads(Path(result.metadata_path).read_text(encoding="utf-8"))
        self.assertEqual(metadata["resampling"]["source_shapes"][f"{S2_SAMPLE.name}:B05"], [60, 60])
        self.assertEqual(metadata["resampling"]["target_shape"], [120, 120])

    def test_builds_combined_s1_s2_model_input(self):
        result = build_combined_s1_s2_model_input(S1_SAMPLE, S2_SAMPLE, self.tmpdir / "all.npy")

        self.assertEqual(result.array_shape, (12, 120, 120))
        self.assertEqual(result.band_order[:2], ["VV", "VH"])
        self.assertEqual(result.band_order[2:], ["B02", "B03", "B04", "B05", "B06", "B07", "B08", "B8A", "B11", "B12"])


if __name__ == "__main__":
    unittest.main()
