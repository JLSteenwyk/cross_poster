"""Twitter/X platform module for cross-posting."""

import os
import tempfile
import time
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

    @staticmethod
    def _extract_rate_limit(headers) -> Optional[dict]:
        """Extract Twitter rate-limit metadata from response headers."""
        if not headers:
            return None

        # Requests headers are case-insensitive, but normalize defensively.
        normalized = {str(k).lower(): v for k, v in dict(headers).items()}
        raw_limit = normalized.get("x-rate-limit-limit")
        raw_remaining = normalized.get("x-rate-limit-remaining")
        raw_reset = normalized.get("x-rate-limit-reset")

        if raw_limit is None and raw_remaining is None and raw_reset is None:
            return None

        def _to_int(value):
            try:
                return int(value) if value is not None else None
            except (TypeError, ValueError):
                return None

        limit = _to_int(raw_limit)
        remaining = _to_int(raw_remaining)
        reset_epoch = _to_int(raw_reset)
        now = int(time.time())
        reset_in_seconds = max(0, reset_epoch - now) if reset_epoch is not None else None

        return {
            "limit": limit,
            "remaining": remaining,
            "reset_epoch": reset_epoch,
            "reset_in_seconds": reset_in_seconds,
            "tracked_at_epoch": now,
        }

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

    def post(
        self,
        parts: list[str],
        image_bytes: Optional[bytes] = None,
        image_bytes_list: Optional[list[bytes]] = None,
        images_by_part: Optional[list[list[bytes]]] = None,
        mode: str = "auto",
    ) -> dict:
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
            rate_limit = None

            _ = mode  # reserved for result metadata and debugging
            images = image_bytes_list if image_bytes_list is not None else (
                [image_bytes] if image_bytes else []
            )

            for i, text in enumerate(parts):
                media_ids = None
                part_images = None
                if images_by_part is not None and i < len(images_by_part):
                    part_images = images_by_part[i]
                elif i == 0:
                    part_images = images

                if part_images:
                    uploaded_ids = []
                    for image_data in part_images[:4]:
                        media_id = self._upload_image(image_data)
                        if media_id:
                            uploaded_ids.append(media_id)
                    if uploaded_ids:
                        media_ids = uploaded_ids

                response = self.client.create_tweet(
                    text=text,
                    media_ids=media_ids,
                    in_reply_to_tweet_id=previous_id,
                )
                response_rate_limit = self._extract_rate_limit(getattr(response, "headers", None))
                if response_rate_limit:
                    rate_limit = response_rate_limit

                tweet_id = response.data["id"]
                tweet_ids.append(tweet_id)
                previous_id = tweet_id

            urls = [f"https://x.com/i/web/status/{tweet_id}" for tweet_id in tweet_ids]
            return {
                "success": True,
                "ids": tweet_ids,
                "urls": urls,
                "rate_limit": rate_limit,
            }

        except Exception as e:
            error_rate_limit = self._extract_rate_limit(
                getattr(getattr(e, "response", None), "headers", None)
            )
            return {"success": False, "error": str(e), "rate_limit": error_rate_limit}
