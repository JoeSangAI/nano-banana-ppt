from nano_banana_ppt.core.generator import _merge_native_images_with_locked_regions


def test_overlay_bbox_falls_back_to_allowed_region_when_vlm_drifts():
    native_images = [
        {
            "path": "blend.png",
            "semantic_role": "left portrait",
            "integration_mode": "blend",
            "bounding_box": {"left": 0.05, "top": 0.12, "width": 0.34, "height": 0.72},
        },
        {
            "path": "overlay.png",
            "semantic_role": "right screenshot",
            "integration_mode": "overlay",
            "overlay_allowed_region": {"left": 0.58, "top": 0.18, "width": 0.30, "height": 0.58},
            "bounding_box": {"left": 0.58, "top": 0.18, "width": 0.30, "height": 0.58},
        },
    ]

    calculated_overlay_images = [
        {
            "path": "overlay.png",
            "integration_mode": "overlay",
            "dynamic_bounding_box": {"left": 0.04, "top": 0.22, "width": 0.38, "height": 0.60},
        }
    ]

    merged = _merge_native_images_with_locked_regions(native_images, calculated_overlay_images)
    overlay = merged[1]

    assert overlay["dynamic_bounding_box"] == {"left": 0.58, "top": 0.18, "width": 0.30, "height": 0.58}


def test_overlay_bbox_keeps_adjustment_when_it_stays_in_allowed_region():
    native_images = [
        {
            "path": "overlay.png",
            "semantic_role": "right screenshot",
            "integration_mode": "overlay",
            "overlay_allowed_region": {"left": 0.55, "top": 0.16, "width": 0.35, "height": 0.60},
            "bounding_box": {"left": 0.55, "top": 0.16, "width": 0.35, "height": 0.60},
        }
    ]

    calculated_overlay_images = [
        {
            "path": "overlay.png",
            "integration_mode": "overlay",
            "dynamic_bounding_box": {"left": 0.60, "top": 0.20, "width": 0.25, "height": 0.40},
        }
    ]

    merged = _merge_native_images_with_locked_regions(native_images, calculated_overlay_images)
    overlay = merged[0]["dynamic_bounding_box"]

    assert overlay == {"left": 0.60, "top": 0.20, "width": 0.25, "height": 0.40}
