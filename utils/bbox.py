"""
Bbox helper functions for image processing and layout calculations.
"""
import logging
from typing import Dict, List, Optional

from PIL import Image

logger = logging.getLogger(__name__)


def _fix_black_corners(img: Image.Image) -> Image.Image:
    """Fix black corners in generated images (placeholder function)"""
    return img


def _clamp(value: float, minimum: float, maximum: float) -> float:
    return max(minimum, min(value, maximum))


def _normalize_bbox(bbox: Dict) -> Optional[Dict[str, float]]:
    if not bbox:
        return None
    try:
        left = float(bbox.get("left", 0.0))
        top = float(bbox.get("top", 0.0))
        width = float(bbox.get("width", 0.0))
        height = float(bbox.get("height", 0.0))
    except (TypeError, ValueError):
        return None

    if width <= 0 or height <= 0:
        return None

    left = _clamp(left, 0.0, 1.0)
    top = _clamp(top, 0.0, 1.0)
    width = _clamp(width, 0.0, 1.0 - left)
    height = _clamp(height, 0.0, 1.0 - top)
    if width <= 0 or height <= 0:
        return None

    return {
        "left": round(left, 4),
        "top": round(top, 4),
        "width": round(width, 4),
        "height": round(height, 4),
    }


def _fit_bbox_within_region(candidate_bbox: Optional[Dict], allowed_bbox: Optional[Dict]) -> Optional[Dict[str, float]]:
    allowed = _normalize_bbox(allowed_bbox)
    if not allowed:
        return _normalize_bbox(candidate_bbox)

    candidate = _normalize_bbox(candidate_bbox) or allowed
    width = min(candidate["width"], allowed["width"])
    height = min(candidate["height"], allowed["height"])
    max_left = allowed["left"] + allowed["width"] - width
    max_top = allowed["top"] + allowed["height"] - height
    left = _clamp(candidate["left"], allowed["left"], max_left)
    top = _clamp(candidate["top"], allowed["top"], max_top)

    return {
        "left": round(left, 4),
        "top": round(top, 4),
        "width": round(width, 4),
        "height": round(height, 4),
    }


def _bbox_overlap_area(a: Optional[Dict], b: Optional[Dict]) -> float:
    box_a = _normalize_bbox(a)
    box_b = _normalize_bbox(b)
    if not box_a or not box_b:
        return 0.0

    ax2 = box_a["left"] + box_a["width"]
    ay2 = box_a["top"] + box_a["height"]
    bx2 = box_b["left"] + box_b["width"]
    by2 = box_b["top"] + box_b["height"]
    overlap_w = max(0.0, min(ax2, bx2) - max(box_a["left"], box_b["left"]))
    overlap_h = max(0.0, min(ay2, by2) - max(box_a["top"], box_b["top"]))
    return round(overlap_w * overlap_h, 6)


def _lock_overlay_bbox(
    original_image: Dict,
    calculated_image: Optional[Dict],
    blend_reserved_regions: List[Dict],
) -> Dict:
    merged_image = dict(original_image)
    candidate_bbox = None
    if calculated_image:
        candidate_bbox = calculated_image.get("dynamic_bounding_box") or calculated_image.get("bounding_box")

    allowed_bbox = (
        original_image.get("overlay_allowed_region")
        or original_image.get("bounding_box")
        or candidate_bbox
    )
    locked_bbox = _fit_bbox_within_region(candidate_bbox, allowed_bbox)

    if locked_bbox and any(_bbox_overlap_area(locked_bbox, reserved) > 0.0001 for reserved in blend_reserved_regions):
        fallback_bbox = _normalize_bbox(original_image.get("bounding_box")) or _normalize_bbox(original_image.get("overlay_allowed_region"))
        if fallback_bbox:
            locked_bbox = fallback_bbox

    if locked_bbox:
        merged_image["dynamic_bounding_box"] = locked_bbox
    return merged_image
