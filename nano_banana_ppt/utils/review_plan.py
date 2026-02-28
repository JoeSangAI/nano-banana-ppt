"""
人类可审阅的 PPT 计划：plan_for_review.md 的生成与解析

- build_review_md: 从 narrative_outline + style_config 生成人类可读的 MD
- parse_review_md: 从 MD 解析回结构化数据
- derive_technical_plan: 从解析结果 + LLM 生成完整 plan.json（含 visual_prompt）
"""
import json
import logging
import re
from pathlib import Path
from typing import Dict, List, Optional, Any

logger = logging.getLogger(__name__)

REVIEW_MD_FILENAME = "plan_for_review.md"


def build_review_md(
    narrative_outline: List[Dict],
    style_config: Dict,
    meta: Dict,
) -> str:
    """
    从 narrative_outline 和 style_config 生成人类可读的 plan_for_review.md
    """
    palette = style_config.get("palette", [])
    palette_str = ", ".join(palette) if palette else "（自动）"
    style_desc = style_config.get("description", "（AI 自动设计）")
    fonts = style_config.get("fonts", [])
    fonts_str = ", ".join(fonts) if fonts else "（自动）"

    content_file = meta.get("content_file", "")
    lines = [
        "# PPT 视觉计划 · 待您确认",
        "",
        "> 请审阅以下内容，可直接编辑本文件。确认无误后，运行 `execute` 生成 PPT。",
        "",
        "---",
        "",
        "## 一、整体设计",
        "",
        "| 项目 | 说明 |",
        "|------|------|",
        f"| 内容源 | {content_file} |",
        f"| 模板 | {meta.get('template_file') or '无（AI 自动设计）'} |",
        f"| 配色 | {palette_str} |",
        f"| Logo | {meta.get('logo_file') or '未使用'} |",
        f"| 字体 | {fonts_str} |",
        f"| 风格 | {style_desc[:80]}{'...' if len(style_desc) > 80 else ''} |",
        "",
        "---",
        "",
        "## 二、各页预览",
        "",
    ]

    type_names = {
        "cover": "封面",
        "section": "章节",
        "content": "内容",
        "hero": "金句",
        "breathing": "呼吸",
        "toc": "目录",
        "table": "表格",
        "data": "数据",
        "flowchart": "流程",
        "framework": "框架",
        "comparison": "对比",
        "ending": "封底",
    }

    for page in narrative_outline:
        pnum = page.get("page_num", 0)
        ptype = page.get("type", "content")
        ptype_cn = type_names.get(ptype, ptype)

        tc = page.get("text_content", {})
        headline = tc.get("headline", "") or page.get("title", "")
        subhead = tc.get("subhead", "")
        body = list(dict.fromkeys(tc.get("body") or []))  # 去重，防止重复渲染
        table_data = tc.get("table_data") or page.get("table_data")
        visual_suggestion = page.get("visual_suggestion", "")
        narrative_role = page.get("narrative_role", "")
        one_takeaway = page.get("one_takeaway", "")

        lines.append(f"### 第 {pnum} 页 · {ptype_cn}")
        lines.append("")
        lines.append(f"- **页面类型**：{ptype_cn}")
        lines.append(f"- **标题**：{headline}")
        if subhead:
            lines.append(f"- **副标题**：{subhead}")
        if narrative_role:
            lines.append(f"- **叙事角色**：{narrative_role}")
        if one_takeaway:
            lines.append(f"- **本页收获**：{one_takeaway}")
        lift_rate = page.get("lift_rate") or tc.get("lift_rate")
        if lift_rate:
            lines.append(f"- **抬机率**：{lift_rate}")

        if table_data:
            headers = table_data.get("headers", [])
            rows = table_data.get("rows", [])
            lines.append("- **表格内容**：")
            lines.append("")
            if headers:
                header_line = "| " + " | ".join(str(h) for h in headers) + " |"
                sep_line = "|" + "|".join(["---"] * len(headers)) + "|"
                lines.append(header_line)
                lines.append(sep_line)
            for row in rows:
                lines.append("| " + " | ".join(str(c) for c in row) + " |")
            lines.append("")
        elif body:
            body_format = tc.get("body_format", "bullets")
            lines.append(f"- **正文形态**：{body_format}")
            lines.append("- **正文**：")
            if body_format in ("paragraph", "quote", "data") and len(body) <= 2:
                for b in body:
                    lines.append(f"  {b}")
            else:
                for b in body:
                    lines.append(f"  - {b}")
            lines.append("")

        speaker_notes = page.get("speaker_notes", "")
        if speaker_notes:
            lines.append("- **🎙️ 演讲备注 (Speaker Notes)**：")
            lines.append(f"  > {speaker_notes.replace(chr(10), chr(10) + '  > ')}")
            lines.append("")

        lines.append(f"- **配图/画面**：{visual_suggestion}")
        lines.append("")
        lines.append("---")
        lines.append("")

    return "\n".join(lines)


