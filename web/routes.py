"""Route handlers for Cross-Poster web app."""

import os
from collections import defaultdict, deque
from pathlib import Path
from threading import Lock
from time import time

import grapheme
import requests as http_requests
from flask import Blueprint, render_template, request, jsonify, redirect

from core.splitter import TWITTER, BLUESKY, LINKEDIN
from core.thread_plan import build_thread_plan
from core.media import validate_image, resize_for_platform
from core.text_normalizer import normalize_common_text, normalize_linkedin_text
from platforms.twitter import TwitterPlatform
from platforms.bluesky import BlueskyPlatform
from platforms.linkedin import LinkedInPlatform

_web_dir = Path(__file__).parent

bp = Blueprint(
    "main",
    __name__,
    template_folder=str(_web_dir / "templates"),
    static_folder=str(_web_dir / "static"),
    static_url_path="/static",
)

PLATFORM_CONFIGS = {
    "twitter": TWITTER,
    "bluesky": BLUESKY,
    "linkedin": LINKEDIN,
}

PLATFORM_DISPLAY = {
    "twitter": "Twitter",
    "bluesky": "BlueSky",
    "linkedin": "LinkedIn",
}

ENHANCE_MAX_CHARS = 6000
ENHANCE_RATE_LIMIT = 20  # requests
ENHANCE_WINDOW_SECONDS = 60  # per minute
_enhance_rate_bucket = defaultdict(deque)
_enhance_rate_lock = Lock()
_platform_rate_limits = {}
_platform_rate_limits_lock = Lock()


def _enhance_text_with_ai(text: str) -> str:
    """Enhance text with OpenAI while preserving intent and platform fit."""
    api_key = os.environ.get("OPENAI_API_KEY", "").strip()
    if not api_key:
        raise ValueError("Missing OPENAI_API_KEY in environment.")

    model = os.environ.get("OPENAI_MODEL", "gpt-4.1-mini").strip() or "gpt-4.1-mini"

    system_prompt = (
        "You are a social media editor. Rewrite user text for a strong social post. "
        "Keep the meaning, facts, and intent. Keep concise, professional, and casual tone "
        "with a slight emphasis on casual warmth. Sound human, not generic AI. "
        "Avoid em dashes and avoid overused AI phrasing. "
        "Use plain punctuation, short sentences, and clean line breaks when useful. "
        "Do not add hashtags unless already present. Do not invent facts. "
        "Return only the revised post text."
    )

    resp = http_requests.post(
        "https://api.openai.com/v1/chat/completions",
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        json={
            "model": model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {
                    "role": "user",
                    "content": (
                        "Rewrite this post text:\n\n"
                        f"{text}"
                    ),
                },
            ],
        },
        timeout=30,
    )

    if resp.status_code != 200:
        raise RuntimeError("Enhancement request failed at provider.")

    data = resp.json()
    choices = data.get("choices", [])
    if not choices:
        raise RuntimeError("Enhancement failed: empty model response.")

    content = choices[0].get("message", {}).get("content", "")
    if not isinstance(content, str) or not content.strip():
        raise RuntimeError("Enhancement failed: no text returned.")

    return content.strip()


def _is_enhance_rate_limited(client_ip: str) -> bool:
    """Simple in-memory rolling-window rate limit for /api/enhance."""
    now = time()
    cutoff = now - ENHANCE_WINDOW_SECONDS

    with _enhance_rate_lock:
        bucket = _enhance_rate_bucket[client_ip]
        while bucket and bucket[0] < cutoff:
            bucket.popleft()

        if len(bucket) >= ENHANCE_RATE_LIMIT:
            return True

        bucket.append(now)
        return False


@bp.route("/")
def index():
    return render_template("index.html")


@bp.route("/api/preview", methods=["POST"])
def preview():
    """Return thread split preview for all requested platforms."""
    data = request.get_json()
    text = data.get("text", "")
    platforms = data.get("platforms", [])
    image_count = int(data.get("imageCount") or 0)

    result = {}
    for key in platforms:
        config = PLATFORM_CONFIGS.get(key)
        if not config:
            continue

        normalized_text = normalize_linkedin_text(text) if key == "linkedin" else normalize_common_text(text)

        image_cap = 4 if key in ("twitter", "bluesky") else 1
        parts, image_refs_by_part, mode = build_thread_plan(
            text=normalized_text,
            config=config,
            image_count=image_count,
            per_post_image_cap=image_cap,
        )

        full_text = "".join(parts)
        count = grapheme.length(full_text) if config.use_graphemes else len(full_text)
        limit = config.char_limit

        result[key] = {
            "parts": parts,
            "image_refs": image_refs_by_part,
            "mode": mode,
            "count": count,
            "limit": limit,
            "over": limit is not None and count > limit,
        }

    return jsonify(result)


