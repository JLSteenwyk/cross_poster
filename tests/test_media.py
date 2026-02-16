"""Tests for the media handler."""

import io
import pytest
from PIL import Image
from core.media import validate_image, resize_for_platform, PLATFORM_IMAGE_LIMITS


def _make_test_image(width=100, height=100, format="PNG") -> bytes:
    """Create a test image as bytes."""
    img = Image.new("RGB", (width, height), color="red")
    buf = io.BytesIO()
    img.save(buf, format=format)
    return buf.getvalue()


class TestValidateImage:
    def test_valid_png(self):
        data = _make_test_image(format="PNG")
        assert validate_image(data) is True

    def test_valid_jpeg(self):
        data = _make_test_image(format="JPEG")
        assert validate_image(data) is True

    def test_invalid_data(self):
        assert validate_image(b"not an image") is False

    def test_empty_data(self):
        assert validate_image(b"") is False


class TestResizeForPlatform:
    def test_small_image_unchanged(self):
        data = _make_test_image(100, 100)
        result = resize_for_platform(data, "bluesky")
        # Should still be valid
        img = Image.open(io.BytesIO(result))
        assert img.size == (100, 100)

    def test_bluesky_size_limit(self):
        # Create a large image that exceeds 1MB
        data = _make_test_image(4000, 4000)
        result = resize_for_platform(data, "bluesky")
        assert len(result) <= PLATFORM_IMAGE_LIMITS["bluesky"]["max_bytes"]

    def test_twitter_size_limit(self):
        data = _make_test_image(4000, 4000)
        result = resize_for_platform(data, "twitter")
        assert len(result) <= PLATFORM_IMAGE_LIMITS["twitter"]["max_bytes"]

    def test_unknown_platform_returns_original(self):
        data = _make_test_image(100, 100)
        result = resize_for_platform(data, "unknown_platform")
        assert result == data
