import unittest

from backend.geospatial.alignment_checker import check_alignment
from backend.geospatial.models import AssetFormat, AssetMetadata, RasterBounds, RasterTransform


def asset(name, crs="EPSG:4326", width=256, height=256, bounds=None, transform=None):
    return AssetMetadata(
        path=name,
        filename=name,
        format=AssetFormat.TIFF,
        width=width,
        height=height,
        band_count=3,
        crs=crs,
        bounds=bounds or RasterBounds(0.0, 0.0, 1.0, 1.0),
        transform=transform or RasterTransform((0.01, 0.0, 0.0, 0.0, -0.01, 1.0)),
        resolution=(0.01, 0.01),
    )


class AlignmentCheckerTests(unittest.TestCase):
    def test_compatible_when_grid_matches(self):
        result = check_alignment(asset("a.tif"), asset("b.tif"))

        self.assertTrue(result.compatible)
        self.assertEqual(result.score, 1.0)
        self.assertEqual(result.issues, [])

    def test_incompatible_when_crs_missing(self):
        result = check_alignment(asset("a.tif", crs=None), asset("b.tif"))

        self.assertFalse(result.compatible)
        self.assertTrue(any(issue.field == "crs" for issue in result.issues))

    def test_dimension_mismatch_warns_and_lowers_score(self):
        result = check_alignment(asset("a.tif"), asset("b.tif", width=512))

        self.assertFalse(result.compatible)
        self.assertTrue(any(issue.field == "dimensions" for issue in result.issues))


if __name__ == "__main__":
    unittest.main()
