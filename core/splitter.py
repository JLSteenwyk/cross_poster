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
    split_mode: str = "sentence_hybrid"


TWITTER = PlatformConfig("Twitter", 280, False, "word_dense")
BLUESKY = PlatformConfig("BlueSky", 300, True, "sentence_hybrid")
LINKEDIN = PlatformConfig("LinkedIn", 3000, False, "sentence_hybrid")



def _measure(text: str, use_graphemes: bool) -> int:
    """Measure text length using graphemes or characters."""
    if use_graphemes:
        return grapheme.length(text)
    return len(text)


def _split_sentences(text: str) -> list[str]:
    """Split text into sentence-like chunks while preserving whitespace/newlines."""
    chunks = re.findall(r'.+?(?:[.!?](?:\s+|$)|$)', text, flags=re.S)
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

    if config.split_mode == "word_dense":
        raw_parts = _build_parts_with_dynamic_reserve(_split_words(text), config)
    else:
        sentence_parts = _build_parts_with_dynamic_reserve(_split_sentences(text), config)
        # BlueSky favors sentence boundaries, but if that creates a tiny tail,
        # repack by words for denser posts.
        if _needs_denser_word_packing(sentence_parts, config):
            raw_parts = _build_parts_with_dynamic_reserve(_split_words(text), config)
        else:
            raw_parts = sentence_parts

    if len(raw_parts) > 1:
        return _add_indicators(raw_parts, config)
    return raw_parts


def _build_parts_from_segments(
    segments: list[str],
    config: PlatformConfig,
    indicator_reserve: int = 0,
) -> list[str]:
    """Build parts from segments (sentences or words), respecting limits.

    Reserves space for thread indicators like (1/10).
    """
    if not segments:
        return [""]

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


def _build_parts_with_dynamic_reserve(segments: list[str], config: PlatformConfig) -> list[str]:
    """Build parts while reserving exact indicator length for final part count."""
    if not segments:
        return [""]

    # Start with a practical indicator estimate like " (1/2)".
    total_estimate = 2
    parts = _build_parts_from_segments(segments, config, indicator_reserve=6)

    for _ in range(6):
        if len(parts) <= 1:
            # No indicators needed for a single-part post.
            return _build_parts_from_segments(segments, config, indicator_reserve=0)

        total_estimate = len(parts)
        reserve = len(f" ({total_estimate}/{total_estimate})")
        new_parts = _build_parts_from_segments(segments, config, indicator_reserve=reserve)

        if len(new_parts) == total_estimate:
            return new_parts
        parts = new_parts

    return parts


def _needs_denser_word_packing(parts: list[str], config: PlatformConfig) -> bool:
    """Detect split patterns with a tiny trailing part that word packing can improve."""
    if not parts or len(parts) < 2 or config.char_limit is None:
        return False
    last_fill = _measure(parts[-1], config.use_graphemes) / config.char_limit
    prev_fill = _measure(parts[-2], config.use_graphemes) / config.char_limit
    return last_fill < 0.35 and prev_fill > 0.65


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
