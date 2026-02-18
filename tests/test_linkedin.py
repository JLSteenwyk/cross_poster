"""Tests for the LinkedIn platform module."""

from unittest.mock import MagicMock, patch, mock_open
import pytest
from platforms.linkedin import LinkedInPlatform


class TestLinkedInPlatform:
    def test_init_missing_credentials_raises(self):
        with patch.dict("os.environ", {}, clear=True):
            with pytest.raises(ValueError, match="LinkedIn credentials required"):
                LinkedInPlatform()

    @patch("platforms.linkedin.requests")
    def test_post_single(self, mock_requests):
        mock_userinfo_resp = MagicMock()
        mock_userinfo_resp.status_code = 200
        mock_userinfo_resp.json.return_value = {"sub": "abc123"}

        mock_post_resp = MagicMock()
        mock_post_resp.status_code = 201
        mock_post_resp.headers = {"x-restli-id": "urn:li:share:123456"}

        mock_requests.get.return_value = mock_userinfo_resp
        mock_requests.post.return_value = mock_post_resp

        platform = LinkedInPlatform(
            client_id="cid", client_secret="csec",
            access_token="tok", refresh_token="rtok"
        )
        result = platform.post(["Hello LinkedIn!"])

        assert result["success"] is True
        assert result["urls"] == ["https://www.linkedin.com/feed/update/urn:li:share:123456/"]

    @patch("platforms.linkedin.requests")
    def test_post_joins_parts(self, mock_requests):
        """LinkedIn doesn't support threads, so parts should be joined."""
        mock_userinfo_resp = MagicMock()
        mock_userinfo_resp.status_code = 200
        mock_userinfo_resp.json.return_value = {"sub": "abc123"}

        mock_post_resp = MagicMock()
        mock_post_resp.status_code = 201
        mock_post_resp.headers = {}

        mock_requests.get.return_value = mock_userinfo_resp
        mock_requests.post.return_value = mock_post_resp

        platform = LinkedInPlatform(
            client_id="cid", client_secret="csec",
            access_token="tok", refresh_token="rtok"
        )
        result = platform.post(["Part 1.", "Part 2."])

        assert result["success"] is True
        call_args = mock_requests.post.call_args
        body = call_args.kwargs.get("json") or call_args[1].get("json")
        assert "Part 1." in body["commentary"]
        assert "Part 2." in body["commentary"]

    @patch("platforms.linkedin.requests")
    def test_post_normalizes_dashes_and_asterisks(self, mock_requests):
        mock_userinfo_resp = MagicMock()
        mock_userinfo_resp.status_code = 200
        mock_userinfo_resp.json.return_value = {"sub": "abc123"}

        mock_post_resp = MagicMock()
        mock_post_resp.status_code = 201
        mock_post_resp.headers = {}

        mock_requests.get.return_value = mock_userinfo_resp
        mock_requests.post.return_value = mock_post_resp

        platform = LinkedInPlatform(
            client_id="cid", client_secret="csec",
            access_token="tok", refresh_token="rtok"
        )
        result = platform.post(["A — B and i*agent and *bold*"])

        assert result["success"] is True
        call_args = mock_requests.post.call_args
        body = call_args.kwargs.get("json") or call_args[1].get("json")
        assert "A -- B" in body["commentary"]
        assert "i*\u200bagent" in body["commentary"]
        assert "*\u200bbold*\u200b" in body["commentary"]

    @patch("platforms.linkedin.requests")
    def test_post_failure(self, mock_requests):
        mock_userinfo_resp = MagicMock()
        mock_userinfo_resp.status_code = 200
        mock_userinfo_resp.json.return_value = {"sub": "abc123"}

        mock_post_resp = MagicMock()
        mock_post_resp.status_code = 403
        mock_post_resp.text = "Forbidden"

        mock_requests.get.return_value = mock_userinfo_resp
        mock_requests.post.return_value = mock_post_resp

        platform = LinkedInPlatform(
            client_id="cid", client_secret="csec",
            access_token="tok", refresh_token="rtok"
        )
        result = platform.post(["Hello."])

        assert result["success"] is False

    @patch("platforms.linkedin.requests")
    def test_post_uses_first_image_when_multiple_supplied(self, mock_requests):
        mock_userinfo_resp = MagicMock()
        mock_userinfo_resp.status_code = 200
        mock_userinfo_resp.json.return_value = {"sub": "abc123"}

        mock_post_resp = MagicMock()
        mock_post_resp.status_code = 201
        mock_post_resp.headers = {}

        mock_requests.get.return_value = mock_userinfo_resp
        mock_requests.post.return_value = mock_post_resp

        platform = LinkedInPlatform(
            client_id="cid", client_secret="csec",
            access_token="tok", refresh_token="rtok"
        )
        with patch.object(platform, "_upload_image", return_value="urn:li:image:123") as mock_upload:
            result = platform.post(["Hello."], image_bytes_list=[b"first", b"second"])

        assert result["success"] is True
        mock_upload.assert_called_once_with(b"first")