def parse_review_md(md_text: str) -> Dict[str, Any]:
    """
    解析 plan_for_review.md，返回结构化数据。
    返回: { "meta": {...}, "style": {...}, "pages": [ {...}, ... ] }
    """
    pages = []
    current_page = None
    in_table = False
    table_rows = []
    table_headers = None

    # 提取整体设计（简单正则）
    content_match = re.search(r"\|\s*内容源\s*\|\s*(.+?)\s*\|", md_text)
    template_match = re.search(r"\|\s*模板\s*\|\s*(.+?)\s*\|", md_text)
    palette_match = re.search(r"\|\s*配色\s*\|\s*(.+?)\s*\|", md_text)
    logo_match = re.search(r"\|\s*Logo\s*\|\s*(.+?)\s*\|", md_text)
    style_match = re.search(r"\|\s*风格\s*\|\s*(.+?)\s*\|", md_text)

    meta = {
        "content_file": content_match.group(1).strip() if content_match else "",
        "template_file": template_match.group(1).strip() if template_match else None,
        "logo_file": logo_match.group(1).strip() if logo_match else None,
    }
    if meta.get("template_file") == "无（AI 自动设计）":
        meta["template_file"] = None
    if meta.get("logo_file") == "未使用":
        meta["logo_file"] = None

    style = {
        "palette": [],
        "description": style_match.group(1).strip() if style_match else "",
    }
    if palette_match:
        pstr = palette_match.group(1).strip()
        if pstr and pstr != "（自动）":
            style["palette"] = [s.strip() for s in re.findall(r"#[0-9A-Fa-f]{6}", pstr)]
            if not style["palette"]:
                style["palette"] = [s.strip() for s in pstr.split(",") if s.strip()]

    # 按页解析：匹配 ### 第 N 页 · 类型 及其后内容块
    type_map = {
        "封面": "cover", "章节": "section", "内容": "content",
        "金句": "hero", "呼吸": "breathing", "目录": "toc", "表格": "table",
        "数据": "data", "流程": "flowchart", "框架": "framework",
        "对比": "comparison", "封底": "ending",
    }

    page_blocks = re.findall(
        r"###\s*第\s*(\d+)\s*页\s*·\s*(\S+)\s*\n\n(.*?)(?=\n###\s*第|\Z)",
        md_text,
        re.DOTALL,
    )

    for pnum_str, ptype_cn, block in page_blocks:
        pnum = int(pnum_str)
        ptype = type_map.get(ptype_cn, "content")
        headline = ""
        subhead = ""
        narrative_role = ""
        one_takeaway = ""
        lift_rate = ""
        body_format = "bullets"
        body = []
        table_data = None
        visual_suggestion = ""
        speaker_notes_lines = []

        in_body = False
        in_notes = False
        for raw_line in block.split("\n"):
            line = raw_line.rstrip()
            if re.match(r"^-\s*\*\*标题\*\*[：:]\s*", line):
                headline = re.sub(r"^-\s*\*\*标题\*\*[：:]\s*", "", line).strip()
            elif re.match(r"^-\s*\*\*副标题\*\*[：:]\s*", line):
                subhead = re.sub(r"^-\s*\*\*副标题\*\*[：:]\s*", "", line).strip()
            elif re.match(r"^-\s*\*\*叙事角色\*\*[：:]\s*", line):
                narrative_role = re.sub(r"^-\s*\*\*叙事角色\*\*[：:]\s*", "", line).strip()
            elif re.match(r"^-\s*\*\*本页收获\*\*[：:]\s*", line):
                one_takeaway = re.sub(r"^-\s*\*\*本页收获\*\*[：:]\s*", "", line).strip()
            elif re.match(r"^-\s*\*\*抬机率\*\*[：:]\s*", line):
                lift_rate = re.sub(r"^-\s*\*\*抬机率\*\*[：:]\s*", "", line).strip()
            elif re.match(r"^-\s*\*\*正文形态\*\*[：:]\s*", line):
                body_format = re.sub(r"^-\s*\*\*正文形态\*\*[：:]\s*", "", line).strip()
            elif line.strip() == "- **正文**：" or line.strip() == "- **正文**: ":
                in_body = True
                in_notes = False
            elif line.strip().startswith("- **🎙️ 演讲备注"):
                in_body = False
                in_notes = True
            elif in_body and re.match(r"^\s+-\s+", line) and "**" not in line[:20]:
                body.append(re.sub(r"^\s+-\s+", "", line).strip())
            elif in_body and re.match(r"^\s{2,}\S", line) and body_format in ("paragraph", "quote", "data", "mixed") and not line.strip().startswith("-"):
                body.append(line.strip())
            elif in_notes and re.match(r"^\s*>\s+", line):
                speaker_notes_lines.append(re.sub(r"^\s*>\s+", "", line))
            elif "|" in line and re.match(r"^\|", line):
                in_body = False
                in_notes = False
                cells = [c.strip() for c in line.split("|")[1:-1] if c.strip()]
                if not cells or all(c.replace("-", "").strip() == "" for c in cells):
                    continue
                if cells:
                    if not table_data:
                        table_data = {"headers": cells, "rows": []}
                    else:
                        table_data["rows"].append(cells)
            elif re.match(r"^-\s*\*\*配图/画面\*\*[：:]\s*", line):
                in_body = False
                in_notes = False
                visual_suggestion = re.sub(r"^-\s*\*\*配图/画面\*\*[：:]\s*", "", line).strip()
            elif line.strip() != "":
                # If we are not in notes or body, don't clear flags for empty lines, but clear for other markers
                pass

        # 正文去重（保持顺序），避免如 P18 出现「核心命题」重复两遍
        body = list(dict.fromkeys(body))

        page_dict = {
            "page_num": pnum,
            "type": ptype,
            "text_content": {
                "headline": headline,
                "subhead": subhead,
                "body_format": body_format,
                "body": body,
                **({"table_data": table_data} if table_data else {}),
            },
            "visual_suggestion": visual_suggestion,
            "speaker_notes": "\n".join(speaker_notes_lines) if speaker_notes_lines else ""
        }
        if narrative_role:
            page_dict["narrative_role"] = narrative_role
        if one_takeaway:
            page_dict["one_takeaway"] = one_takeaway
        if lift_rate:
            page_dict["lift_rate"] = lift_rate
        pages.append(page_dict)

    pages.sort(key=lambda p: p["page_num"])
    return {"meta": meta, "style": style, "pages": pages}


