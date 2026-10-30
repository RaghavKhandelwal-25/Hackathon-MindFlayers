"""Integration tests for FinGuide FastAPI endpoints.

Tests:
1. GET /api/health returns index stats and model configuration.
2. POST /api/chat with valid question returns reply and structured sources.
3. POST /api/chat with empty question returns HTTP 400.
4. CORS headers are correctly configured.
"""

from __future__ import annotations

import unittest
from pathlib import Path
import sys

BASE_DIR = Path(__file__).resolve().parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from fastapi.testclient import TestClient
from api import app, get_pipeline


class TestFastAPIIntegration(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)

    def test_root_endpoint(self):
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("message", data)
        self.assertIn("health_url", data)

    def test_health_endpoint(self):
        response = self.client.get("/api/health")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["status"], "ok")
        self.assertIn("index_ready", data)
        self.assertIn("total_chunks", data)
        self.assertIn("documents", data)
        self.assertIn("groq_model", data)
        self.assertIn("embedding_model", data)
        self.assertTrue(data["index_ready"], "FAISS index should be ready")
        self.assertGreater(data["total_chunks"], 0, "Chunks should be indexed")

    def test_chat_endpoint_empty_message(self):
        response = self.client.post("/api/chat", json={"message": "   "})
        self.assertEqual(response.status_code, 400)

    def test_chat_endpoint_cors_headers(self):
        headers = {
            "Origin": "http://localhost:5173",
            "Access-Control-Request-Method": "POST",
        }
        response = self.client.options("/api/chat", headers=headers)
        self.assertIn(response.status_code, (200, 204))
        self.assertIn("access-control-allow-origin", response.headers)
        self.assertEqual(response.headers["access-control-allow-origin"], "http://localhost:5173")

    def test_chat_endpoint_live_question(self):
        payload = {
            "message": "What is compound interest and why does it matter?",
            "history": [],
            "top_k": 3,
        }
        response = self.client.post("/api/chat", json=payload)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("reply", data)
        self.assertIn("sources", data)
        self.assertIsInstance(data["sources"], list)
        self.assertTrue(len(data["reply"]) > 20, "Reply should be non-trivial")
        print("\n[test_chat_endpoint_live_question] Live Response:")
        print(f"Reply Preview: {data['reply'][:150]}...")
        print(f"Sources Count: {len(data['sources'])}")
        for s in data["sources"]:
            print(f" - [{s.get('type')}] {s.get('title')} (Page: {s.get('page')}, URL: {s.get('url')})")


if __name__ == "__main__":
    unittest.main()
