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
        "> 💡 **AI 风格灵感库 (Style Inspirations)**",
        "> 觉得当前风格太单调？您可以尝试将上方表格中的【风格】改为以下任意一种，或者任意混合：",
        "> - **液态玻璃 (liquid_glass)**：高级科技风，Bento 网格，半透明毛玻璃，适合产品发布/科技公司。",
        "> - **时尚杂志 (magazine_editorial)**：优雅衬线体，电影级留白排版，适合品牌宣发/人物/美妆。",
        "> - **新中式 / 国潮 (traditional_chinese)**：水墨留白，朱红青绿点缀，圆窗隐喻，适合文化/政务/茶饮。",
        "> - **日式美学 (japanese_aesthetic)**：侘寂风，大地色系，极简非对称，适合文艺/极简生活方式。",
        "> - **新粗野主义 (neo_brutalism)**：亮色高对比，黑色粗边框，大胆前卫，适合年轻态/设计感/快消。",
        "> - **3D粘土风 (soft_3d_clay)**：可爱，马卡龙色系，膨胀 3D 软材质，适合轻松活泼的汇报/母婴/游戏。",
        "> - **全息镭射 (holographic_chrome)**：Y2K千禧风，液态金属发光渐变，适合潮流/潮牌/前卫艺术。",
        "> - **黑金奢华 (dark_luxury)**：高级定制，深色背景+暗金点缀，适合金融/房地产/奢侈品。",
        "> - **学术风 (academic_paper)**：严谨白底，经典衬线体，规范网格，适合论文答辩/科研项目。",
        "> - *或自由描述*：例如“赛博朋克风，加入中国龙元素”、“黑白复古报纸排版”等。AI 将动态适应！",
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
        "hero": "核心/金句",
        "quote": "名人金句",
        "infographic": "信息图",
        "breathing": "呼吸",
        "toc": "目录",
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
        lines.append(f"- **标题**：{headline}")
        if subhead:
            lines.append(f"- **副标题**：{subhead}")
        
        # Metadata fields are omitted from review markdown to keep it clean for the user
        # They will still exist in the underlying data structure and plan.json
        # lines.append(f"- **页面类型**：{ptype_cn}")
        # if narrative_role:
        #     lines.append(f"- **叙事角色**：{narrative_role}")
        # if one_takeaway:
        #     lines.append(f"- **本页收获**：{one_takeaway}")
        # lift_rate = page.get("lift_rate") or tc.get("lift_rate")
        # if lift_rate:
        #     lines.append(f"- **抬机率**：{lift_rate}")

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
            # We don't need to show body format to the user either
            # body_format = tc.get("body_format", "bullets")
            # lines.append(f"- **正文形态**：{body_format}")
            
            body_format = tc.get("body_format", "bullets")
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

        native_images = page.get("native_images", [])
        if not native_images and page.get("native_image"):
            native_images = [page.get("native_image")]
            
        if native_images:
            lines.append("- **📥 原生图片**：")
            for idx, img in enumerate(native_images):
                path = img.get('path', 'unknown_path')
                role = img.get('semantic_role', '')
                bbox = img.get('bounding_box', {})
                if bbox:
                    bbox_str = f"left: {bbox.get('left')}, top: {bbox.get('top')}, width: {bbox.get('width')}, height: {bbox.get('height')}"
                else:
                    bbox_str = img.get('layout', 'center')
                # 简化格式，去掉多余的信息和标签，只保留角色、预览和位置信息
                import os
                
                # Make sure the path is correct relative to content_file when generating review md
                # Or keep it as absolute path
                content_file = meta.get("content_file", "")
                base_dir = os.path.dirname(os.path.abspath(content_file)) if content_file else ""
                
                if not os.path.isabs(path) and base_dir:
                    abs_path = os.path.normpath(os.path.join(base_dir, path))
                    if os.path.exists(abs_path):
                        path = abs_path
                
                img_src = f"file://{path}" if os.path.isabs(path) else path
                lines.append(f"  {idx+1}. {role} <img src=\"{img_src}\" height=\"40\" style=\"vertical-align: middle;\" /> (`{bbox_str}`)")
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

    # 提取整体设计（处理可能包含<br>的情况）
    content_match = re.search(r"\|\s*(?:<br>)?内容源\s*\|\s*(?:<br>)?(.+?)\s*\|", md_text)
    template_match = re.search(r"\|\s*(?:<br>)?模板\s*\|\s*(?:<br>)?(.+?)\s*\|", md_text)
    palette_match = re.search(r"\|\s*(?:<br>)?配色\s*\|\s*(?:<br>)?(.+?)\s*\|", md_text)
    logo_match = re.search(r"\|\s*(?:<br>)?Logo\s*\|\s*(?:<br>)?(.+?)\s*\|", md_text)
    fonts_match = re.search(r"\|\s*(?:<br>)?字体\s*\|\s*(?:<br>)?(.+?)\s*\|", md_text)
    style_match = re.search(r"\|\s*(?:<br>)?风格\s*\|\s*(?:<br>)?(.+?)\s*\|", md_text)

    meta = {
        "content_file": content_match.group(1).strip() if content_match else "",
        "template_file": template_match.group(1).strip() if template_match else None,
        "logo_file": logo_match.group(1).strip() if logo_match else None,
    }
    if meta.get("template_file") == "无（AI 自动设计）":
        meta["template_file"] = None
    if meta.get("logo_file") == "未使用":
        meta["logo_file"] = None

    # 解析字体列表
    fonts = []
    if fonts_match:
        fstr = fonts_match.group(1).strip()
        if fstr and fstr not in ("（自动）", "自动"):
            fonts = [f.strip() for f in fstr.split(",") if f.strip()]

    style = {
        "palette": [],
        "fonts": fonts,
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
        "金句": "hero", "核心/金句": "hero", "名人金句": "quote", "呼吸": "breathing", "目录": "toc",
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
        # 页面类型不再在 markdown 中体现，从原始数据或者推测，或者默认为 content
        # 我们需要保留它如果原本就在 JSON 中，但因为 plan_for_review 会被重新解析生成 JSON，
        # 所以我们需要尽量保证不要丢失信息。既然我们在 title 里写了 "### 第 X 页 · 页面类型"
        # 我们可以从标题里提取类型
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
        native_images = []

        in_body = False
        in_notes = False
        in_native_images = False
        
        for raw_line in block.split("\n"):
            line = raw_line.rstrip()
            if re.match(r"^-\s*\*\*标题\*\*\s*[：:]\s*", line):
                headline = re.sub(r"^-\s*\*\*标题\*\*\s*[：:]\s*", "", line).strip()
                in_native_images = False
            elif re.match(r"^-\s*\*\*副标题\*\*\s*[：:]\s*", line):
                subhead = re.sub(r"^-\s*\*\*副标题\*\*\s*[：:]\s*", "", line).strip()
                in_native_images = False
            # 这些字段已在写入时被注释掉，但为了向后兼容解析，仍保留
            elif re.match(r"^-\s*\*\*叙事角色\*\*\s*[：:]\s*", line):
                narrative_role = re.sub(r"^-\s*\*\*叙事角色\*\*\s*[：:]\s*", "", line).strip()
                in_native_images = False
            elif re.match(r"^-\s*\*\*本页收获\*\*\s*[：:]\s*", line):
                one_takeaway = re.sub(r"^-\s*\*\*本页收获\*\*\s*[：:]\s*", "", line).strip()
                in_native_images = False
            elif re.match(r"^-\s*\*\*抬机率\*\*\s*[：:]\s*", line):
                lift_rate = re.sub(r"^-\s*\*\*抬机率\*\*\s*[：:]\s*", "", line).strip()
                in_native_images = False
            elif re.match(r"^-\s*\*\*正文形态\*\*\s*[：:]\s*", line):
                body_format = re.sub(r"^-\s*\*\*正文形态\*\*\s*[：:]\s*", "", line).strip()
                in_native_images = False
            elif re.match(r"^-\s*\*\*正文\*\*\s*[：:]\s*", line) or line.strip() == "- **正文**：" or line.strip() == "- **正文**: ":
                in_body = True
                in_notes = False
                in_native_images = False
            elif line.strip().startswith("- **🎙️ 演讲备注"):
                in_body = False
                in_notes = True
                in_native_images = False
            elif line.strip().startswith("- **📥 原生图片"):
                in_body = False
                in_notes = False
                in_native_images = True
            elif in_body and re.match(r"^\s+-\s+", line):
                # 移除开头的空格和短横线，如果遇到粗体，保留粗体文本内容
                cleaned_line = re.sub(r"^\s+-\s+", "", line).strip()
                # 也可以直接把粗体星号替换掉
                cleaned_line = cleaned_line.replace("**", "")
                body.append(cleaned_line)
            elif in_body and re.match(r"^\s{2,}\S", line) and body_format in ("paragraph", "quote", "data", "mixed") and not line.strip().startswith("-"):
                body.append(line.strip())
            elif in_notes and re.match(r"^\s*>\s+", line):
                speaker_notes_lines.append(re.sub(r"^\s*>\s+", "", line))
            elif in_native_images and re.match(r"^\s*\d+\.\s+", line):
                # 支持四种格式：
                # 1. 带有 html img 标签的精简格式: role <img src="file://path" ... /> (`left: ...`)
                # 2. 带有 html img 标签: role <img src="file://path" ... /> (`bounding_box`: ...)
                # 3. 带有 markdown 预览图片链接: ![role](path) (`bounding_box`: ...)
                # 4. 带有 markdown 普通链接: [filename](path) -> role (`bounding_box`: ...)
                # 5. 只有路径的旧格式: `path` -> role (`bounding_box`: ...)
                
                # 1. & 2. 尝试匹配 HTML 格式（支持包含或不包含 'bounding_box:'）
                # 兼容带有 file:// 协议和不带的普通路径
                img_match = re.search(r"^(.*?)\s*<img src=\"(?:file://)?([^\"]+)\".*?\/>\s*\(`(?:bounding_box`:\s*)?(.*?)`?\)", re.sub(r"^\s*\d+\.\s+", "", line))
                if img_match:
                    role = img_match.group(1).strip()
                    path = img_match.group(2).strip()
                    bbox_str = img_match.group(3).strip()
                    if bbox_str.endswith(')'): # handle optional backticks
                        bbox_str = bbox_str[:-1].strip()
                    if bbox_str.endswith('`'):
                        bbox_str = bbox_str[:-1].strip()
                        
                    # Handle paths that don't have file:// but still got matched into group(2)
                    if path.startswith("file://"):
                        path = path[7:]
                else:
                    img_match = re.search(r"!\[(.*?)\]\((.*?)\)\s*\(`bounding_box`:\s*(.*?)\)", line)
                    if img_match:
                        role = img_match.group(1).strip()
                        path = img_match.group(2).strip()
                        bbox_str = img_match.group(3).strip()
                    else:
                        img_match = re.search(r"\[([^\]]+)\]\(([^)]+)\)\s*->\s*(.*?)\s*\(`bounding_box`:\s*(.*?)\)", line)
                        if img_match:
                            path = img_match.group(2).strip()
                            role = img_match.group(3).strip()
                            bbox_str = img_match.group(4).strip()
                        else:
                            img_match = re.search(r"`([^`]+)`\s*->\s*(.*?)\s*\(`bounding_box`:\s*(.*?)\)", line)
                            if img_match:
                                path = img_match.group(1).strip()
                                role = img_match.group(2).strip()
                                bbox_str = img_match.group(3).strip()
                
                if img_match:
                    bbox = {}
                    # Try to parse left, top, width, height from bbox_str
                    for part in bbox_str.split(","):
                        if ":" in part:
                            k, v = part.split(":", 1)
                            try:
                                bbox[k.strip()] = float(v.strip())
                            except ValueError:
                                pass
                                
                    # Attempt to resolve relative paths
                    import os
                    content_file = meta.get("content_file", "")
                    base_dir = os.path.dirname(os.path.abspath(content_file)) if content_file else ""
                    if not os.path.isabs(path) and base_dir:
                        abs_path = os.path.normpath(os.path.join(base_dir, path))
                        if os.path.exists(abs_path):
                            path = abs_path
                    elif not os.path.exists(path):
                        # Attempt to resolve if it's just a filename
                        filename = os.path.basename(path)
                        if base_dir:
                            abs_path = os.path.normpath(os.path.join(base_dir, filename))
                            if os.path.exists(abs_path):
                                path = abs_path
                    
                    native_images.append({
                        "path": path,
                        "semantic_role": role,
                        "bounding_box": bbox
                    })
            elif "|" in line and re.match(r"^\|", line):
                in_body = False
                in_notes = False
                in_native_images = False
                cells = [c.strip() for c in line.split("|")[1:-1] if c.strip()]
                if not cells or all(c.replace("-", "").strip() == "" for c in cells):
                    continue
                if cells:
                    if not table_data:
                        table_data = {"headers": cells, "rows": []}
                    else:
                        table_data["rows"].append(cells)
            elif re.match(r"^-\s*\*\*配图/画面\*\*\s*[：:]\s*", line):
                in_body = False
                in_notes = False
                in_native_images = False
                visual_suggestion = re.sub(r"^-\s*\*\*配图/画面\*\*\s*[：:]\s*", "", line).strip()
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
        if native_images:
            page_dict["native_images"] = native_images
            
        pages.append(page_dict)

    pages.sort(key=lambda p: p["page_num"])
    return {"meta": meta, "style": style, "pages": pages}


def _generate_visual_prompt_for_page(
    page: Dict,
    style_config: Dict,
    design_system: str,
    client,
    model_fallback: List[str],
    outline_summary: str = "",
) -> str:
    """对单页调用 LLM 生成 visual_prompt"""
    from .llm_client import chat_completion_with_fallback

    ptype = page.get("type", "content")
    tc = page.get("text_content", {})
    headline = tc.get("headline", "")
    subhead = tc.get("subhead", "")
    body = list(dict.fromkeys(tc.get("body") or []))  # 去重，防止 AI 生图时渲染重复项
    visual_suggestion = page.get("visual_suggestion", "")

    type_instructions = {
        "cover": "【COVER】Full-screen immersive. Title massive and centered. High-impact visual anchor. Use a symbolic, high-end 3D object or cinematic scene as the main visual anchor.",
        "section": "【SECTION】Minimalist chapter divider. Section title as sole focus. Create a sense of 'pause' or 'new chapter'.",
        "hero": "【HERO】Massive typography for core message. Strong visual impact. Typography (Font, Weight, Positioning) MUST match the global style exactly.",
        "quote": "【QUOTE CARD】Wide Quote Card. 1/3 of the space for a realistic portrait with a subtle gradient transition, 2/3 for a massive quotation text with an oversized faint quotation mark in the background.",
        "infographic": "【INFOGRAPHIC / HIGH DENSITY】Modular and structured layout. Use a Bento Grid or central hub connector design. Organize complex information into clear, distinct sections (cards/glass panes). Use icons and visual hierarchy to manage high information density while keeping it clean and professional.",
        "content": "【CONTENT】Structured information. Bento grids. Balance text with visual. Ensure body text is legible.",
        "toc": "【TOC】Structured and clean grid or list layout. Use icons or large numbers for each chapter.",
        "data": "【DATA】Focus on the chart/number. Make key numbers huge. Sleek, modern data visualization.",
        "flowchart": "【FLOWCHART】Process or progression. Use abstract, balanced layouts that imply flow without relying on rigid literal arrows. Avoid generic templates.",
        "framework": "【FRAMEWORK】Logical structure or model. Use sleek, modern, abstract structural compositions. DO NOT force literal pyramids or rigid hierarchies unless explicitly requested.",
        "comparison": "【COMPARISON】Contrast or juxtaposition. Use balanced, side-by-side or contrasting abstract elements. Avoid overly literal or cluttered intersecting curves.",
        "ending": "【ENDING】Simple, memorable. Clean background, centered text.",
        "breathing": "【BREATHING】Extreme minimalism. A single question, number, or half-screen whitespace with a transition phrase.",
    }
    type_inst = type_instructions.get(ptype, "【CONTENT】Structured slide.")

    body_text = "\n".join(f"Text {i+1}: \"{b.lstrip('-•* ').strip()}\"" for i, b in enumerate(body[:6])) if body else ""

    global_context_block = f"""【Global Deck Context — for visual consistency across ALL slides】
{outline_summary}
""" if outline_summary else ""

    prompt = f"""Generate a detailed image-generation prompt for a PPT slide (16:9, for Gemini/Nano Banana 2).

{design_system}

{global_context_block}Page type: {ptype.upper()}
Instruction: {type_inst}

Text to display (render exactly, do not translate Chinese):
- Headline: "{headline}"
- Subhead: "{subhead}"
{'- Body items:\n' + body_text if body_text else ''}

Initial Visual Suggestion: {visual_suggestion}

【STYLE ADAPTATION RULE (CRITICAL)】
The "Initial Visual Suggestion" above describes the desired metaphor or object, but its specific stylistic vibe may be outdated because the Global Style was updated by the user. 
You MUST ADAPT the subject matter/metaphor from the Initial Visual Suggestion so that it is rendered STRICTLY in the exact aesthetic of the Global Style and Color Palette. 
For example, if the Suggestion says "a bright sunny corporate office" but the Global Style is "Cyberpunk Dark Neon", you MUST generate "a cyberpunk dark neon corporate office with glowing accents". 
The Global Style ALWAYS OVERRIDES the stylistic implications of the Initial Visual Suggestion.

Output: A single, detailed English prompt string for image generation. No explanation. Include: background, layout, typography placement.
CRITICAL consistency rules:
- This slide is PART OF A DECK. Its background color, font style, shape language, and decorative elements MUST be visually identical to the design system above. Do NOT deviate.
- Render each body item EXACTLY ONCE (no duplicates).
- You may use subtle list markers (like small dots) ONLY if formatting a list of multiple small points; otherwise, do not use bullet points for diagrams or frameworks.
- No logos, no watermarks, NO black blocks, NO solid black rectangles, NO empty black corners — use seamless full-bleed composition extending to all edges.
CRITICAL AVOIDANCE: If the visual direction mentions leaving space for a picture/image (e.g., "leave the right side empty", "leave space in the middle"), you MUST NOT generate any text, graphics, or complex visual elements in that specific area. Leave it as a solid color or a very simple, clean gradient background so a real image can be pasted over it later."""

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

    fonts = style.get("fonts", [])
    style_config = {
        "description": style.get("description", "Professional presentation"),
        "palette": style.get("palette", ["#1a1a2e", "#16213e", "#0f3460"]),
        "fonts": fonts,
        "mode": "ai_minting",
    }
    palette = style_config.get("palette", [])
    if len(palette) >= 2:
        color_constraint = (
            f"Background base: {palette[0]}/{palette[1]}, "
            f"Title color: {palette[2] if len(palette) > 2 else '#FFFFFF'}, "
            f"Body text: {palette[3] if len(palette) > 3 else '#FFFFFF'}"
        )
    elif palette:
        color_constraint = f"Palette: {', '.join(palette)}"
    else:
        color_constraint = ""
    fonts_constraint = f"Fonts: {', '.join(fonts)}." if fonts else ""
    design_system = (
        f"【Visual Design System (STRICT)】\n"
        f"1. **Global Style**: {style_config['description']}\n"
        f"2. **Color Palette (MANDATORY)**: {color_constraint}\n"
        f"{f'3. **Typography**: {fonts_constraint}' if fonts_constraint else ''}\n"
        f"4. **Consistency (CRITICAL)**: ALL slides MUST use the exact same fonts, colors, shape language, and decorative elements. "
        f"Every slide must look like it belongs to the same deck — same visual vocabulary, same color scheme."
    )

    layout_map = {
        "cover": "full_screen_immersive",
        "section": "minimalist_hero",
        "hero": "minimalist_hero",
        "quote": "wide_quote_card",
        "breathing": "minimalist_hero",
        "content": "left_text_right_visual",
        "flowchart": "flowchart_diagram",
        "framework": "framework_diagram",
        "comparison": "comparison_diagram",
        "ending": "centered_headline",
    }

    # 生成全局大纲摘要，用于给每页的 visual prompt 提供整体一致性上下文
    outline_summary = "\n".join([
        f"- P{p['page_num']} ({p.get('type','content')}): {p.get('text_content', {}).get('headline', '')}"
        for p in pages[:12]
    ])
    if len(pages) > 12:
        outline_summary += "\n... (more slides)"

    slides = []
    for i, page in enumerate(pages):
        pnum = page["page_num"]
        ptype = page["type"]
        tc = page.get("text_content", {}).copy()
        table_data = tc.get("table_data")

        native_images = page.get("native_images", [])

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

        if table_data and page.get("visualization", "") in ("bar", "line", "pie"):
            slide["table_data"] = table_data
            slide["visualization"] = page.get("visualization", "")
            slide["visual_prompt"] = "DATA_VISUALIZATION_PLACEHOLDER"
            slide["use_data_visualizer"] = True
        else:
            if table_data:
                slide["table_data"] = table_data
            vp = _generate_visual_prompt_for_page(
                page, style_config, design_system, client, model_fallback,
                outline_summary=outline_summary,
            )
            slide["visual_prompt"] = vp
            slide["reference_image"] = None
            
        if native_images:
            slide["native_images"] = native_images
            
        slides.append(slide)
        logger.info(f"  P{pnum} [{ptype}] visual_prompt 已生成")

    # 追加背景页
    slides.append({
        "page_num": len(slides) + 1,
        "type": "background_only",
        "title": "Pure Background",
        "visual_prompt": f"A clean, minimal, empty 16:9 background matching the {style_config['description']} style. Use the same color palette: {', '.join(style_config.get('palette', []))}. DO NOT generate any text, typography, logos, charts, or complex structural elements. It must be a pure, elegant gradient or subtle textured background suitable for placing new content on top.",
        "reference_image": None,
        "style_config": style_config,
    })

    return {"meta": meta, "slides": slides}
