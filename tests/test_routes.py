"""Tests for Flask web routes."""

import io
import json
from unittest.mock import patch, MagicMock

import pytest

from web.app import create_app


@pytest.fixture
def client():
    app = create_app()
    app.config["TESTING"] = True
    with app.test_client() as c:
        yield c


class TestIndex:
    def test_get_index(self, client):
        resp = client.get("/")
        assert resp.status_code == 200
        assert b"Cross-Poster" in resp.data


class TestPreview:
    def test_preview_single_platform(self, client):
        resp = client.post(
            "/api/preview",
            data=json.dumps({"text": "Hello world", "platforms": ["twitter"]}),
            content_type="application/json",
        )
        assert resp.status_code == 200
        data = resp.get_json()
        assert "twitter" in data
        assert data["twitter"]["parts"] == ["Hello world"]
        assert data["twitter"]["count"] == 11
        assert data["twitter"]["limit"] == 280
        assert data["twitter"]["over"] is False

    def test_preview_multiple_platforms(self, client):
        resp = client.post(
            "/api/preview",
            data=json.dumps({
                "text": "Test post",
                "platforms": ["twitter", "bluesky", "linkedin"],
            }),
            content_type="application/json",
        )
        data = resp.get_json()
        assert "twitter" in data
        assert "bluesky" in data
        assert "linkedin" in data

    def test_preview_over_limit(self, client):
        long_text = "A" * 300
        resp = client.post(
            "/api/preview",
            data=json.dumps({"text": long_text, "platforms": ["twitter"]}),
            content_type="application/json",
        )
        data = resp.get_json()
        assert data["twitter"]["over"] is True

    def test_preview_empty_text(self, client):
        resp = client.post(
            "/api/preview",
            data=json.dumps({"text": "", "platforms": ["twitter"]}),
            content_type="application/json",
        )
        data = resp.get_json()
        assert data["twitter"]["parts"] == [""]

    def test_preview_normalizes_em_dash(self, client):
        resp = client.post(
            "/api/preview",
            data=json.dumps({"text": "A — B", "platforms": ["twitter"]}),
            content_type="application/json",
        )
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["twitter"]["parts"] == ["A -- B"]

    def test_preview_linkedin_neutralizes_asterisk_formatting(self, client):
        resp = client.post(
            "/api/preview",
            data=json.dumps({"text": "i*agent and *bold*", "platforms": ["linkedin"]}),
            content_type="application/json",
        )
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["linkedin"]["parts"] == ["i*\u200bagent and *\u200bbold*\u200b"]

    def test_preview_manual_mode_with_image_refs(self, client):
        resp = client.post(
            "/api/preview",
            data=json.dumps({
                "text": "One [img1]\n---\nTwo [img2]",
                "platforms": ["twitter"],
                "imageCount": 2,
            }),
            content_type="application/json",
        )
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["twitter"]["mode"] == "manual"
        assert data["twitter"]["parts"] == ["One", "Two"]
        assert data["twitter"]["image_refs"] == [[0], [1]]

    @patch("web.routes.LinkedInPlatform", autospec=True)
    def test_post_linkedin_includes_text_after_manual_separator(self, MockLinkedIn, client):
        mock_instance = MockLinkedIn.return_value
        mock_instance.access_token = "tok"
        mock_instance.post.return_value = {"success": True}

        resp = client.post(
            "/api/post",
            data={
                "text": "First section\n---\nSecond section",
                "platforms": "linkedin",
            },
        )
        assert resp.status_code == 200
        args = mock_instance.post.call_args.args
        assert args[0] == ["First section", "Second section"]


