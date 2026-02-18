"""Tests for thread planning and image reference mapping."""

from core.splitter import TWITTER
from core.thread_plan import build_thread_plan


class TestThreadPlan:
    def test_auto_mode_distributes_images(self):
        text = ("A" * 270) + ". " + ("B" * 270) + "."
        parts, refs, mode = build_thread_plan(
            text=text,
            config=TWITTER,
            image_count=3,
            per_post_image_cap=2,
        )
        assert mode == "auto"
        assert len(parts) >= 2
        assert refs[0] == [0, 1]
        assert refs[1] == [2]

    def test_manual_mode_maps_images_per_subpost(self):
        text = "First [img1] [img2]\n---\nSecond [img3]"
        parts, refs, mode = build_thread_plan(
            text=text,
            config=TWITTER,
            image_count=4,
            per_post_image_cap=4,
        )
        assert mode == "manual"
        assert parts == ["First", "Second"]
        assert refs == [[0, 1], [2]]

    def test_manual_mode_ignores_out_of_range_refs(self):
        text = "Only [img9]\n---\nSecond [img1]"
        parts, refs, mode = build_thread_plan(
            text=text,
            config=TWITTER,
            image_count=2,
            per_post_image_cap=4,
        )
        assert mode == "manual"
        assert parts == ["Only", "Second"]
        assert refs == [[], [0]]

    def test_manual_mode_accepts_three_or_more_dashes(self):
        text = "First section\n----\nSecond section"
        parts, refs, mode = build_thread_plan(
            text=text,
            config=TWITTER,
            image_count=0,
            per_post_image_cap=4,
        )
        assert mode == "manual"
        assert parts == ["First section", "Second section"]
        assert refs == [[], []]
