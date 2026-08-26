import unittest
from pathlib import Path

from backend.geospatial.metadata_extractor import read_asset_metadata
from backend.geospatial.modality_detector import detect_modality
from backend.geospatial.patch_folder import discover_band_files


REAL_SAMPLE_ROOT = Path("data/raw/real_samples/benv1_14k")
S1_SAMPLE = REAL_SAMPLE_ROOT / "s1" / "S1A_IW_GRDH_1SDV_20170802T163325_34TCR_58_90"
S2_SAMPLE = REAL_SAMPLE_ROOT / "s2" / "S2A_MSIL2A_20170803T094031_58_90"


@unittest.skipUnless(S1_SAMPLE.exists() and S2_SAMPLE.exists(), "benv1_14k sample is not available")
class PatchFolderTests(unittest.TestCase):
    def test_discovers_real_s1_patch_bands(self):
        bands = discover_band_files(S1_SAMPLE)

        self.assertEqual(set(bands), {"VV", "VH"})

    def test_discovers_real_s2_patch_bands(self):
        bands = discover_band_files(S2_SAMPLE)

        self.assertIn("B02", bands)
        self.assertIn("B03", bands)
        self.assertIn("B04", bands)
        self.assertIn("B08", bands)
        self.assertIn("B8A", bands)
        self.assertIn("B11", bands)
        self.assertIn("B12", bands)

    def test_reads_real_patch_folder_metadata_and_modality(self):
        s1_metadata = read_asset_metadata(S1_SAMPLE)
        s2_metadata = read_asset_metadata(S2_SAMPLE)

        self.assertEqual(s1_metadata.format.value, "patch_folder")
        self.assertEqual(s1_metadata.band_count, 2)
        self.assertEqual(detect_modality(s1_metadata).modality.value, "sar")

        self.assertEqual(s2_metadata.format.value, "patch_folder")
        self.assertEqual(s2_metadata.band_count, 12)
        self.assertEqual(detect_modality(s2_metadata).modality.value, "multispectral")


if __name__ == "__main__":
    unittest.main()
