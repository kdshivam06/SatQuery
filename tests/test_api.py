import unittest
from pathlib import Path

from fastapi.testclient import TestClient

from backend.main import app


REAL_SAMPLE_ROOT = Path("data/raw/real_samples/benv1_14k")


class ApiTests(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)

    def test_health(self):
        response = self.client.get("/health")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "ok")

    @unittest.skipUnless(REAL_SAMPLE_ROOT.exists(), "benv1_14k sample is not available")
    def test_analyze_benv1_cross_modal(self):
        response = self.client.post(
            "/api/analyze/benv1",
            json={
                "query": "Use the optical and SAR images together to identify built-up and water-covered regions.",
                "index": 0,
                "generate_pdf": True,
            },
        )

        self.assertEqual(response.status_code, 200)
        run_id = response.json()["run_id"]
        status_response = self.client.get(f"/api/runs/{run_id}")
        state = status_response.json()

        self.assertEqual(status_response.status_code, 200)
        self.assertEqual(state["status"], "completed")
        self.assertIn("SAR and multispectral", state["answer"])
        self.assertGreater(state["confidence"], 0.0)
        self.assertTrue(state["visual_outputs"])
        self.assertTrue(state["trace"])


if __name__ == "__main__":
    unittest.main()
