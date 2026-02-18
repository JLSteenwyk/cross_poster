"""LinkedIn platform module for cross-posting.

Uses the LinkedIn Posts API (replaces deprecated UGC Posts API).
OAuth2 3-legged flow for authentication.
"""

import os
import webbrowser
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
from typing import Optional
from pathlib import Path

import requests
from core.text_normalizer import normalize_linkedin_text

# LinkedIn API version in YYYYMM format
LINKEDIN_API_VERSION = "202601"


class LinkedInPlatform:
    """Post to LinkedIn via the Posts API."""

    REDIRECT_URI = "http://localhost:5001/callback/linkedin"
    OAUTH_PORT = 5001
    REQUEST_TIMEOUT = (5, 20)

    def __init__(
        self,
        client_id: Optional[str] = None,
        client_secret: Optional[str] = None,
        access_token: Optional[str] = None,
        refresh_token: Optional[str] = None,
    ):
        self.client_id = client_id or os.environ.get("LINKEDIN_CLIENT_ID")
        self.client_secret = client_secret or os.environ.get("LINKEDIN_CLIENT_SECRET")
        self.access_token = access_token or os.environ.get("LINKEDIN_ACCESS_TOKEN")
        self.refresh_token = refresh_token or os.environ.get("LINKEDIN_REFRESH_TOKEN")

        if not self.client_id or not self.client_secret:
            raise ValueError(
                "LinkedIn credentials required. Set LINKEDIN_CLIENT_ID and "
                "LINKEDIN_CLIENT_SECRET in .env"
            )

        self._person_id = None

    def _api_headers(self) -> dict:
        """Return standard headers for LinkedIn REST API calls."""
        return {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json",
            "X-Restli-Protocol-Version": "2.0.0",
            "Linkedin-Version": LINKEDIN_API_VERSION,
        }

    def _get_person_id(self) -> str:
        """Fetch the authenticated user's person ID."""
        if self._person_id:
            return self._person_id

        resp = requests.get(
            "https://api.linkedin.com/v2/userinfo",
            headers={"Authorization": f"Bearer {self.access_token}"},
            timeout=self.REQUEST_TIMEOUT,
        )
        resp.raise_for_status()
        self._person_id = resp.json()["sub"]
        return self._person_id

    def _upload_image(self, image_bytes: bytes) -> Optional[str]:
        """Upload an image to LinkedIn using the Images API.

        Returns image URN (urn:li:image:...) or None.
        """
        try:
            person_id = self._get_person_id()

            # Step 1: Initialize upload
            init_resp = requests.post(
                "https://api.linkedin.com/rest/images?action=initializeUpload",
                headers=self._api_headers(),
                json={
                    "initializeUploadRequest": {
                        "owner": f"urn:li:person:{person_id}",
                    }
                },
                timeout=self.REQUEST_TIMEOUT,
            )
            init_resp.raise_for_status()

            upload_data = init_resp.json()["value"]
            upload_url = upload_data["uploadUrl"]
            image_urn = upload_data["image"]

            # Step 2: Upload the binary image
            upload_resp = requests.put(
                upload_url,
                headers={"Authorization": f"Bearer {self.access_token}"},
                data=image_bytes,
                timeout=self.REQUEST_TIMEOUT,
            )
            upload_resp.raise_for_status()

            return image_urn

        except Exception:
            return None

    def authorize(self) -> bool:
        """Run the OAuth2 authorization flow. Opens browser, captures callback."""
        auth_code = None

        class CallbackHandler(BaseHTTPRequestHandler):
            def do_GET(self):
                nonlocal auth_code
                query = parse_qs(urlparse(self.path).query)
                auth_code = query.get("code", [None])[0]
                self.send_response(200)
                self.send_header("Content-Type", "text/html")
                self.end_headers()
                self.wfile.write(b"<h1>Authorization complete. You can close this tab.</h1>")

            def log_message(self, format, *args):
                pass

        auth_url = (
            f"https://www.linkedin.com/oauth/v2/authorization"
            f"?response_type=code"
            f"&client_id={self.client_id}"
            f"&redirect_uri={self.REDIRECT_URI}"
            f"&scope=openid%20profile%20email%20w_member_social"
        )

        server = HTTPServer(("localhost", self.OAUTH_PORT), CallbackHandler)
        webbrowser.open(auth_url)

        server.timeout = 120
        server.handle_request()
        server.server_close()

        if not auth_code:
            return False

        resp = requests.post(
            "https://www.linkedin.com/oauth/v2/accessToken",
            data={
                "grant_type": "authorization_code",
                "code": auth_code,
                "client_id": self.client_id,
                "client_secret": self.client_secret,
                "redirect_uri": self.REDIRECT_URI,
            },
            timeout=self.REQUEST_TIMEOUT,
        )

        if resp.status_code != 200:
            return False

        tokens = resp.json()
        self.access_token = tokens["access_token"]
        self.refresh_token = tokens.get("refresh_token", "")

        self._save_tokens()
        return True

    def _save_tokens(self):
        """Save access and refresh tokens back to .env file."""
        env_path = Path(__file__).parent.parent / ".env"
        if not env_path.exists():
            return

        content = env_path.read_text()
        lines = content.split("\n")
        new_lines = []
        for line in lines:
            if line.startswith("LINKEDIN_ACCESS_TOKEN="):
                new_lines.append(f"LINKEDIN_ACCESS_TOKEN={self.access_token}")
            elif line.startswith("LINKEDIN_REFRESH_TOKEN="):
                new_lines.append(f"LINKEDIN_REFRESH_TOKEN={self.refresh_token}")
            else:
                new_lines.append(line)
        env_path.write_text("\n".join(new_lines))

    def refresh_access_token(self) -> bool:
        """Refresh the access token using the refresh token."""
        if not self.refresh_token:
            return False

        resp = requests.post(
            "https://www.linkedin.com/oauth/v2/accessToken",
            data={
                "grant_type": "refresh_token",
                "refresh_token": self.refresh_token,
                "client_id": self.client_id,
                "client_secret": self.client_secret,
            },
            timeout=self.REQUEST_TIMEOUT,
        )

        if resp.status_code != 200:
            return False

        tokens = resp.json()
        self.access_token = tokens["access_token"]
        self.refresh_token = tokens.get("refresh_token", self.refresh_token)
        self._save_tokens()
        return True

    def post(
        self,
        parts: list[str],
        image_bytes: Optional[bytes] = None,
        image_bytes_list: Optional[list[bytes]] = None,
        images_by_part: Optional[list[list[bytes]]] = None,
        mode: str = "auto",
    ) -> dict:
        """Post to LinkedIn using the Posts API. Parts are joined (no thread support)."""
        full_text = normalize_linkedin_text("\n\n".join(parts))
        _ = mode  # reserved for result metadata and debugging
        images = image_bytes_list if image_bytes_list is not None else (
            [image_bytes] if image_bytes else []
        )
        if images_by_part is not None:
            images = [img for group in images_by_part for img in group]

        if not self.access_token:
            return {"success": False, "error": "No access token. Run OAuth flow first."}

        try:
            person_id = self._get_person_id()

            payload = {
                "author": f"urn:li:person:{person_id}",
                "commentary": full_text,
                "visibility": "PUBLIC",
                "distribution": {
                    "feedDistribution": "MAIN_FEED",
                    "targetEntities": [],
                    "thirdPartyDistributionChannels": [],
                },
                "lifecycleState": "PUBLISHED",
                "isReshareDisabledByAuthor": False,
            }

            if images:
                image_urn = self._upload_image(images[0])
                if image_urn:
                    payload["content"] = {
                        "media": {
                            "id": image_urn,
                        }
                    }

            resp = requests.post(
                "https://api.linkedin.com/rest/posts",
                headers=self._api_headers(),
                json=payload,
                timeout=self.REQUEST_TIMEOUT,
            )

            if resp.status_code == 201:
                post_id = resp.headers.get("x-restli-id", "")
                post_url = (
                    f"https://www.linkedin.com/feed/update/{post_id}/"
                    if post_id else None
                )
                result = {"success": True}
                if post_id:
                    result["id"] = post_id
                if post_url:
                    result["urls"] = [post_url]
                return result
            else:
                return {"success": False, "error": f"Post failed (status {resp.status_code}): {resp.text}"}

        except Exception as e:
            return {"success": False, "error": str(e)}
