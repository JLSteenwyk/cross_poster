"""Tests for the thread splitter."""

import pytest
from core.splitter import split_for_platform, PlatformConfig, TWITTER, BLUESKY, LINKEDIN


class TestPlatformConfigs:
    def test_twitter_config(self):
        assert TWITTER.name == "Twitter"
        assert TWITTER.char_limit == 280
        assert TWITTER.use_graphemes is False

    def test_bluesky_config(self):
        assert BLUESKY.name == "BlueSky"
        assert BLUESKY.char_limit == 300
        assert BLUESKY.use_graphemes is True

    def test_linkedin_config(self):
        assert LINKEDIN.name == "LinkedIn"
        assert LINKEDIN.char_limit == 3000
        assert LINKEDIN.use_graphemes is False


class TestSplitForPlatform:
    def test_short_text_no_split(self):
        text = "Hello world."
        parts = split_for_platform(text, TWITTER)
        assert parts == ["Hello world."]

    def test_text_at_exact_limit(self):
        text = "A" * 280
        parts = split_for_platform(text, TWITTER)
        assert parts == [text]

    def test_splits_at_sentence_boundary(self):
        # Two sentences that together exceed 280 chars
        s1 = "A" * 140 + "."
        s2 = " " + "B" * 140 + "."
        text = s1 + s2
        parts = split_for_platform(text, TWITTER)
        assert len(parts) == 2
        # Each part should have a thread indicator
        assert "(1/2)" in parts[0]
        assert "(2/2)" in parts[1]

    def test_thread_indicator_counted_against_limit(self):
        # Text that barely fits in one post should NOT get a thread indicator
        text = "A" * 280
        parts = split_for_platform(text, TWITTER)
        assert len(parts) == 1
        assert "(1/" not in parts[0]

    def test_bluesky_uses_graphemes(self):
        # An emoji is 1 grapheme but multiple bytes/chars
        text = "Hello! " + "\U0001f600" * 290 + ". Done."
        parts = split_for_platform(text, BLUESKY)
        # Should split because grapheme count exceeds 300
        assert len(parts) >= 2

    def test_word_boundary_fallback(self):
        # One very long sentence that exceeds the limit
        text = "word " * 100  # 500 chars, no sentence boundaries
        parts = split_for_platform(text, TWITTER)
        assert len(parts) >= 2
        for part in parts:
            assert len(part) <= 280

    def test_empty_text(self):
        parts = split_for_platform("", TWITTER)
        assert parts == [""]

    def test_whitespace_only(self):
        parts = split_for_platform("   ", TWITTER)
        assert parts == ["   "]

    def test_linkedin_long_text_no_split(self):
        # 2000 chars should not split on LinkedIn (limit 3000)
        text = "A" * 2000
        parts = split_for_platform(text, LINKEDIN)
        assert parts == [text]

    def test_preserves_sentence_content(self):
        text = "First sentence. Second sentence. Third sentence."
        parts = split_for_platform(text, PlatformConfig("Test", 40, False))
        # All original content should appear across parts (minus indicators)
        joined = " ".join(p.replace("(1/3) ", "").replace("(2/3) ", "").replace("(3/3) ", "")
                          .replace(" (1/3)", "").replace(" (2/3)", "").replace(" (3/3)", "")
                          for p in parts)
        assert "First sentence" in joined
        assert "Second sentence" in joined
        assert "Third sentence" in joined

    def test_preserves_newlines_when_splitting(self):
        text = ("Line one.\n\nLine two with spacing.\nLine three. " * 12).strip()
        parts = split_for_platform(text, TWITTER)
        assert len(parts) > 1
        joined = "\n".join(
            p.rsplit(" (", 1)[0] if p.endswith(")") else p
            for p in parts
        )
        assert "Line one.\n\nLine two with spacing.\nLine three." in joined

    def test_preserves_dotted_versions_when_splitting(self):
        prefix = ("A" * 260) + ". "
        text = (
            prefix
            + "OrthoFisher (v1.1.2) has had a major quality and usability refresh "
            + "since the initial release."
        )
        parts = split_for_platform(text, TWITTER)
        assert len(parts) > 1
        joined = " ".join(
            p.rsplit(" (", 1)[0] if p.endswith(")") else p
            for p in parts
        )
        assert "(v1.1.2)" in joined
