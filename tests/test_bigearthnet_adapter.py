import shutil
import tempfile
import unittest
from pathlib import Path

from backend.modeling.bigearthnet_adapter import prepare_bigearthnet_input


COMBINED_INPUT = Path("runs/benv1_pair_0/model_inputs/s1_s2_v0.2.0.npy")
S2_INPUT = Path("runs/benv1_pair_0/model_inputs/S2A_MSIL2A_20170803T094031_58_90_s2_v0.2.0.npy")


@unittest.skipUnless(COMBINED_INPUT.exists() and S2_INPUT.exists(), "real model input stacks are not available")
class BigEarthNetAdapterTests(unittest.TestCase):
    def setUp(self):
        self.tmpdir = Path(tempfile.mkdtemp(prefix="satquery_adapter_test_"))

    def tearDown(self):
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_prepares_combined_stack_for_batch_model_input(self):
        prepared = prepare_bigearthnet_input(
            COMBINED_INPUT,
            self.tmpdir / "prepared_all.npy",
            sensor="all",
            target_size=224,
        )

        self.assertEqual(prepared.shape, (1, 12, 224, 224))
        self.assertEqual(prepared.band_order[:2], ["VV", "VH"])
        self.assertTrue(Path(prepared.tensor_path).exists())
        self.assertTrue(Path(prepared.metadata_path).exists())

    def test_prepares_s2_stack_for_batch_model_input(self):
        prepared = prepare_bigearthnet_input(
            S2_INPUT,
            self.tmpdir / "prepared_s2.npy",
            sensor="s2",
            target_size=224,
        )

        self.assertEqual(prepared.shape, (1, 10, 224, 224))
        self.assertEqual(prepared.band_order, ["B02", "B03", "B04", "B05", "B06", "B07", "B08", "B8A", "B11", "B12"])


if __name__ == "__main__":
    unittest.main()
