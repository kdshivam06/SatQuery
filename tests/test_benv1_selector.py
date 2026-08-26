import unittest
from pathlib import Path

from backend.geospatial.benv1_selector import list_benv1_pairs, select_benv1_pair


REAL_SAMPLE_ROOT = Path("data/raw/real_samples/benv1_14k")


@unittest.skipUnless(REAL_SAMPLE_ROOT.exists(), "benv1_14k sample is not available")
class Benv1SelectorTests(unittest.TestCase):
    def test_selects_first_pair_by_index(self):
        pair = select_benv1_pair(REAL_SAMPLE_ROOT, index=0)

        self.assertTrue(pair.exists)
        self.assertEqual(pair.s2_id, "S2A_MSIL2A_20170803T094031_58_90")
        self.assertEqual(pair.s1_id, "S1A_IW_GRDH_1SDV_20170802T163325_34TCR_58_90")
        self.assertIn("Discontinuous urban fabric", pair.s2_labels)

    def test_selects_pair_by_s2_id(self):
        pair = select_benv1_pair(
            REAL_SAMPLE_ROOT,
            s2_id="S2A_MSIL2A_20170803T094031_58_90",
        )

        self.assertTrue(pair.exists)
        self.assertTrue(pair.s1_path.endswith(pair.s1_id))

    def test_lists_pairs(self):
        pairs = list_benv1_pairs(REAL_SAMPLE_ROOT, limit=2)

        self.assertEqual(len(pairs), 2)
        self.assertTrue(all(pair.exists for pair in pairs))


if __name__ == "__main__":
    unittest.main()
