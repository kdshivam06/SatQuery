import unittest

from backend.geospatial.modality_detector import detect_modality
from backend.geospatial.models import AssetFormat, AssetMetadata, Modality


class ModalityDetectorTests(unittest.TestCase):
    def test_detects_sentinel_1_from_filename(self):
        metadata = AssetMetadata(
            path="S1_patch_VV_VH.tif",
            filename="S1_patch_VV_VH.tif",
            format=AssetFormat.TIFF,
            band_count=2,
        )

        result = detect_modality(metadata)

        self.assertEqual(result.modality, Modality.SAR)
        self.assertGreaterEqual(result.confidence, 0.65)

    def test_detects_multispectral_from_many_bands(self):
        metadata = AssetMetadata(
            path="tile.tif",
            filename="tile.tif",
            format=AssetFormat.TIFF,
            band_count=13,
        )

        result = detect_modality(metadata)

        self.assertEqual(result.modality, Modality.MULTISPECTRAL)

    def test_detects_rgb_optical_from_three_bands(self):
        metadata = AssetMetadata(
            path="cartosat_rgb.png",
            filename="cartosat_rgb.png",
            format=AssetFormat.PNG,
            band_count=3,
        )

        result = detect_modality(metadata)

        self.assertEqual(result.modality, Modality.OPTICAL)


if __name__ == "__main__":
    unittest.main()