def _generate_visual_prompt_for_page(
    page: Dict,
    style_config: Dict,
    design_system: str,
    client,
    model_fallback: List[str],
) -> str:
    """对单页调用 LLM 生成 visual_prompt"""
    from .llm_client import chat_completion_with_fallback

    ptype = page.get("type", "content")
    tc = page.get("text_content", {})
    headline = tc.get("headline", "")
    subhead = tc.get("subhead", "")
    body = list(dict.fromkeys(tc.get("body") or []))  # 去重，防止 AI 生图时渲染重复项
    visual_suggestion = page.get("visual_suggestion", "")

    palette = style_config.get("palette", [])
    if len(palette) >= 2:
        color_constraint = f"Palette: {', '.join(palette[:3])}"
    else:
        color_constraint = ""

    type_instructions = {
        "cover": "【COVER】Full-screen immersive. Title massive and centered. High-impact visual anchor.",
        "section": "【SECTION】Minimalist chapter divider. Section title as sole focus.",
        "hero": "【HERO】Massive typography for core message. Strong visual impact.",
        "content": "【CONTENT】Structured information. Bento grids. Balance text with visual.",
        "flowchart": "【FLOWCHART】Process diagram. Left-to-right or top-to-bottom flow with clear nodes and arrows. Each body item is a step/node. Input→Process→Output style. Professional flowchart aesthetic.",
        "framework": "【FRAMEWORK】Hierarchy or pyramid diagram. Layered structure (e.g. 1+N+X). Each layer clearly labeled. Modern consulting-style framework visualization.",
        "comparison": "【COMPARISON】Contrast diagram. Two trends or forces (e.g. Attention↘ vs Content↗). Crossing curves or side-by-side comparison. Clear visual contrast.",
        "ending": "【ENDING】Simple, memorable. Clean background, centered text.",
    }
    type_inst = type_instructions.get(ptype, "【CONTENT】Structured slide.")

    body_text = "\n".join(f"Text {i+1}: \"{b.lstrip('-•* ').strip()}\"" for i, b in enumerate(body[:6])) if body else ""

    prompt = f"""Generate a detailed image-generation prompt for a PPT slide (16:9, for Gemini/Nano Banana 2).

{design_system}
{color_constraint}

Page type: {ptype.upper()}
Instruction: {type_inst}

Text to display (render exactly, do not translate Chinese):
- Headline: "{headline}"
- Subhead: "{subhead}"
{'- Body items:\n' + body_text if body_text else ''}

Visual/imagery direction from human: {visual_suggestion}

Output: A single, detailed English prompt string for image generation. No explanation. Include: background, layout, typography placement. CRITICAL: Render each body item EXACTLY ONCE (no duplicates). You may use subtle list markers (like small dots) ONLY if formatting a list of multiple small points; otherwise, do not use bullet points for diagrams or frameworks. CRITICAL negative constraints: no logos, no watermarks, NO black blocks, NO solid black rectangles, NO empty black corners - use seamless full-bleed composition extending to all edges."""

    try:
        resp = chat_completion_with_fallback(
            client, model_fallback=model_fallback,
            messages=[
                {"role": "system", "content": "You are a prompt engineer for PPT slide image generation. Output only the prompt string."},
                {"role": "user", "content": prompt},
            ],
            temperature=0.6,
        )
        return resp.choices[0].message.content.strip()
    except Exception as e:
        logger.error(f"生成 visual_prompt 失败 (P{page.get('page_num')}): {e}")
        return f"Professional PPT slide. {ptype}. Headline: {headline}. Style: {visual_suggestion}."


