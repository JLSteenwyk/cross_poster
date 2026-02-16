"""Tests for the Twitter platform module."""

from unittest.mock import MagicMock, patch
import pytest
from platforms.twitter import TwitterPlatform


class TestTwitterPlatform:
    def test_init_missing_credentials_raises(self):
        with patch.dict("os.environ", {}, clear=True):
            with pytest.raises(ValueError, match="Twitter credentials required"):
                TwitterPlatform()

    @patch("platforms.twitter.tweepy")
    def test_post_single(self, mock_tweepy):
        mock_client = MagicMock()
        mock_client.create_tweet.return_value = MagicMock(data={"id": "123"})
        mock_tweepy.Client.return_value = mock_client

        platform = TwitterPlatform(
            api_key="k", api_secret="s",
            access_token="t", access_token_secret="ts"
        )
        result = platform.post(["Hello world."])
        assert result == {"success": True, "ids": ["123"]}

    @patch("platforms.twitter.tweepy")
    def test_post_thread(self, mock_tweepy):
        mock_client = MagicMock()
        mock_client.create_tweet.side_effect = [
            MagicMock(data={"id": "1"}),
            MagicMock(data={"id": "2"}),
        ]
        mock_tweepy.Client.return_value = mock_client

        platform = TwitterPlatform(
            api_key="k", api_secret="s",
            access_token="t", access_token_secret="ts"
        )
        result = platform.post(["Part 1.", "Part 2."])
        assert result == {"success": True, "ids": ["1", "2"]}
        # Second tweet should reply to first
        calls = mock_client.create_tweet.call_args_list
        assert calls[1].kwargs.get("in_reply_to_tweet_id") == "1"

    @patch("platforms.twitter.tweepy")
    def test_post_failure(self, mock_tweepy):
        mock_client = MagicMock()
        mock_client.create_tweet.side_effect = Exception("Rate limit")
        mock_tweepy.Client.return_value = mock_client

        platform = TwitterPlatform(
            api_key="k", api_secret="s",
            access_token="t", access_token_secret="ts"
        )
        result = platform.post(["Hello."])
        assert result["success"] is False
        assert "Rate limit" in result["error"]
