"""Image validation and resizing for cross-platform posting."""

import io

from PIL import Image


PLATFORM_IMAGE_LIMITS = {
    "twitter": {"max_bytes": 5 * 1024 * 1024},      # 5MB
    "bluesky": {"max_bytes": 1 * 1024 * 1024},       # 1MB
    "linkedin": {"max_bytes": 10 * 1024 * 1024},     # 10MB (practical limit)
}


def validate_image(data: bytes) -> bool:
    """Check if data is a valid image (PNG, JPEG, or GIF).

    Args:
        data: Raw image bytes.

    Returns:
        True if valid image, False otherwise.
    """
    if not data:
        return False
    try:
        img = Image.open(io.BytesIO(data))
        img.verify()
        return img.format in ("PNG", "JPEG", "GIF")
    except Exception:
        return False


def resize_for_platform(data: bytes, platform: str) -> bytes:
    """Resize an image to fit a platform's size constraints.

    Progressively reduces dimensions until the file size is under the limit.

    Args:
        data: Raw image bytes.
        platform: Platform name (twitter, bluesky, linkedin, substack).

    Returns:
        Image bytes, possibly resized.
    """
    limits = PLATFORM_IMAGE_LIMITS.get(platform)
    if not limits:
        return data

    max_bytes = limits["max_bytes"]

    if len(data) <= max_bytes:
        return data

    img = Image.open(io.BytesIO(data))
    # Convert to RGB if necessary (e.g., RGBA PNGs)
    if img.mode in ("RGBA", "P"):
        img = img.convert("RGB")

    # Progressively scale down until under the size limit
    scale = 0.9
    for _ in range(20):
        new_w = int(img.width * scale)
        new_h = int(img.height * scale)
        if new_w < 10 or new_h < 10:
            break
        resized = img.resize((new_w, new_h), Image.LANCZOS)
        buf = io.BytesIO()
        resized.save(buf, format="JPEG", quality=85)
        if buf.tell() <= max_bytes:
            return buf.getvalue()
        scale *= 0.9

    # Last resort: return whatever we got
    buf = io.BytesIO()
    resized.save(buf, format="JPEG", quality=70)
    return buf.getvalue()
