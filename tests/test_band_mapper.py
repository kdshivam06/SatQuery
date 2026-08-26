import unittest

from backend.geospatial.band_mapper import (
    get_bigearthnet_pretrained_band_order,
    plan_available_model_bands,
)
from backend.geospatial.models import AssetFormat, AssetMetadata, BandInfo


class BandMapperTests(unittest.TestCase):
    def test_bigearthnet_v020_s1_order(self):
        self.assertEqual(get_bigearthnet_pretrained_band_order("s1"), ("VV", "VH"))

    def test_bigearthnet_v020_s2_order(self):
        self.assertEqual(
            get_bigearthnet_pretrained_band_order("s2"),
            ("B02", "B03", "B04", "B05", "B06", "B07", "B08", "B8A", "B11", "B12"),
        )

    def test_bigearthnet_v011_all_order_kept_for_old_models(self):
        self.assertEqual(
            get_bigearthnet_pretrained_band_order("all", model_version="v0.1.1"),
            ("B02", "B03", "B04", "B08", "B05", "B06", "B07", "B11", "B12", "B8A", "VH", "VV"),
        )

    def test_plans_available_bands_from_descriptions(self):
        metadata = AssetMetadata(
            path="patch.tif",
            filename="patch.tif",
            format=AssetFormat.TIFF,
            band_count=4,
            bands=[
                BandInfo(index=1, description="B02 blue"),
                BandInfo(index=2, description="B03 green"),
                BandInfo(index=3, description="B04 red"),
                BandInfo(index=4, description="B08 nir"),
            ],
        )

        plan = plan_available_model_bands(metadata, ("B04", "B03", "B02", "B08"))

        self.assertTrue(plan["complete"])
        self.assertEqual(
            plan["mapped"],
            [
                {"band": "B04", "index": 3},
                {"band": "B03", "index": 2},
                {"band": "B02", "index": 1},
                {"band": "B08", "index": 4},
            ],
        )


if __name__ == "__main__":
    unittest.main()
