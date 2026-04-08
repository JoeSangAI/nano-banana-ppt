"""
Curated Style Library for Nano Banana PPT

Loads predefined visual style definitions from Markdown files in the styles/ directory.
Each .md file uses YAML frontmatter for structured data and Markdown body for descriptions.

Category structure:
1. 内容讲解型 (Content / Educational)
2. 结构与技术型 (Structure & Technical)
3. 商务与高端型 (Business & Premium)
4. 人物与亲和型 (Human & Approachable)
5. 编辑、杂志与潮流型 (Editorial, Magazine & Street)
6. 流行、娱乐与高冲击型 (Pop, Youth & High-energy)
7. Artistic & Avant-garde
"""

import os
import re
import logging
from pathlib import Path
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)

# Resolve styles/ directory relative to this file
_STYLES_DIR = Path(__file__).resolve().parent.parent / "styles"


# ── Frontmatter parser (no external dependency) ──

def _parse_frontmatter(text: str) -> tuple:
    """Parse YAML-ish frontmatter delimited by '---' lines.

    Returns (frontmatter_dict, body_str).
    Handles: strings, lists (lines starting with '  - ').
    """
    if not text.startswith("---"):
        return {}, text

    # Split on the second '---'
    parts = text.split("---", 2)
    if len(parts) < 3:
        return {}, text

    fm_text = parts[1].strip()
    body = parts[2].strip()

    result = {}
    current_key = None

    for line in fm_text.splitlines():
        stripped = line.strip()
        if not stripped:
            continue

        # List item under current key
        if stripped.startswith("- ") and current_key is not None:
            val = stripped[2:].strip().strip('"').strip("'")
            if current_key not in result:
                result[current_key] = []
            if isinstance(result[current_key], list):
                result[current_key].append(val)
            continue

        # Key: value pair
        if ":" in stripped:
            key, _, val = stripped.partition(":")
            key = key.strip()
            val = val.strip().strip('"').strip("'")
            current_key = key
            if val:
                result[key] = val
            # If val is empty, next lines might be list items
            continue

    return result, body


def _parse_body_sections(body: str) -> dict:
    """Parse Markdown body into sections keyed by ## heading."""
    section_map = {
        "风格描述": "description",
        "造型语言": "shape_language",
        "图像风格": "imagery_style",
        "强调色用法": "accent_usage",
    }
    result = {}
    current_field = None
    current_lines = []

    for line in body.splitlines():
        heading_match = re.match(r"^##\s+(.+)$", line)
        if heading_match:
            # Save previous section
            if current_field:
                result[current_field] = "\n".join(current_lines).strip()
            heading = heading_match.group(1).strip()
            current_field = section_map.get(heading)
            current_lines = []
        else:
            if current_field is not None:
                current_lines.append(line)

    # Save last section
    if current_field:
        result[current_field] = "\n".join(current_lines).strip()

    return result


def _load_style_file(filepath: Path) -> Optional[tuple]:
    """Load a single style .md file. Returns (style_id, style_dict) or None."""
    try:
        text = filepath.read_text(encoding="utf-8")
    except Exception as e:
        logger.warning(f"Cannot read style file {filepath}: {e}")
        return None

    fm, body = _parse_frontmatter(text)
    if not fm.get("id"):
        logger.warning(f"Style file {filepath.name} has no 'id' in frontmatter, skipping")
        return None

    sections = _parse_body_sections(body)

    style_id = fm["id"]
    # Build aliases list: always include the id itself as first alias
    aliases = [style_id]
    fm_aliases = fm.get("aliases", [])
    if isinstance(fm_aliases, str):
        fm_aliases = [fm_aliases]
    aliases.extend(fm_aliases)

    style_dict = {
        "category": fm.get("category", ""),
        "aliases": aliases,
        "description": sections.get("description", ""),
        "palette": fm.get("palette", []),
        "fonts": fm.get("fonts", []),
        "shape_language": sections.get("shape_language", ""),
        "imagery_style": sections.get("imagery_style", ""),
        "accent_usage": sections.get("accent_usage", ""),
        "best_for": fm.get("best_for", []),
        "avoid": fm.get("avoid", []),
    }

    # Ensure list fields are lists
    for list_field in ("palette", "fonts", "best_for", "avoid", "aliases"):
        if isinstance(style_dict[list_field], str):
            style_dict[list_field] = [style_dict[list_field]]

    return style_id, style_dict


def _load_styles_from_dir(styles_dir: Path = None) -> Dict[str, dict]:
    """Scan styles/ directory and load all .md files into a dict."""
    if styles_dir is None:
        styles_dir = _STYLES_DIR

    styles = {}
    if not styles_dir.is_dir():
        logger.warning(f"Styles directory not found: {styles_dir}")
        return styles

    for md_file in sorted(styles_dir.glob("*.md")):
        result = _load_style_file(md_file)
        if result:
            style_id, style_dict = result
            styles[style_id] = style_dict

    logger.info(f"Loaded {len(styles)} styles from {styles_dir}")
    return styles


# ── Module-level style library (loaded once at import time) ──

STYLE_LIBRARY: Dict[str, dict] = _load_styles_from_dir()


def reload_styles(styles_dir: Path = None) -> int:
    """Reload all styles from disk. Returns number of styles loaded."""
    global STYLE_LIBRARY
    STYLE_LIBRARY = _load_styles_from_dir(styles_dir)
    return len(STYLE_LIBRARY)


# ── Public API (unchanged signatures) ──

def get_curated_style(user_preference: str) -> dict:
    """
    Check if the user preference matches any curated style aliases.
    Returns the style dict if found, else None.
    """
    if not user_preference:
        return None

    pref_lower = user_preference.lower().strip()

    for style_key, style_data in STYLE_LIBRARY.items():
        for alias in style_data.get("aliases", []):
            if alias.lower() in pref_lower or pref_lower in alias.lower():
                return style_data

    return None


def get_styles_by_category(category: str) -> list:
    """
    Return all styles in a given category.
    """
    return [
        {"key": k, **v}
        for k, v in STYLE_LIBRARY.items()
        if v.get("category") == category
    ]


def list_all_categories() -> list:
    """
    Return unique category names.
    """
    return list(set(v.get("category") for v in STYLE_LIBRARY.values()))
