"""
人类可审阅的 PPT 计划：plan_for_review.md 的生成与解析

- build_review_md: 从 narrative_outline + style_config 生成人类可读的 MD
- parse_review_md: 从 MD 解析回结构化数据
- derive_technical_plan: 从解析结果 + LLM 生成完整 plan.json（含 visual_prompt）
"""
import json
import logging
import re
import os
from pathlib import Path
from typing import Dict, List, Optional, Any

logger = logging.getLogger(__name__)

REVIEW_MD_FILENAME = "visual_plan.md"


def build_master_plan_from_content_plan(
    content_md_path: str,
    style_config: Dict,
    meta: Dict,
    manifesto: str = "",
    per_slide_suggestions: Dict[int, str] = None,
) -> str:
    """
    从 content_plan.md 文件读取内容大纲,结合 style_config 生成完整的 visual_plan.md

    Args:
        content_md_path: content_plan.md 文件路径
        style_config: 风格配置
        meta: 元信息
        manifesto: 视觉主张文本
        per_slide_suggestions: {page_num: visual_suggestion_str} — VisualDirector 为每页生成的视觉描述
    """
    # 读取 content_plan.md 并使用 parse_review_md 正确解析
    with open(content_md_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # 使用 parse_review_md 解析完整内容
    parsed = parse_review_md(content)
    narrative_outline = parsed.get("pages", [])

    # 如果没有解析到任何页面,创建一个默认的
    if not narrative_outline:
        narrative_outline = [{
            "page_num": 1,
            "type": "cover",
            "text_content": {
                "headline": "演示文稿",
                "body": ""
            }
        }]

    # 注入 VisualDirector 为每页生成的 visual_suggestion
    if per_slide_suggestions:
        for page in narrative_outline:
            pnum = page.get("page_num")
            if pnum in per_slide_suggestions:
                page["visual_suggestion"] = per_slide_suggestions[pnum]

    # 调用 build_review_md 生成完整的审阅计划
    return build_review_md(narrative_outline, style_config, meta, manifesto)


def generate_design_manifesto(
    parsed: Dict,
    template_mode: bool,
    client: Any,
    model_fallback: Optional[List[str]] = None
) -> Dict[str, str]:
    """
    使用 LLM 生成 Art Director 风格的 Design System Manifesto，
    用于严格限制生图的方向，消除廉价 AI 感。返回 JSON 格式包含中文提案和英文禁令。
    """
    from .llm_client import chat_completion_with_fallback

    # Extract outline_summary and style_hint from parsed
    pages = parsed.get("pages", [])
    outline_summary = "\n".join([
        f"- P{p.get('page_num', 0)} ({p.get('type','content')}): {p.get('text_content', {}).get('headline', '')}"
        for p in pages[:12]
    ])
    if len(pages) > 12:
        outline_summary += "\n... (more slides)"
        
    style = parsed.get("style", {})
    style_hint = f"Style: {style.get('description', 'Professional')}. Palette: {', '.join(style.get('palette', []))}."

    system_prompt = "你是一位世界顶级的演示文稿设计总监（Art Director）和视觉策略专家。"
    
    template_instruction = ""
    if template_mode:
        template_instruction = "TEMPLATE MODE IS ACTIVE: The design MUST heavily prioritize negative space, subdued/abstract backgrounds, and absolute minimalism so that the generated images can seamlessly sit behind or beside template content without clashing."

    user_prompt = f"""Based on the presentation outline and the requested style, define a Design System Manifesto.

【Inputs】
- Outline Summary:
{outline_summary}

- Global Style Hint:
{style_hint}

{template_instruction}

【Task】
你需要生成一份针对这份 PPT 的“设计总监视觉设计提案”。
1. 你的提案应该用流畅自然、通俗易懂的**中文大白话**（2-3段话）来撰写，就像一位资深设计总监在向客户做提案，解释我们为什么选择这样的色彩策略、情绪氛围，以及整体的视觉方向（拒绝任何塑料感和廉价的AI常见套路）。
2. 同时，针对生图大模型，你需要提供一段**纯英文的严格负向提示词（Negative Prompt / Cliche Bans）**，禁止生成那些陈词滥调（例如发光大脑、3D漏斗、赛博节点等）。
3. 你还需要提供一份**视觉多样性方案（visual_diversity_strategy）**：为这份 PPT 规划 4-6 种不同类别的视觉主体（visual motifs），确保整份 PPT 在统一风格下有足够的视觉丰富性和变化感。

【CRITICAL: chinese_proposal 写作红线】
- 只描述**色彩策略**（为什么选这些颜色、怎么搭配）、**情绪氛围**（整体给人什么感觉）、**方向性的视觉气质**（如"高级感"、"网感"、"克制"等）。
- **绝对禁止**承诺任何具体的视觉技法或元素——例如"3D插画"、"对话气泡"、"贴纸元素"、"手绘风"、"动态粒子"、"霓虹灯效果"等。因为最终的图像由 AI 生图模型自由发挥，你无法保证这些具体技法一定会出现在最终成品中。
- 正确示例：说"视觉上要有活力和张力" ✅，而不是"我们会用3D插画和贴纸" ❌
- 总之：描述"感觉"和"方向"，不要承诺"手段"和"元素"。

【CRITICAL: visual_diversity_strategy 规划原则】
- 分析 Outline 的内容主题，为整份 PPT 规划 4-6 种**不同类别**的视觉主体（visual motifs），让每页的核心视觉元素有充分的变化。
- **鼓励使用具象隐喻**（figurative imagery）：人物剪影、建筑场景、自然景观、物件特写、空间透视等，而不是全部退回到抽象几何体（如纯色石块、立方体、玻璃面板等）。
- 即使内容比较抽象（如哲学话题、商业理念），也应该为每个概念找到一个**具体的视觉锚点**。例如：用"冰川融化"隐喻"不可逆转的改变"、用"灯塔"隐喻"使命"、用"空旷的城市"隐喻"消失"。
- 关键原则：**同一类视觉主体不应连续出现超过 2 页**。如果出现石碑，不应全篇都是石碑；应在下一页切换到不同类别。
- 每种 motif 写一句话描述使用场景。

【Output Format】
你必须且只能输出合法的 JSON 字符串，包含以下三个字段：
{{
  "chinese_proposal": "（这里写2-3段中文大白话的设计提案内容，只谈色彩策略、情绪氛围和方向性气质）",
  "english_cliche_bans": "（这里写纯英文的严格禁止生成的元素清单，例如：NO glowing brains, NO generic 3D funnels...）",
  "visual_diversity_strategy": "（纯英文。列出 4-6 种 visual motifs，每种一句话描述使用场景。例如：1. Solitary human silhouettes against vast landscapes — for slides about individual purpose and reflection. 2. Architectural ruins and empty plazas — for slides about disappearance and absence. ...）"
}}

不要输出任何其他的解释文字、Markdown 代码块符号等。直接输出 JSON。
"""

    try:
        resp = chat_completion_with_fallback(
            client, model_fallback=model_fallback or ["gemini-3.1-pro-preview"],
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.7,
            response_format={"type": "json_object"}
        )
        content = resp.choices[0].message.content.strip()
        if content.startswith("```json"):
            content = content[7:]
        elif content.startswith("```"):
            content = content[3:]
        if content.endswith("```"):
            content = content[:-3]
        
        result = json.loads(content.strip())
        return {
            "chinese_proposal": result.get("chinese_proposal", "现代极简专业风格。我们使用干净的线条和微妙的渐变，结合大面积留白，为您的内容提供一个高级、清晰的展示空间。"),
            "english_cliche_bans": result.get("english_cliche_bans", "No glowing brains, no handshakes, no generic 3D funnels, no floating data."),
            "visual_diversity_strategy": result.get("visual_diversity_strategy", "")
        }
    except Exception as e:
        logger.error(f"Failed to generate Design Manifesto: {e}")
        return {
            "chinese_proposal": "现代极简专业风格。我们使用干净的线条和微妙的渐变，结合大面积留白，为您的内容提供一个高级、清晰的展示空间。",
            "english_cliche_bans": "No glowing brains, no handshakes, no generic 3D funnels, no floating data.",
            "visual_diversity_strategy": ""
        }


def generate_per_slide_visual_suggestions(
    narrative_outline: List[Dict],
    style_config: Dict,
    api_key: str,
    api_base: Optional[str] = None,
) -> Dict[int, str]:
    """
    为每一页生成具体的「配图/画面」人类语言描述（Visual Director 提案）。
    返回 dict: {page_num: visual_suggestion_string}
    这些描述将在 master_plan.md 中供用户审阅，并在 execute 阶段严格遵循。
    """
    from .llm_client import chat_completion_with_fallback, MODEL_FALLBACK_CHAIN
    from openai import OpenAI

    client = OpenAI(api_key=api_key, base_url=api_base or "https://generativelanguage.googleapis.com/v1beta/openai")

    palette = style_config.get("palette", [])
    style_desc = style_config.get("description", "Professional presentation")
    palette_str = ", ".join(palette) if palette else "auto"

    # 构建每页的上下文摘要（给 LLM 参考）
    pages_context = []
    for p in narrative_outline:
        pnum = p.get("page_num", 0)
        ptype = p.get("type", "content")
        tc = p.get("text_content", {})
        headline = tc.get("headline", "")
        subhead = tc.get("subhead", "")
        body = tc.get("body", [])
        table_data = tc.get("table_data")

        ctx = f"P{pnum} [{ptype}] 标题:{headline}"
        if subhead:
            ctx += f" | 副标题:{subhead}"
        if body:
            ctx += f" | 正文:{'; '.join(str(b) for b in body[:3])}"
        if table_data:
            headers = table_data.get("headers", [])
            rows = table_data.get("rows", [])
            ctx += f" | 表格列名: {headers} | 表格行数据: {rows}"
        pages_context.append(ctx)

    pages_text = "\n".join(pages_context)

    system_prompt = (
        "You are a world-class Art Director. "
        "For each slide listed, you must propose a CONCRETE, SPECIFIC visual scene description "
        "in natural Chinese. Be precise — state exact visual metaphors, objects, and composition. "
        "If a slide has TABLE DATA, you MUST describe the exact data points and how they appear visually. "
        "Write for a human to read and confirm — this is the creative brief for image generation."
    )

    user_prompt = f"""【Global Style】
- Style: {style_desc}
- Color Palette: {palette_str}

【Slides to Design — ALL DATA MUST APPEAR IN DESCRIPTION】
{pages_text}

【CRITICAL RULES — VIOLATION WILL PRODUCE WRONG OUTPUT】

For EVERY slide:
- Write 2-4 sentences of concrete Chinese visual description
- Describe EXACT objects, lighting, composition, visual metaphors
- For DATA slides: You MUST include ALL numbers from the table in your description. Do NOT summarize or omit any row.

SPECIFIC EXAMPLES OF CORRECT BEHAVIOR:
- GOOD: "画面中央是一个天平，左边放着标注'5.5万亿（占电商30%）'的金色立方体，右边是标注'6000亿'的巨大红色圆环，天平向右侧倾斜"
- BAD:   "画面中央是一个天平，对比左右两侧的数据差异"

- GOOD: "四个数据卡片并排：'10.74亿（日活）'、'95%（渗透率）'、'18.3亿（抖音）'、'156分钟（时长）'"
- BAD:   "四个数据卡片展示关键指标"

Output format (pure JSON, no markdown):
{{
  "slides": {{
    "1": "配图描述（必须包含所有关键数据）...",
    "2": "配图描述...",
    ...
  }}
}}

JSON only, no explanation:"""

    try:
        response = chat_completion_with_fallback(
            client,
            model="MiniMax-M2.7",
            model_fallback=MODEL_FALLBACK_CHAIN,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.7
        )
        import json, re
        content = response.choices[0].message.content.strip()
        # Extract JSON
        json_match = re.search(r'\{[\s\S]+\}', content)
        if json_match:
            data = json.loads(json_match.group())
            slides_data = data.get("slides", {})
            return {int(k): v for k, v in slides_data.items()}
    except Exception as e:
        logger.error(f"Failed to generate per-slide visual suggestions: {e}")
    return {}


def build_content_review_md(
    narrative_outline: List[Dict],
    meta: Dict,
) -> str:
    """
    从 narrative_outline 生成人类可读的 content_plan.md，仅供内容和逻辑审阅。
    """
    content_file = meta.get("content_file", "")
    lines = [
        "# PPT 内容计划 · 待您确认",
        "",
        "> 请审阅以下大纲内容，可直接编辑本文件修改标题、正文和备注等。",
        "> 确认无误后，运行 `plan-visual` 生成包含视觉风格的完整计划。",
        "",
        "---",
        "",
        "## 一、内容源信息",
        "",
        f"- **内容源**：{content_file}",
        "",
        "---",
        "",
        "## 二、各页大纲预览",
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
        "back": "尾页",
    }

    for page in narrative_outline:
        pnum = page.get("page_num", 0)
        ptype = page.get("type", "content")
        ptype_cn = type_names.get(ptype, ptype)

        tc = page.get("text_content", {})
        headline = tc.get("headline", "") or page.get("title", "")
        subhead = tc.get("subhead", "")
        body_raw = tc.get("body") or []
        # 去重，但要处理可能包含 dict 的情况
        body = []
        seen = set()
        for item in body_raw:
            if isinstance(item, dict):
                # dict 类型直接添加，不去重
                body.append(item)
            else:
                # 字符串类型去重
                if item not in seen:
                    body.append(item)
                    seen.add(item)
        table_data = tc.get("table_data") or page.get("table_data")

        lines.append(f"### 第 {pnum} 页 · {ptype_cn}")
        lines.append("")
        lines.append(f"- **标题**：{headline}")
        if subhead:
            lines.append(f"- **副标题**：{subhead}")

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
                mode = img.get('integration_mode', 'overlay')
                mode_str = "[融合]" if mode == "blend" else "[叠加]"
                bbox = img.get('bounding_box', {})
                if bbox:
                    bbox_str = f"left: {bbox.get('left')}, top: {bbox.get('top')}, width: {bbox.get('width')}, height: {bbox.get('height')}"
                else:
                    bbox_str = img.get('layout', 'center')
                
                content_file = meta.get("content_file", "")
                base_dir = os.path.dirname(os.path.abspath(content_file)) if content_file else ""
                
                if not os.path.isabs(path) and base_dir:
                    abs_path = os.path.normpath(os.path.join(base_dir, path))
                    if os.path.exists(abs_path):
                        path = abs_path
                
                img_src = f"file://{path}" if os.path.isabs(path) else path
                lines.append(f"  {idx+1}. {mode_str} {role} <img src=\"{img_src}\" height=\"40\" style=\"vertical-align: middle;\" /> (`{bbox_str}`)")
            lines.append("")

        lines.append("---")
        lines.append("")

    return "\n".join(lines)


def build_review_md(
    narrative_outline: List[Dict],
    style_config: Dict,
    meta: Dict,
    manifesto: str = "",
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
        "## 二、视觉主张 (Design System Manifesto)",
        "",
        manifesto if manifesto else "> （尚未生成视觉主张，将在 execute 阶段由 Art Director 自动补齐）",
        "",
        "---",
        "",
        "## 三、色彩规范 (Color Palette)",
        "",
    ]
    
    if palette:
        for i, hex_color in enumerate(palette):
            clean_hex = hex_color.replace("#", "").upper()
            if i == 0:
                role = "背景大色块 (Background)"
            elif i == 1:
                role = "主体文字 (Text)"
            elif i == 2:
                role = "核心点缀色 (Accent 1)"
            elif i == 3:
                role = "次要点缀色 (Accent 2)"
            else:
                role = "其他点缀色"
                
            lines.append(f"- **{role}**：![{hex_color}](https://placehold.co/15x15/{clean_hex}/{clean_hex}.png) `{hex_color}`")
    else:
        lines.append("> （自动生成，未指定具体配色方案）")

    lines.extend([
        "",
        "---",
        "",
        "## 四、各页预览",
        "",
    ])

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
        "back": "尾页",
    }

    for page in narrative_outline:
        pnum = page.get("page_num", 0)
        ptype = page.get("type", "content")
        ptype_cn = type_names.get(ptype, ptype)

        tc = page.get("text_content", {})
        headline = tc.get("headline", "") or page.get("title", "")
        subhead = tc.get("subhead", "")
        body_raw = tc.get("body") or []
        # 去重，但要处理可能包含 dict 的情况
        body = []
        seen = set()
        for item in body_raw:
            if isinstance(item, dict):
                # dict 类型直接添加，不去重
                body.append(item)
            else:
                # 字符串类型去重
                if item not in seen:
                    body.append(item)
                    seen.add(item)
        table_data = tc.get("table_data") or page.get("table_data")
        visual_suggestion = page.get("visual_suggestion", "")
        narrative_role = page.get("narrative_role", "")
        one_takeaway = page.get("one_takeaway", "")

        lines.append(f"### 第 {pnum} 页 · {ptype_cn}")
        lines.append("")
        lines.append(f"- **标题**：{headline}")
        if subhead:
            lines.append(f"- **副标题**：{subhead}")
        if page.get("visual_intent"):
            lines.append(f"- **视觉意图**：{page.get('visual_intent')}")
        if page.get("image_need_level"):
            lines.append(f"- **配图强度**：{page.get('image_need_level')}")
        if page.get("recommended_layout_family"):
            lines.append(f"- **推荐布局**：{page.get('recommended_layout_family')}")
        if page.get("image_selection_reason"):
            lines.append(f"- **选图理由**：{page.get('image_selection_reason')}")
        
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
                mode = img.get('integration_mode', 'overlay')
                mode_str = "[融合]" if mode == "blend" else "[叠加]"
                bbox = img.get('bounding_box', {})
                if bbox:
                    bbox_str = f"left: {bbox.get('left')}, top: {bbox.get('top')}, width: {bbox.get('width')}, height: {bbox.get('height')}"
                else:
                    bbox_str = img.get('layout', 'center')
                # 简化格式，去掉多余的信息和标签，只保留角色、预览和位置信息
                
                # Make sure the path is correct relative to content_file when generating review md
                # Or keep it as absolute path
                content_file = meta.get("content_file", "")
                base_dir = os.path.dirname(os.path.abspath(content_file)) if content_file else ""
                
                if not os.path.isabs(path) and base_dir:
                    abs_path = os.path.normpath(os.path.join(base_dir, path))
                    if os.path.exists(abs_path):
                        path = abs_path
                
                img_src = f"file://{path}" if os.path.isabs(path) else path
                lines.append(f"  {idx+1}. {mode_str} {role} <img src=\"{img_src}\" height=\"40\" style=\"vertical-align: middle;\" /> (`{bbox_str}`)")
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

    # 提取视觉主张 (Design System Manifesto)
    manifesto = ""
    manifesto_match = re.search(r"##\s*[二三]、视觉主张.*?\n(.*?)---", md_text, re.DOTALL)
    if manifesto_match:
        manifesto = manifesto_match.group(1).strip()
        if manifesto == "> （尚未生成视觉主张，将在 execute 阶段由 Art Director 自动补齐）":
            manifesto = ""

    # 按页解析：匹配 ### 第 N 页 · 类型 及其后内容块
    type_map = {
        "封面": "cover", "章节": "section", "内容": "content",
        "金句": "hero", "核心/金句": "hero", "名人金句": "quote", "呼吸": "breathing", "目录": "toc",
        "数据": "data", "流程": "flowchart", "框架": "framework",
        "对比": "comparison", "封底": "ending", "尾页": "back",
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
        visual_intent = ""
        image_need_level = ""
        recommended_layout_family = ""
        image_selection_reason = ""
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
            elif re.match(r"^-\s*\*\*视觉意图\*\*\s*[：:]\s*", line):
                visual_intent = re.sub(r"^-\s*\*\*视觉意图\*\*\s*[：:]\s*", "", line).strip()
                in_native_images = False
            elif re.match(r"^-\s*\*\*配图强度\*\*\s*[：:]\s*", line):
                image_need_level = re.sub(r"^-\s*\*\*配图强度\*\*\s*[：:]\s*", "", line).strip()
                in_native_images = False
            elif re.match(r"^-\s*\*\*推荐布局\*\*\s*[：:]\s*", line):
                recommended_layout_family = re.sub(r"^-\s*\*\*推荐布局\*\*\s*[：:]\s*", "", line).strip()
                in_native_images = False
            elif re.match(r"^-\s*\*\*选图理由\*\*\s*[：:]\s*", line):
                image_selection_reason = re.sub(r"^-\s*\*\*选图理由\*\*\s*[：:]\s*", "", line).strip()
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
                    raw_role = img_match.group(1).strip()
                    integration_mode = "overlay"
                    if raw_role.startswith("[融合]"):
                        integration_mode = "blend"
                        role = raw_role[4:].strip()
                    elif raw_role.startswith("[叠加]"):
                        role = raw_role[4:].strip()
                    else:
                        role = raw_role
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
                        raw_role = img_match.group(1).strip()
                        integration_mode = "overlay"
                        if raw_role.startswith("[融合]"):
                            integration_mode = "blend"
                            role = raw_role[4:].strip()
                        elif raw_role.startswith("[叠加]"):
                            role = raw_role[4:].strip()
                        else:
                            role = raw_role
                        path = img_match.group(2).strip()
                        bbox_str = img_match.group(3).strip()
                    else:
                        img_match = re.search(r"\[([^\]]+)\]\(([^)]+)\)\s*->\s*(.*?)\s*\(`bounding_box`:\s*(.*?)\)", line)
                        if img_match:
                            path = img_match.group(2).strip()
                            raw_role = img_match.group(3).strip()
                            integration_mode = "overlay"
                            if raw_role.startswith("[融合]"):
                                integration_mode = "blend"
                                role = raw_role[4:].strip()
                            elif raw_role.startswith("[叠加]"):
                                role = raw_role[4:].strip()
                            else:
                                role = raw_role
                            bbox_str = img_match.group(4).strip()
                        else:
                            img_match = re.search(r"`([^`]+)`\s*->\s*(.*?)\s*\(`bounding_box`:\s*(.*?)\)", line)
                            if img_match:
                                path = img_match.group(1).strip()
                                raw_role = img_match.group(2).strip()
                                integration_mode = "overlay"
                                if raw_role.startswith("[融合]"):
                                    integration_mode = "blend"
                                    role = raw_role[4:].strip()
                                elif raw_role.startswith("[叠加]"):
                                    role = raw_role[4:].strip()
                                else:
                                    role = raw_role
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
                        "integration_mode": integration_mode,
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
        if visual_intent:
            page_dict["visual_intent"] = visual_intent
        if image_need_level:
            page_dict["image_need_level"] = image_need_level
        if recommended_layout_family:
            page_dict["recommended_layout_family"] = recommended_layout_family
        if image_selection_reason:
            page_dict["image_selection_reason"] = image_selection_reason
        if lift_rate:
            page_dict["lift_rate"] = lift_rate
        if native_images:
            page_dict["native_images"] = native_images
            
        pages.append(page_dict)

    pages.sort(key=lambda p: p["page_num"])
    return {"meta": meta, "style": style, "pages": pages, "manifesto": manifesto}

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
    调用 VisualAgent 生成 visual_prompt。
    """
    from .llm_client import MODEL_FALLBACK_CHAIN

    model_fallback = model_fallback or MODEL_FALLBACK_CHAIN
    
    from tools.nano_banana_ppt.agents.visual import VisualAgent
    visual_agent = VisualAgent(api_key=api_key, api_base=api_base)

    meta = parsed.get("meta", {})
    style = parsed.get("style", {})
    pages = parsed.get("pages", [])
    manifesto = parsed.get("manifesto", "")

    meta["project_dir"] = project_dir
    meta["content_file"] = content_file
    meta["project_name"] = Path(project_dir).name
    if not meta.get("template_file"):
        meta["template_file"] = None
    if not meta.get("logo_file"):
        meta["logo_file"] = None

    # 从 _content_state.json 中恢复 manifesto_bans 和 visual_diversity_strategy
    manifesto_bans = ""
    visual_diversity_strategy = ""
    state_file = Path(project_dir) / "_content_state.json"
    if state_file.exists():
        try:
            with open(state_file, "r", encoding="utf-8") as f:
                state_data = json.load(f)
                manifesto_bans = state_data.get("manifesto_bans", "")
                visual_diversity_strategy = state_data.get("visual_diversity_strategy", "")
        except Exception:
            pass

    fonts = style.get("fonts", [])
    
    manifesto_full = manifesto
    if manifesto and manifesto_bans:
        manifesto_full = f"{manifesto}\n\n【Cliche Avoidance (STRICTLY ENFORCED)】\n{manifesto_bans}"
    elif manifesto_bans:
        manifesto_full = manifesto_bans
    
    if visual_diversity_strategy:
        manifesto_full = f"{manifesto_full}\n\n【Visual Diversity Strategy (MUST FOLLOW)】\n{visual_diversity_strategy}\nCRITICAL: Each slide MUST use a DIFFERENT visual motif from the list above. Never repeat the same type of visual subject (e.g., stone monolith, glass panel) on consecutive slides. Rotate through the motif categories to ensure visual variety across the entire deck."
    
    style_config = {
        "description": style.get("description", "Professional presentation"),
        "palette": style.get("palette", ["#1a1a2e", "#16213e", "#0f3460"]),
        "fonts": fonts,
        "mode": "ai_minting",
        "manifesto": manifesto_full,
    }

    # 包装资产给 visual_agent
    assets = {
        'logo_path': meta.get('logo_file')
    }
    
    # 构建 template_info 给 visual_agent
    template_info = None
    if meta.get("template_file"):
        template_info = {"logo_path": meta.get("logo_file")}

    # 直接调用 VisualAgent 的计划生成逻辑
    slides = visual_agent.generate_visual_plan(
        narrative_outline=pages,
        style_definition_tuple=(style_config['description'], style_config),
        assets=assets,
        template_info=template_info
    )

    return {"meta": meta, "slides": slides}
