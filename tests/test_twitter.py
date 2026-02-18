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
        assert result["success"] is True
        assert result["ids"] == ["123"]
        assert result["urls"] == ["https://x.com/i/web/status/123"]

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
        assert result["success"] is True
        assert result["ids"] == ["1", "2"]
        assert result["urls"] == [
            "https://x.com/i/web/status/1",
            "https://x.com/i/web/status/2",
        ]
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

    @patch("platforms.twitter.tweepy")
    def test_post_returns_rate_limit_snapshot(self, mock_tweepy):
        mock_client = MagicMock()
        mock_client.create_tweet.return_value = MagicMock(
            data={"id": "123"},
            headers={
                "x-rate-limit-limit": "200",
                "x-rate-limit-remaining": "199",
                "x-rate-limit-reset": "4102444800",
            },
        )
        mock_tweepy.Client.return_value = mock_client

        platform = TwitterPlatform(
            api_key="k", api_secret="s",
            access_token="t", access_token_secret="ts"
        )
        result = platform.post(["Hello world."])
        assert result["success"] is True
        assert result["rate_limit"]["limit"] == 200
        assert result["rate_limit"]["remaining"] == 199
        assert result["rate_limit"]["reset_epoch"] == 4102444800

    @patch("platforms.twitter.tweepy")
    def test_post_multiple_images_on_first_tweet(self, mock_tweepy):
        mock_client = MagicMock()
        mock_client.create_tweet.return_value = MagicMock(data={"id": "123"})
        mock_tweepy.Client.return_value = mock_client

        platform = TwitterPlatform(
            api_key="k", api_secret="s",
            access_token="t", access_token_secret="ts"
        )
        with patch.object(platform, "_upload_image", side_effect=[11, 22, 33]):
            result = platform.post(
                ["Hello world."],
                image_bytes_list=[b"1", b"2", b"3"],
            )

        assert result["success"] is True
        call = mock_client.create_tweet.call_args
        assert call.kwargs.get("media_ids") == [11, 22, 33]

    @patch("platforms.twitter.tweepy")
    def test_post_images_by_part(self, mock_tweepy):
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
        with patch.object(platform, "_upload_image", side_effect=[101, 202]):
            result = platform.post(
                ["Part 1", "Part 2"],
                images_by_part=[[b"a"], [b"b"]],
                mode="manual",
            )

        assert result["success"] is True
        calls = mock_client.create_tweet.call_args_list
        assert calls[0].kwargs.get("media_ids") == [101]
        assert calls[1].kwargs.get("media_ids") == [202]
