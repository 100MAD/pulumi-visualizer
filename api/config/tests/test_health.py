from unittest.mock import patch

from django.test import SimpleTestCase, TestCase


class LivenessTests(SimpleTestCase):
    def test_live_ok(self):
        response = self.client.get("/health/live/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"status": "ok"})


class ReadinessTests(TestCase):
    def test_ready_ok(self):
        response = self.client.get("/health/ready/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"status": "ok"})

    def test_ready_unavailable_when_db_fails(self):
        with patch("config.health.connection") as conn:
            conn.ensure_connection.side_effect = RuntimeError("db down")
            response = self.client.get("/health/ready/")
        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.json(), {"status": "unavailable"})
