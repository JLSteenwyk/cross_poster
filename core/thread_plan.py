"""Thread planning helpers for manual subposts and image mapping."""

import re

from core.splitter import PlatformConfig, split_for_platform

MANUAL_SEPARATOR_RE = re.compile(r"(?m)^\s*---+\s*$")
IMAGE_REF_RE = re.compile(r"\[img(\d+)\]", flags=re.I)


def _unique_in_order(values: list[int]) -> list[int]:
    seen = set()
    ordered = []
    for value in values:
        if value in seen:
            continue
        seen.add(value)
        ordered.append(value)
    return ordered


def _extract_refs_and_clean_text(text: str, image_count: int) -> tuple[str, list[int]]:
    refs: list[int] = []

    def _replace(match: re.Match) -> str:
        idx = int(match.group(1)) - 1
        if 0 <= idx < image_count:
            refs.append(idx)
        return ""

    cleaned = IMAGE_REF_RE.sub(_replace, text)
    cleaned = re.sub(r"[ \t]{2,}", " ", cleaned)
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)
    return cleaned.strip(), _unique_in_order(refs)


def _distribute_refs(image_count: int, part_count: int, per_post_cap: int) -> list[list[int]]:
    if image_count <= 0 or part_count <= 0 or per_post_cap <= 0:
        return [[] for _ in range(max(0, part_count))]

    refs = list(range(image_count))
    result = []
    cursor = 0
    for _ in range(part_count):
        next_cursor = min(cursor + per_post_cap, len(refs))
        result.append(refs[cursor:next_cursor])
        cursor = next_cursor
    return result


def build_thread_plan(
    text: str,
    config: PlatformConfig,
    image_count: int = 0,
    per_post_image_cap: int = 4,
) -> tuple[list[str], list[list[int]], str]:
    """Return parts and image refs for a platform.

    Modes:
    - manual: line separator `---` defines subposts, `[imgN]` attaches images to that subpost.
    - auto: uses splitter and distributes images across posts by cap.
    """
    if MANUAL_SEPARATOR_RE.search(text or ""):
        segments = [segment for segment in MANUAL_SEPARATOR_RE.split(text or "") if segment.strip()]
        parts: list[str] = []
        image_refs_by_part: list[list[int]] = []

        for segment in segments:
            clean_segment, refs = _extract_refs_and_clean_text(segment, image_count)
            segment_parts = split_for_platform(clean_segment, config)
            if not segment_parts:
                continue
            for i, segment_part in enumerate(segment_parts):
                parts.append(segment_part)
                image_refs_by_part.append(refs if i == 0 else [])

        if not parts:
            return [""], [[]], "manual"
        return parts, image_refs_by_part, "manual"

    clean_text, _ = _extract_refs_and_clean_text(text or "", image_count)
    parts = split_for_platform(clean_text, config)
    image_refs_by_part = _distribute_refs(
        image_count=image_count,
        part_count=len(parts),
        per_post_cap=per_post_image_cap,
    )
    return parts, image_refs_by_part, "auto"
