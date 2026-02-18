"""Text normalization utilities for platform-safe posting."""


def normalize_common_text(text: str) -> str:
    """Normalize punctuation to plain ASCII-friendly forms."""
    if not text:
        return text

    # Keep author intent for plain "--" style punctuation.
    text = text.replace("\u2014", "--")  # em dash
    text = text.replace("\u2013", "-")   # en dash
    return text


def normalize_linkedin_text(text: str) -> str:
    """Normalize LinkedIn text and neutralize accidental markdown markers."""
    text = normalize_common_text(text)
    # Break *bold* parsing while preserving visible asterisks.
    return text.replace("*", "*\u200b")