@bp.route("/api/post", methods=["POST"])
def post():
    """Post to all enabled platforms. Accepts multipart/form-data."""
    text = request.form.get("text", "").strip()
    platforms = request.form.getlist("platforms")
    image_files = request.files.getlist("images")
    if not image_files:
        # Backward compatibility for older clients using a single "image" field.
        legacy_image = request.files.get("image")
        if legacy_image:
            image_files = [legacy_image]

    if not text:
        return jsonify({"error": "No text provided"}), 400
    if not platforms:
        return jsonify({"error": "No platforms selected"}), 400

    image_bytes_list = []
    for image_file in image_files:
        if not image_file or not image_file.filename:
            continue
        image_bytes = image_file.read()
        if not validate_image(image_bytes):
            return jsonify({"error": "Invalid image file"}), 400
        image_bytes_list.append(image_bytes)

    results = {}
    for key in platforms:
        config = PLATFORM_CONFIGS.get(key)
        if not config:
            results[key] = {"success": False, "error": "Unknown platform"}
            continue

        normalized_text = normalize_linkedin_text(text) if key == "linkedin" else normalize_common_text(text)

        max_images = 4 if key in ("twitter", "bluesky") else 1
        parts, image_refs_by_part, mode = build_thread_plan(
            text=normalized_text,
            config=config,
            image_count=len(image_bytes_list),
            per_post_image_cap=max_images,
        )

        resized_images = [resize_for_platform(img, key) for img in image_bytes_list]
        images_by_part = [
            [resized_images[idx] for idx in refs[:max_images] if 0 <= idx < len(resized_images)]
            for refs in image_refs_by_part
        ]

        try:
            if key == "twitter":
                platform = TwitterPlatform()
                result = platform.post(parts, images_by_part=images_by_part, mode=mode)
            elif key == "bluesky":
                platform = BlueskyPlatform()
                result = platform.post(parts, images_by_part=images_by_part, mode=mode)
            elif key == "linkedin":
                platform = LinkedInPlatform()
                if not platform.access_token:
                    result = {
                        "success": False,
                        "error": "No access token. Authorize LinkedIn first.",
                    }
                else:
                    result = platform.post(parts, images_by_part=images_by_part, mode=mode)
            else:
                result = {"success": False, "error": "Unknown platform"}
        except Exception as e:
            result = {"success": False, "error": str(e)}

        rate_limit = result.get("rate_limit")
        if rate_limit:
            with _platform_rate_limits_lock:
                _platform_rate_limits[key] = rate_limit

        results[key] = result

    return jsonify(results)


@bp.route("/api/enhance", methods=["POST"])
def enhance():
    """Enhance post copy using AI editing suggestions."""
    data = request.get_json() or {}
    text = (data.get("text") or "").strip()
    if not text:
        return jsonify({"error": "No text provided"}), 400
    if len(text) > ENHANCE_MAX_CHARS:
        return jsonify({
            "error": f"Text too long for enhancement. Max {ENHANCE_MAX_CHARS} characters."
        }), 400

    client_ip = request.headers.get("X-Forwarded-For", request.remote_addr or "unknown")
    client_ip = client_ip.split(",")[0].strip() or "unknown"
    if _is_enhance_rate_limited(client_ip):
        return jsonify({"error": "Too many enhancement requests. Please wait and try again."}), 429

    try:
        enhanced = _enhance_text_with_ai(text)
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        return jsonify({"error": str(e)}), 502

    return jsonify({"text": enhanced})


@bp.route("/api/linkedin/authorize")
def linkedin_authorize():
    """Redirect the user to LinkedIn's OAuth authorization page."""
    try:
        platform = LinkedInPlatform()
    except ValueError as e:
        return jsonify({"error": str(e)}), 400

    auth_url = (
        f"https://www.linkedin.com/oauth/v2/authorization"
        f"?response_type=code"
        f"&client_id={platform.client_id}"
        f"&redirect_uri={platform.REDIRECT_URI}"
        f"&scope=openid%20profile%20email%20w_member_social"
    )
    return redirect(auth_url)


@bp.route("/callback/linkedin")
def linkedin_callback():
    """Handle LinkedIn OAuth callback — exchange code for tokens."""
    code = request.args.get("code")
    error = request.args.get("error")

    if error or not code:
        return render_template(
            "index.html",
            linkedin_status="error",
            linkedin_message=error or "No authorization code received.",
        )

    try:
        platform = LinkedInPlatform()
    except ValueError as e:
        return render_template(
            "index.html",
            linkedin_status="error",
            linkedin_message=str(e),
        )

    resp = http_requests.post(
        "https://www.linkedin.com/oauth/v2/accessToken",
        data={
            "grant_type": "authorization_code",
            "code": code,
            "client_id": platform.client_id,
            "client_secret": platform.client_secret,
            "redirect_uri": platform.REDIRECT_URI,
        },
        timeout=20,
    )

    if resp.status_code != 200:
        return render_template(
            "index.html",
            linkedin_status="error",
            linkedin_message=f"Token exchange failed: {resp.text}",
        )

    tokens = resp.json()
    platform.access_token = tokens["access_token"]
    platform.refresh_token = tokens.get("refresh_token", "")
    platform._save_tokens()

    return render_template(
        "index.html",
        linkedin_status="success",
        linkedin_message="LinkedIn authorized successfully!",
    )


@bp.route("/api/linkedin/status")
def linkedin_status():
    """Check if LinkedIn access token exists."""
    token = os.environ.get("LINKEDIN_ACCESS_TOKEN", "")
    return jsonify({"authorized": bool(token)})


@bp.route("/api/rate-limits")
def rate_limits():
    """Return latest known per-platform API rate-limit snapshots."""
    with _platform_rate_limits_lock:
        return jsonify(_platform_rate_limits)


@bp.route("/api/profile")
def profile():
    """Return display info for preview mockups."""
    bluesky_username = os.environ.get("BLUESKY_USERNAME", "")
    return jsonify({
        "displayName": os.environ.get("DISPLAY_NAME", "Your Name"),
        "twitterHandle": os.environ.get("TWITTER_HANDLE", "@you"),
        "blueskyHandle": f"@{bluesky_username}" if bluesky_username else "@you.bsky.social",
        "linkedinHeadline": os.environ.get("LINKEDIN_HEADLINE", "Your headline"),
    })
