"""
Shared prompt structure helpers.
"""

from typing import Iterable


PROMPT_SECTION_HEADERS = (
    "【LANGUAGE RULE】",
    "【NON-NEGOTIABLE】",
    "【TEXT TO RENDER】",
    "【PAGE SEMANTICS】",
    "【STYLE SYSTEM】",
    "【SEED / REFERENCE CONTROL】",
    "【VISUAL SCENE】",
    "【NEGATIVE CONSTRAINTS】",
    "【FINAL INSTRUCTION】",
)


def format_prompt_sections(prefix: str = "- ") -> str:
    return "\n".join(f"{prefix}{section}" for section in PROMPT_SECTION_HEADERS)


def prompt_has_required_sections(prompt: str, sections: Iterable[str] = PROMPT_SECTION_HEADERS) -> bool:
    return all(section in prompt for section in sections)
