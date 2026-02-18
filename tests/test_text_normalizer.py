"""Tests for platform text normalization."""

from core.text_normalizer import normalize_common_text, normalize_linkedin_text


class TestTextNormalizer:
    def test_normalize_common_text_converts_em_dash(self):
        assert normalize_common_text("A — B") == "A -- B"

    def test_normalize_common_text_converts_en_dash(self):
        assert normalize_common_text("A – B") == "A - B"

    def test_normalize_linkedin_text_neutralizes_asterisks(self):
        normalized = normalize_linkedin_text("i*agent and *bold*")
        assert "i*\u200bagent" in normalized
        assert "*\u200bbold*\u200b" in normalized
