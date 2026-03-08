from nano_banana_ppt.core.image_selector import ImageSelector


class _DummyClient:
    pass


def test_postprocess_marks_wide_ad_banner_as_junk():
    selector = ImageSelector(_DummyClient())
    raw = {
        "semantic_summary": "A promotional advertisement banner for a Blancpain watch.",
        "image_type": "product",
        "text_density": "low",
        "suitability_for_overlay": 90,
        "suitability_for_blend": 20,
        "is_junk": False,
    }

    result = selector._postprocess_analysis("/tmp/banner.webp", raw, (1067, 300))

    assert result["is_junk"] is True
    assert result["junk_reason"] == "detected_ad_banner_or_qr"


def test_default_layout_for_content_page():
    selector = ImageSelector(_DummyClient())
    page = {"type": "content"}
    assert selector._default_layout_for_page(page) == "left_visual_right_text"
