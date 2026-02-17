"""Thread splitter for cross-platform posting.

Splits text into thread parts at sentence boundaries, respecting
per-platform character/grapheme limits.
"""

import re
from dataclasses import dataclass
from typing import Optional

import grapheme


@dataclass
class PlatformConfig:
    name: str
    char_limit: Optional[int]
    use_graphemes: bool


TWITTER = PlatformConfig("Twitter", 280, False)
BLUESKY = PlatformConfig("BlueSky", 300, True)
LINKEDIN = PlatformConfig("LinkedIn", 3000, False)



def _measure(text: str, use_graphemes: bool) -> int:
    """Measure text length using graphemes or characters."""
    if use_graphemes:
        return grapheme.length(text)
    return len(text)


def _split_sentences(text: str) -> list[str]:
    """Split text into sentence-like chunks while preserving whitespace/newlines."""
    chunks = re.findall(r'[^.!?]+[.!?]*(?:\s+|$)', text, flags=re.S)
    return [c for c in chunks if c]


def _split_words(text: str) -> list[str]:
    """Split into word/whitespace tokens while preserving exact formatting."""
    return re.findall(r"\S+|\s+", text, flags=re.S)


def split_for_platform(text: str, config: PlatformConfig) -> list[str]:
    """Split text into thread parts for a given platform.

    Args:
        text: The full post text.
        config: Platform configuration with limits.

    Returns:
        List of text parts. Single-element list if no splitting needed.
    """
    # No limit means no splitting
    if config.char_limit is None:
        return [text]

    # If text fits within limit, return as-is
    if _measure(text, config.use_graphemes) <= config.char_limit:
        return [text]

    # First pass: estimate number of parts to calculate indicator size
    # We'll use sentence splitting first, then word splitting as fallback
    sentences = _split_sentences(text)

    # Build parts by accumulating sentences
    raw_parts = _build_parts_from_segments(sentences, config, is_sentences=True)

    # If we still have parts that are too long (single long sentences),
    # split those at word boundaries
    final_parts = []
    for part in raw_parts:
        if _measure(part, config.use_graphemes) > config.char_limit:
            words = _split_words(part)
            word_parts = _build_parts_from_segments(
                words, config, is_sentences=False,
                total_parts_hint=len(raw_parts)
            )
            final_parts.extend(word_parts)
        else:
            final_parts.append(part)

    # Add thread indicators if more than one part
    if len(final_parts) > 1:
        final_parts = _add_indicators(final_parts, config)

    return final_parts


def _build_parts_from_segments(
    segments: list[str],
    config: PlatformConfig,
    is_sentences: bool,
    total_parts_hint: int = 0,
) -> list[str]:
    """Build parts from segments (sentences or words), respecting limits.

    Reserves space for thread indicators like (1/10).
    """
    if not segments:
        return [""]

    # Reserve space for thread indicator: " (XX/XX)" = up to 8 chars
    indicator_reserve = 8
    effective_limit = config.char_limit - indicator_reserve

    parts = []
    current = ""
    current_len = 0

    segment_lengths = [
        grapheme.length(segment) if config.use_graphemes else len(segment)
        for segment in segments
    ]

    for segment, segment_len in zip(segments, segment_lengths):
        candidate_len = current_len + segment_len

        if candidate_len <= effective_limit:
            current += segment
            current_len = candidate_len
        else:
            if current:
                parts.append(current)
            current = segment
            current_len = segment_len

    if current:
        parts.append(current)

    return parts


def _add_indicators(parts: list[str], config: PlatformConfig) -> list[str]:
    """Add (1/N) thread indicators to each part."""
    total = len(parts)
    result = []
    for i, part in enumerate(parts, 1):
        indicator = f" ({i}/{total})"
        base = part.rstrip()
        # Verify it still fits; if not, trim the part
        combined = base + indicator
        if config.char_limit and _measure(combined, config.use_graphemes) > config.char_limit:
            # Trim part to make room
            overage = _measure(combined, config.use_graphemes) - config.char_limit
            if config.use_graphemes:
                # Trim graphemes from end
                graphemes_list = list(grapheme.graphemes(base))
                trimmed = "".join(graphemes_list[:len(graphemes_list) - overage])
            else:
                trimmed = base[:len(base) - overage]
            result.append(trimmed + indicator)
        else:
            result.append(combined)
    return result
