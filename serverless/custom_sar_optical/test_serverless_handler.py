"""Isolated tests for provider-neutral serverless inference handler."""

import os
import tempfile
import unittest
import numpy as np

from serverless.custom_sar_optical.handler import handle_inference
from serverless.custom_sar_optical.loader import load_model_classifiers


class TestServerlessHandler(unittest.TestCase):

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()

        # Create dummy channel-first S1 (2 channels) and S2 (12 channels) numpy stacks
        self.sar_npy = os.path.join(self.temp_dir, "sar_stack.npy")
        self.optical_npy = os.path.join(self.temp_dir, "optical_stack.npy")

        # Member 2 default band specs: S1=2 channels (VV, VH), S2=12 channels
        np.save(self.sar_npy, np.random.rand(2, 120, 120).astype("float32"))
        np.save(self.optical_npy, np.random.rand(12, 120, 120).astype("float32"))

    def test_missing_inputs(self):
        res = handle_inference({})
        self.assertEqual(res["status"], "failed")
        self.assertIn("Missing inputs", res["error"])

    def test_file_not_found(self):
        res = handle_inference({"sar_input_path": "non_existent_file.npy"})
        self.assertEqual(res["status"], "failed")
        self.assertIn("SAR input file not found", res["error"])

    def test_inference_execution(self):
        res = handle_inference({
            "sar_input_path": self.sar_npy,
            "optical_input_path": self.optical_npy,
        })
        self.assertEqual(res["status"], "success")
        self.assertIn("similarity", res)
        self.assertIn("matched", res)
        self.assertIn("confidence", res)
        self.assertGreaterEqual(res["runtime_ms"], 0)

    def test_warm_model_caching(self):
        cls1_a, cls2_a = load_model_classifiers()
        cls1_b, cls2_b = load_model_classifiers()
        self.assertIs(cls1_a, cls1_b)
        self.assertIs(cls2_a, cls2_b)


if __name__ == "__main__":
    unittest.main()
