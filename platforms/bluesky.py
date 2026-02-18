"""BlueSky platform module for cross-posting."""

import os
from typing import Optional

from atproto import Client, models


class BlueskyPlatform:
    """Post to BlueSky with thread and image support."""

    def __init__(self, username: Optional[str] = None, password: Optional[str] = None):
        self.username = username or os.environ.get("BLUESKY_USERNAME")
        self.password = password or os.environ.get("BLUESKY_PASSWORD")

        if not self.username or not self.password:
            raise ValueError(
                "Bluesky credentials required. Set BLUESKY_USERNAME and "
                "BLUESKY_PASSWORD in .env"
            )

        self.client = Client()
        self._logged_in = False

    def _ensure_login(self):
        if not self._logged_in:
            self.client.login(self.username, self.password)
            self._logged_in = True

    def _upload_image(self, image_bytes: bytes) -> Optional[models.AppBskyEmbedImages.Image]:
        """Upload an image to BlueSky. Returns Image model or None."""
        try:
            upload = self.client.upload_blob(image_bytes)
            return models.AppBskyEmbedImages.Image(
                alt="Attached image",
                image=upload.blob,
            )
        except Exception:
            return None

    @staticmethod
    def _uri_to_web_url(uri: str) -> Optional[str]:
        """Convert at:// URI to public bsky.app URL when possible."""
        try:
            # at://did:plc:xxx/app.bsky.feed.post/abc123
            if not uri.startswith("at://"):
                return None
            parts = uri[5:].split("/")
            if len(parts) < 3:
                return None
            actor = parts[0]
            rkey = parts[-1]
            return f"https://bsky.app/profile/{actor}/post/{rkey}"
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
        """Post text parts as a post or thread.

        Args:
            parts: List of text parts.
            image_bytes: Optional image to attach to the first post.

        Returns:
            Dict with 'success' bool, 'uris' list on success, 'error' string on failure.
        """
        try:
            self._ensure_login()

            uris = []
            parent_ref = None
            root_ref = None

            _ = mode  # reserved for result metadata and debugging
            images = image_bytes_list if image_bytes_list is not None else (
                [image_bytes] if image_bytes else []
            )

            for i, text in enumerate(parts):
                embed = None
                part_images = None
                if images_by_part is not None and i < len(images_by_part):
                    part_images = images_by_part[i]
                elif i == 0:
                    part_images = images

                if part_images:
                    uploaded_images = []
                    for image_data in part_images[:4]:
                        img = self._upload_image(image_data)
                        if img:
                            uploaded_images.append(img)
                    if uploaded_images:
                        embed = models.AppBskyEmbedImages.Main(images=uploaded_images)

                reply = None
                if parent_ref and root_ref:
                    reply = models.AppBskyFeedPost.ReplyRef(
                        parent=parent_ref, root=root_ref
                    )

                response = self.client.send_post(
                    text=text, embed=embed, reply_to=reply
                )

                uris.append(response.uri)

                # Only build refs if there are more parts to thread
                if i < len(parts) - 1:
                    parent_ref = models.create_strong_ref(response)
                    if root_ref is None:
                        root_ref = parent_ref

            urls = [self._uri_to_web_url(uri) for uri in uris]
            urls = [u for u in urls if u]
            return {"success": True, "uris": uris, "urls": urls}

        except Exception as e:
            return {"success": False, "error": str(e)}