class TestPost:
    def test_post_no_text(self, client):
        resp = client.post("/api/post", data={"platforms": "twitter"})
        assert resp.status_code == 400

    def test_post_no_platforms(self, client):
        resp = client.post("/api/post", data={"text": "Hello"})
        assert resp.status_code == 400

    @patch("web.routes.TwitterPlatform", autospec=True)
    def test_post_twitter_success(self, MockTwitter, client):
        mock_instance = MockTwitter.return_value
        mock_instance.post.return_value = {"success": True}

        resp = client.post(
            "/api/post",
            data={"text": "Hello world", "platforms": "twitter"},
        )
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["twitter"]["success"] is True

    @patch("web.routes.BlueskyPlatform", autospec=True)
    def test_post_bluesky_success(self, MockBluesky, client):
        mock_instance = MockBluesky.return_value
        mock_instance.post.return_value = {"success": True}

        resp = client.post(
            "/api/post",
            data={"text": "Hello world", "platforms": "bluesky"},
        )
        data = resp.get_json()
        assert data["bluesky"]["success"] is True

    @patch("web.routes.LinkedInPlatform", autospec=True)
    def test_post_linkedin_no_token(self, MockLinkedIn, client):
        mock_instance = MockLinkedIn.return_value
        mock_instance.access_token = None

        resp = client.post(
            "/api/post",
            data={"text": "Hello world", "platforms": "linkedin"},
        )
        data = resp.get_json()
        assert data["linkedin"]["success"] is False
        assert "Authorize" in data["linkedin"]["error"]

    @patch("web.routes.TwitterPlatform", autospec=True)
    def test_post_platform_exception(self, MockTwitter, client):
        MockTwitter.side_effect = Exception("API down")

        resp = client.post(
            "/api/post",
            data={"text": "Hello world", "platforms": "twitter"},
        )
        data = resp.get_json()
        assert data["twitter"]["success"] is False
        assert "API down" in data["twitter"]["error"]

    @patch("web.routes.TwitterPlatform", autospec=True)
    def test_post_with_image(self, MockTwitter, client):
        mock_instance = MockTwitter.return_value
        mock_instance.post.return_value = {"success": True}

        # Create a minimal valid JPEG
        from PIL import Image
        buf = io.BytesIO()
        img = Image.new("RGB", (10, 10), color="red")
        img.save(buf, format="JPEG")
        buf.seek(0)

        resp = client.post(
            "/api/post",
            data={
                "text": "Hello with image",
                "platforms": "twitter",
                "image": (buf, "test.jpg"),
            },
            content_type="multipart/form-data",
        )
        data = resp.get_json()
        assert data["twitter"]["success"] is True

    @patch("web.routes.TwitterPlatform", autospec=True)
    def test_post_with_multiple_images(self, MockTwitter, client):
        mock_instance = MockTwitter.return_value
        mock_instance.post.return_value = {"success": True}

        from PIL import Image
        img1 = io.BytesIO()
        img2 = io.BytesIO()
        Image.new("RGB", (10, 10), color="red").save(img1, format="JPEG")
        Image.new("RGB", (10, 10), color="blue").save(img2, format="JPEG")
        img1.seek(0)
        img2.seek(0)

        resp = client.post(
            "/api/post",
            data={
                "text": "Hello with images",
                "platforms": "twitter",
                "images": [(img1, "one.jpg"), (img2, "two.jpg")],
            },
            content_type="multipart/form-data",
        )
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["twitter"]["success"] is True

        post_call = mock_instance.post.call_args
        kwargs = post_call.kwargs
        assert "images_by_part" in kwargs
        assert len(kwargs["images_by_part"][0]) == 2

    def test_post_invalid_image(self, client):
        resp = client.post(
            "/api/post",
            data={
                "text": "Hello",
                "platforms": "twitter",
                "image": (io.BytesIO(b"not an image"), "bad.jpg"),
            },
            content_type="multipart/form-data",
        )
        assert resp.status_code == 400
        data = resp.get_json()
        assert "Invalid image" in data["error"]

    @patch("web.routes.TwitterPlatform", autospec=True)
    def test_post_records_twitter_rate_limit_snapshot(self, MockTwitter, client):
        mock_instance = MockTwitter.return_value
        mock_instance.post.return_value = {
            "success": True,
            "ids": ["123"],
            "urls": ["https://x.com/i/web/status/123"],
            "rate_limit": {
                "limit": 200,
                "remaining": 199,
                "reset_epoch": 4102444800,
                "reset_in_seconds": 60,
                "tracked_at_epoch": 4102444740,
            },
        }

        post_resp = client.post(
            "/api/post",
            data={"text": "Hello world", "platforms": "twitter"},
        )
        assert post_resp.status_code == 200

        rl_resp = client.get("/api/rate-limits")
        assert rl_resp.status_code == 200
        data = rl_resp.get_json()
        assert data["twitter"]["limit"] == 200
        assert data["twitter"]["remaining"] == 199


class TestLinkedInOAuth:
    @patch("web.routes.LinkedInPlatform", autospec=True)
    def test_authorize_redirect(self, MockLinkedIn, client):
        mock_instance = MockLinkedIn.return_value
        mock_instance.client_id = "test_id"
        mock_instance.REDIRECT_URI = "http://localhost:5001/callback/linkedin"

        resp = client.get("/api/linkedin/authorize")
        assert resp.status_code == 302
        assert "linkedin.com/oauth/v2/authorization" in resp.headers["Location"]

    def test_linkedin_status(self, client):
        resp = client.get("/api/linkedin/status")
        assert resp.status_code == 200
        data = resp.get_json()
        assert "authorized" in data


class TestEnhance:
    def test_enhance_no_text(self, client):
        resp = client.post(
            "/api/enhance",
            data=json.dumps({"text": ""}),
            content_type="application/json",
        )
        assert resp.status_code == 400
        data = resp.get_json()
        assert "No text provided" in data["error"]

    @patch("web.routes.os.environ.get")
    def test_enhance_missing_api_key(self, mock_get, client):
        def _env_side_effect(key, default=""):
            if key == "OPENAI_API_KEY":
                return ""
            return default

        mock_get.side_effect = _env_side_effect
        resp = client.post(
            "/api/enhance",
            data=json.dumps({"text": "Hello world"}),
            content_type="application/json",
        )
        assert resp.status_code == 400
        data = resp.get_json()
        assert "OPENAI_API_KEY" in data["error"]

    def test_enhance_too_long(self, client):
        resp = client.post(
            "/api/enhance",
            data=json.dumps({"text": "A" * 7000}),
            content_type="application/json",
        )
        assert resp.status_code == 400
        data = resp.get_json()
        assert "Text too long" in data["error"]

    @patch("web.routes._is_enhance_rate_limited")
    def test_enhance_rate_limited(self, mock_rate_limited, client):
        mock_rate_limited.return_value = True
        resp = client.post(
            "/api/enhance",
            data=json.dumps({"text": "Hello world"}),
            content_type="application/json",
        )
        assert resp.status_code == 429
        data = resp.get_json()
        assert "Too many enhancement requests" in data["error"]

    @patch("web.routes.http_requests.post")
    @patch("web.routes.os.environ.get")
    def test_enhance_success(self, mock_env_get, mock_post, client):
        def _env_side_effect(key, default=""):
            if key == "OPENAI_API_KEY":
                return "test-key"
            if key == "OPENAI_MODEL":
                return "gpt-test"
            return default

        mock_env_get.side_effect = _env_side_effect

        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "choices": [
                {
                    "message": {
                        "content": "Refined post copy.",
                    }
                }
            ]
        }
        mock_post.return_value = mock_resp

        resp = client.post(
            "/api/enhance",
            data=json.dumps({"text": "Original post"}),
            content_type="application/json",
        )

        assert resp.status_code == 200
        data = resp.get_json()
        assert data["text"] == "Refined post copy."
