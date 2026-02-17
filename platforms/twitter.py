"""Twitter/X platform module for cross-posting."""

import os
import tempfile
from typing import Optional

import tweepy


class TwitterPlatform:
    """Post to Twitter/X with thread and image support."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        api_secret: Optional[str] = None,
        access_token: Optional[str] = None,
        access_token_secret: Optional[str] = None,
    ):
        self.api_key = api_key or os.environ.get("TWITTER_API_KEY")
        self.api_secret = api_secret or os.environ.get("TWITTER_API_SECRET")
        self.access_token = access_token or os.environ.get("TWITTER_ACCESS_TOKEN")
        self.access_token_secret = access_token_secret or os.environ.get("TWITTER_ACCESS_TOKEN_SECRET")

        if not all([self.api_key, self.api_secret, self.access_token, self.access_token_secret]):
            raise ValueError(
                "Twitter credentials required. Set TWITTER_API_KEY, TWITTER_API_SECRET, "
                "TWITTER_ACCESS_TOKEN, and TWITTER_ACCESS_TOKEN_SECRET in .env"
            )

        self.client = tweepy.Client(
            consumer_key=self.api_key,
            consumer_secret=self.api_secret,
            access_token=self.access_token,
            access_token_secret=self.access_token_secret,
        )

        # v1.1 API for media uploads
        auth = tweepy.OAuth1UserHandler(
            self.api_key, self.api_secret,
            self.access_token, self.access_token_secret,
        )
        self.api_v1 = tweepy.API(auth)

    def _upload_image(self, image_bytes: bytes) -> Optional[int]:
        """Upload an image to Twitter. Returns media_id or None."""
        try:
            with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
                tmp.write(image_bytes)
                tmp_path = tmp.name
            media = self.api_v1.media_upload(filename=tmp_path)
            os.unlink(tmp_path)
            return media.media_id
        except Exception:
            return None

    def post(self, parts: list[str], image_bytes: Optional[bytes] = None) -> dict:
        """Post text parts as a tweet or thread.

        Args:
            parts: List of text parts. Single item = single tweet, multiple = thread.
            image_bytes: Optional image to attach to the first tweet.

        Returns:
            Dict with 'success' bool, 'ids' list on success, 'error' string on failure.
        """
        try:
            tweet_ids = []
            previous_id = None

            for i, text in enumerate(parts):
                media_ids = None
                if i == 0 and image_bytes:
                    media_id = self._upload_image(image_bytes)
                    if media_id:
                        media_ids = [media_id]

                response = self.client.create_tweet(
                    text=text,
                    media_ids=media_ids,
                    in_reply_to_tweet_id=previous_id,
                )

                tweet_id = response.data["id"]
                tweet_ids.append(tweet_id)
                previous_id = tweet_id

            urls = [f"https://x.com/i/web/status/{tweet_id}" for tweet_id in tweet_ids]
            return {"success": True, "ids": tweet_ids, "urls": urls}

        except Exception as e:
            return {"success": False, "error": str(e)}
