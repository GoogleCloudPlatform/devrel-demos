import io
import sys
import unittest
from os import environ
from pathlib import Path
from unittest.mock import MagicMock

from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

# Set environment to testing before importing backend modules to bypass same-origin checks
environ["ENVIRONMENT"] = "testing"

from fastapi.testclient import TestClient

from backend.main import app


class TestAISelfieSouvenir(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)

        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_part = MagicMock()

        img = Image.new("RGB", (10, 10), color="black")
        buffered = io.BytesIO()
        img.save(buffered, format="JPEG")
        mock_part.inline_data.data = buffered.getvalue()
        mock_part.inline_data.mime_type = "image/jpeg"

        mock_response.parts = [mock_part]
        mock_client.models.generate_content.return_value = mock_response

        import backend.main

        backend.main.client = mock_client

    def test_root_index(self):
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        self.assertIn("text/html", response.headers["content-type"])

    def test_get_config(self):
        response = self.client.get("/api/config")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("event_title", data)
        self.assertIn("app_name", data)
        self.assertIn("base_image_uri", data)
        self.assertEqual(
            data["base_image_uri"], "gs://lpdemo-misc-pics/krakow_dragon.jpg"
        )
        self.assertIn("privacy_notice", data)

    def test_get_status(self):
        response = self.client.get("/api/status")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("client_initialized", data)
        self.assertIn("prompt", data)
        self.assertIn("is_cloud_run", data)
        self.assertIn("region", data)
        self.assertIn("location", data)
        self.assertIn("show_cloud_run_region", data)
        self.assertIn("environment", data)

    def test_selfie_generation_success_mock(self):
        img_bytes = io.BytesIO()
        Image.new("RGB", (10, 10), color="black").save(img_bytes, format="JPEG")
        img_bytes.seek(0)

        response = self.client.post(
            "/api/selfie",
            files={"image": ("capture.jpg", img_bytes, "image/jpeg")},
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers["content-type"], "image/jpeg")
        self.assertGreater(len(response.content), 0)

    def test_selfie_invalid_image_file(self):
        response = self.client.post(
            "/api/selfie",
            files={
                "image": (
                    "capture.jpg",
                    io.BytesIO(b"not-an-image-file-contents"),
                    "image/jpeg",
                )
            },
        )
        self.assertEqual(response.status_code, 400)
        data = response.json()
        self.assertIn("Invalid image file upload", data["detail"])

    def test_selfie_generation_safety_blocked(self):
        import backend.main

        mock_blocked_resp = MagicMock()
        mock_blocked_resp.parts = None
        mock_candidate = MagicMock()
        mock_candidate.finish_reason = "SAFETY"
        mock_blocked_resp.candidates = [mock_candidate]

        original_client = backend.main.client
        mock_client = MagicMock()
        mock_client.models.generate_content.return_value = mock_blocked_resp
        backend.main.client = mock_client

        try:
            img_bytes = io.BytesIO()
            Image.new("RGB", (10, 10), color="black").save(img_bytes, format="JPEG")
            img_bytes.seek(0)

            response = self.client.post(
                "/api/selfie",
                files={"image": ("capture.jpg", img_bytes, "image/jpeg")},
            )
            self.assertEqual(response.status_code, 400)
            self.assertIn(
                "Gemini API generation stopped or blocked: SAFETY",
                response.json()["detail"],
            )
        finally:
            backend.main.client = original_client

    def test_same_origin_protection(self):
        import backend.config

        original_env = backend.config.ENVIRONMENT
        backend.config.ENVIRONMENT = "production"

        try:
            import backend.main

            backend.main.rate_limit_records.clear()

            img_bytes = io.BytesIO()
            Image.new("RGB", (10, 10), color="black").save(img_bytes, format="JPEG")
            img_bytes.seek(0)

            response = self.client.post(
                "/api/selfie",
                files={"image": ("capture.jpg", img_bytes, "image/jpeg")},
            )
            self.assertEqual(response.status_code, 403)
            self.assertIn(
                "Requests must originate from the same site", response.json()["detail"]
            )

            img_bytes.seek(0)
            response = self.client.post(
                "/api/selfie",
                files={"image": ("capture.jpg", img_bytes, "image/jpeg")},
                headers={"sec-fetch-site": "same-origin"},
            )
            self.assertEqual(response.status_code, 200)

        finally:
            backend.config.ENVIRONMENT = original_env

    def test_rate_limiting_protection(self):
        import backend.config

        original_env = backend.config.ENVIRONMENT
        backend.config.ENVIRONMENT = "production"

        import backend.main

        backend.main.rate_limit_records.clear()

        try:
            for _ in range(backend.config.RATE_LIMIT_MAX):
                img_bytes = io.BytesIO()
                Image.new("RGB", (10, 10), color="black").save(img_bytes, format="JPEG")
                img_bytes.seek(0)

                response = self.client.post(
                    "/api/selfie",
                    files={"image": ("capture.jpg", img_bytes, "image/jpeg")},
                    headers={"sec-fetch-site": "same-origin"},
                )
                self.assertEqual(response.status_code, 200)

            img_bytes = io.BytesIO()
            Image.new("RGB", (10, 10), color="black").save(img_bytes, format="JPEG")
            img_bytes.seek(0)

            response = self.client.post(
                "/api/selfie",
                files={"image": ("capture.jpg", img_bytes, "image/jpeg")},
                headers={"sec-fetch-site": "same-origin"},
            )
            self.assertEqual(response.status_code, 429)
            self.assertIn("Rate limit exceeded", response.json()["detail"])

            # Non-/api/selfie endpoints should not be rate limited
            for _ in range(backend.config.RATE_LIMIT_MAX + 2):
                response = self.client.get(
                    "/api/config",
                    headers={"sec-fetch-site": "same-origin"},
                )
                self.assertEqual(response.status_code, 200)

        finally:
            backend.config.ENVIRONMENT = original_env
            backend.main.rate_limit_records.clear()

    def test_ip_spoofing_prevention(self):
        import backend.main

        mock_req = MagicMock()
        mock_req.headers = {"x-forwarded-for": "1.1.1.1, 2.2.2.2, 203.0.113.50"}
        ip = backend.main.get_client_ip(mock_req)
        self.assertEqual(ip, "203.0.113.50")

    def test_stale_rate_limit_cleanup(self):
        import backend.main

        backend.main.rate_limit_records.clear()
        # Populate with 1005 stale IP entries
        for i in range(1005):
            backend.main.rate_limit_records[f"10.0.0.{i}"] = [1.0]

        self.assertEqual(len(backend.main.rate_limit_records), 1005)
        # Calling is_rate_limited should trigger pruning since len > 1000
        backend.main.is_rate_limited("192.168.1.1")
        # All 1005 stale entries should be pruned, leaving only 192.168.1.1
        self.assertNotIn("10.0.0.0", backend.main.rate_limit_records)
        self.assertIn("192.168.1.1", backend.main.rate_limit_records)
        backend.main.rate_limit_records.clear()

    def test_local_config_file_loading(self):
        import importlib

        import backend.config

        saved_env = environ.get("ENVIRONMENT")
        environ["ENVIRONMENT"] = "local"
        try:
            importlib.reload(backend.config)
            self.assertEqual(backend.config.ENVIRONMENT, "local")
            self.assertEqual(backend.config.EVENT_TITLE, "EuroPython 2026")
        finally:
            if saved_env is not None:
                environ["ENVIRONMENT"] = saved_env
            else:
                environ.pop("ENVIRONMENT", None)
            importlib.reload(backend.config)

    def test_production_config_file_skipping(self):
        import importlib
        from unittest.mock import patch

        import backend.config

        saved_env = environ.get("ENVIRONMENT")
        saved_title = environ.get("EVENT_TITLE")

        environ.pop("ENVIRONMENT", None)
        environ["EVENT_TITLE"] = "Deployed Production Title"

        from pathlib import Path

        with patch.object(Path, "exists", return_value=False):
            try:
                importlib.reload(backend.config)
                self.assertEqual(backend.config.ENVIRONMENT, "production")
                self.assertEqual(
                    backend.config.EVENT_TITLE, "Deployed Production Title"
                )
            finally:
                if saved_env is not None:
                    environ["ENVIRONMENT"] = saved_env
                else:
                    environ.pop("ENVIRONMENT", None)

                if saved_title is not None:
                    environ["EVENT_TITLE"] = saved_title
                else:
                    environ.pop("EVENT_TITLE", None)
                importlib.reload(backend.config)

    def test_missing_config_file_setting_raises_error(self):
        import importlib
        from unittest.mock import patch

        import backend.config

        saved_config = environ.get("CONFIG_FILE")
        environ.pop("CONFIG_FILE", None)

        def mock_load_dotenv(dotenv_path=None, *args, **kwargs):
            environ.pop("CONFIG_FILE", None)

        with patch("dotenv.load_dotenv", side_effect=mock_load_dotenv):
            with self.assertRaises(ValueError) as ctx:
                importlib.reload(backend.config)
            self.assertIn(
                "CONFIG_FILE environment variable is required", str(ctx.exception)
            )

        environ["CONFIG_FILE"] = "../config/europython2026.env"
        importlib.reload(backend.config)

    def test_nonexistent_config_file_raises_error(self):
        import importlib

        import backend.config

        saved_config = environ.get("CONFIG_FILE")
        environ["CONFIG_FILE"] = "non_existent_config.env"

        try:
            with self.assertRaises(FileNotFoundError) as ctx:
                importlib.reload(backend.config)
            self.assertIn(
                "Config file specified by CONFIG_FILE not found", str(ctx.exception)
            )
        finally:
            environ["CONFIG_FILE"] = "../config/europython2026.env"
            importlib.reload(backend.config)

    def test_missing_required_variable_raises_key_error(self):
        import importlib
        from unittest.mock import patch

        import backend.config

        saved_val = environ.get("EVENT_TITLE")
        environ.pop("EVENT_TITLE", None)

        def mock_load_dotenv(*args, **kwargs):
            environ.pop("EVENT_TITLE", None)

        with patch("dotenv.load_dotenv", side_effect=mock_load_dotenv):
            with self.assertRaises(KeyError):
                importlib.reload(backend.config)

        if saved_val is not None:
            environ["EVENT_TITLE"] = saved_val
        importlib.reload(backend.config)


if __name__ == "__main__":
    unittest.main()