def derive_technical_plan(
    parsed: Dict,
    project_dir: str,
    content_file: str,
    api_key: str,
    api_base: Optional[str] = None,
    model_fallback: Optional[List[str]] = None,
) -> Dict:
    """
    从解析后的 MD 数据，生成完整的 plan.json 结构（含 visual_prompt）。
    需要调用 LLM 为每页生成 visual_prompt（表格页除外）。
    """
    from openai import OpenAI
    from .llm_client import MODEL_FALLBACK_CHAIN

    model_fallback = model_fallback or MODEL_FALLBACK_CHAIN
    client = OpenAI(
        api_key=api_key,
        base_url=api_base or "https://generativelanguage.googleapis.com/v1beta/openai",
        timeout=120.0,
        max_retries=3,
    )

    meta = parsed.get("meta", {})
    style = parsed.get("style", {})
    pages = parsed.get("pages", [])

    meta["project_dir"] = project_dir
    meta["content_file"] = content_file
    meta["project_name"] = Path(project_dir).name
    if not meta.get("template_file"):
        meta["template_file"] = None
    if not meta.get("logo_file"):
        meta["logo_file"] = None

    style_config = {
        "description": style.get("description", "Professional presentation"),
        "palette": style.get("palette", ["#1a1a2e", "#16213e", "#0f3460"]),
        "mode": "ai_minting",
    }
    design_system = f"Global Style: {style_config['description']}. Palette: {', '.join(style_config.get('palette', []))}."

    layout_map = {
        "cover": "full_screen_immersive",
        "section": "minimalist_hero",
        "hero": "minimalist_hero",
        "breathing": "minimalist_hero",
        "content": "left_text_right_visual",
        "flowchart": "flowchart_diagram",
        "framework": "framework_diagram",
        "comparison": "comparison_diagram",
        "ending": "centered_headline",
        "table": "table_dominant",
    }

    slides = []
    for i, page in enumerate(pages):
        pnum = page["page_num"]
        ptype = page["type"]
        tc = page.get("text_content", {}).copy()
        table_data = tc.get("table_data")

        slide = {
            "page_num": pnum,
            "section_title": page.get("section_title", ""),
            "type": ptype,
            "title": tc.get("headline", ""),
            "text_content": tc,
            "layout": layout_map.get(ptype, "left_text_right_visual"),
            "logo_path": meta.get("logo_file"),
            "logo_location": "Top-Right",
            "style_config": style_config,
        }
        if page.get("speaker_notes"):
            slide["speaker_notes"] = page["speaker_notes"]

        if table_data:
            slide["table_data"] = table_data
            slide["visualization"] = "table"
            slide["visual_prompt"] = "DATA_VISUALIZATION_PLACEHOLDER"
            slide["use_data_visualizer"] = True
        else:
            vp = _generate_visual_prompt_for_page(
                page, style_config, design_system, client, model_fallback
            )
            slide["visual_prompt"] = vp
            slide["reference_image"] = None

        slides.append(slide)
        logger.info(f"  P{pnum} [{ptype}] visual_prompt 已生成")

    # 追加背景页
    slides.append({
        "page_num": len(slides) + 1,
        "type": "background_only",
        "title": "Pure Background",
        "visual_prompt": "Clean gradient background matching the presentation style. No text, no logos.",
        "reference_image": None,
        "style_config": style_config,
    })

    return {"meta": meta, "slides": slides}
