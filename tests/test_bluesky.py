"""Tests for the BlueSky platform module."""

from unittest.mock import MagicMock, patch, PropertyMock
import pytest
from platforms.bluesky import BlueskyPlatform


class TestBlueskyPlatform:
    def test_init_missing_credentials_raises(self):
        with patch.dict("os.environ", {}, clear=True):
            with pytest.raises(ValueError, match="Bluesky credentials required"):
                BlueskyPlatform()

    @patch("platforms.bluesky.Client")
    def test_post_single(self, mock_client_cls):
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.uri = "at://did:plc:xxx/app.bsky.feed.post/123"
        mock_client.send_post.return_value = mock_response
        mock_client_cls.return_value = mock_client

        platform = BlueskyPlatform(username="test.bsky.social", password="pass")
        result = platform.post(["Hello world."])

        assert result["success"] is True
        assert len(result["uris"]) == 1
        assert result["urls"] == ["https://bsky.app/profile/did:plc:xxx/post/123"]
        mock_client.login.assert_called_once()

    @patch("platforms.bluesky.models")
    @patch("platforms.bluesky.Client")
    def test_post_thread(self, mock_client_cls, mock_models):
        mock_client = MagicMock()
        responses = [
            MagicMock(uri=f"at://did:plc:xxx/app.bsky.feed.post/{i}")
            for i in range(2)
        ]
        mock_client.send_post.side_effect = responses
        mock_models.create_strong_ref.return_value = MagicMock()
        mock_client_cls.return_value = mock_client

        platform = BlueskyPlatform(username="test.bsky.social", password="pass")
        result = platform.post(["Part 1.", "Part 2."])

        assert result["success"] is True
        assert len(result["uris"]) == 2
        assert result["urls"] == [
            "https://bsky.app/profile/did:plc:xxx/post/0",
            "https://bsky.app/profile/did:plc:xxx/post/1",
        ]

    @patch("platforms.bluesky.Client")
    def test_post_failure(self, mock_client_cls):
        mock_client = MagicMock()
        mock_client.send_post.side_effect = Exception("Network error")
        mock_client_cls.return_value = mock_client

        platform = BlueskyPlatform(username="test.bsky.social", password="pass")
        result = platform.post(["Hello."])

        assert result["success"] is False
        assert "Network error" in result["error"]
