"""
人类可审阅的 PPT 计划生成与解析。

- build_review_md: 从 narrative_outline + style_config 生成人类可读的 visual_plan.md
- parse_review_md: 从 MD 解析回结构化数据
- derive_technical_plan: 从解析结果生成执行层使用的 visual_plan.json
"""
import json
import logging
import re
import os
from pathlib import Path
from typing import Dict, List, Optional, Any
from .provider_config import DEFAULT_LLM_MODEL, get_llm_api_base

logger = logging.getLogger(__name__)

REVIEW_MD_FILENAME = "visual_plan.md"


def _normalize_image_mode_value(mode: Optional[str]) -> str:
    """将图片模式规范化为 PRD 约定的大写常量。"""
    if not mode:
        return "INTENT_FUSION"

    mode_str = str(mode).strip()
    upper_mode = mode_str.upper()

    mapping = {
        "INTENT_FUSION": "INTENT_FUSION",
        "INTENT-FUSION": "INTENT_FUSION",
        "INTENT FUSION": "INTENT_FUSION",
        "INTENT_FUSION".lower(): "INTENT_FUSION",
        "ELEMENT_PRESERVE": "ELEMENT_PRESERVE",
        "ELEMENT-PRESERVE": "ELEMENT_PRESERVE",
        "ELEMENT PRESERVE": "ELEMENT_PRESERVE",
        "ELEMENT_PRESERVE".lower(): "ELEMENT_PRESERVE",
        "ORIGINAL_PRESENT": "ORIGINAL_PRESENT",
        "ORIGINAL-PRESENT": "ORIGINAL_PRESENT",
        "ORIGINAL PRESENT": "ORIGINAL_PRESENT",
        "ORIGINAL_PRESENT".lower(): "ORIGINAL_PRESENT",
        "[融合]": "INTENT_FUSION",
        "[叠加]": "ORIGINAL_PRESENT",
    }

    return mapping.get(mode_str, mapping.get(upper_mode, "INTENT_FUSION"))


def _mode_to_review_label(mode: Optional[str]) -> str:
    return f"[{_normalize_image_mode_value(mode)}]"


def build_visual_plan_from_content_plan(
    content_md_path: str,
    style_config: Dict,
    meta: Dict,
    manifesto: str = "",
    per_slide_descriptions: Dict[int, str] = None,
    state_narrative_outline: List[Dict] = None,
    generated_slides: Optional[List[Dict]] = None,
) -> str:
    """
    从 content_plan.md 文件读取内容大纲,结合 style_config 生成完整的 visual_plan.md

    Args:
        content_md_path: content_plan.md 文件路径
        style_config: 风格配置
        meta: 元信息
        manifesto: 视觉主张文本
        per_slide_descriptions: {page_num: visual_description_str} — VisualDirector 为每页生成的视觉描述
        state_narrative_outline: 可选，从 _content_state.json 传入的 narrative_outline（包含 native_images）
        generated_slides: 可选，plan-visual 阶段已生成的执行层 slides，用于回写 final prompt 等字段
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

    # 注入 VisualDirector 为每页生成的 visual_description
    if per_slide_descriptions:
        for page in narrative_outline:
            pnum = page.get("page_num")
            if pnum in per_slide_descriptions:
                page["visual_description"] = per_slide_descriptions[pnum]

    # 如果传入了 state_narrative_outline，合并 native_images 信息
    if state_narrative_outline:
        state_by_pnum = {p.get("page_num"): p for p in state_narrative_outline}
        for page in narrative_outline:
            pnum = page.get("page_num")
            if pnum in state_by_pnum:
                state_page = state_by_pnum[pnum]
                if state_page.get("native_images"):
                    page["native_images"] = state_page.get("native_images")

    if generated_slides:
        slides_by_pnum = {slide.get("page_num"): slide for slide in generated_slides}
        for page in narrative_outline:
            slide = slides_by_pnum.get(page.get("page_num"))
            if not slide:
                continue
            page["visual_description"] = slide.get(
                "visual_description",
                page.get("visual_description", page.get("visual_suggestion", "")),
            )
            page["final_visual_prompt"] = slide.get(
                "final_visual_prompt",
                slide.get("visual_prompt", page.get("final_visual_prompt", "")),
            )
            page["seed_role"] = slide.get("seed_role", page.get("seed_role", ""))
            page["seed_usage_rule"] = slide.get("seed_usage_rule", page.get("seed_usage_rule", ""))

    # 调用 build_review_md 生成完整的审阅计划
    return build_review_md(narrative_outline, style_config, meta, manifesto)


# 兼容旧引用，后续可删除
build_master_plan_from_content_plan = build_visual_plan_from_content_plan


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

    user_prompt = (Path(__file__).parent / "prompts" / "review_plan_manifesto.txt").read_text(encoding="utf-8").format(
        outline_summary=outline_summary,
        style_hint=style_hint,
        template_instruction=template_instruction,
    )

    try:
        resp = chat_completion_with_fallback(
            client, model_fallback=model_fallback or ["MiniMax-M2.7"],
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.3,  # 降低温度以提高稳定性
            response_format={"type": "json_object"}
        )
        content = resp.choices[0].message.content.strip()

        # 记录原始返回内容用于调试
        logger.info(f"Design Manifesto raw response (first 200 chars): {content[:200]}")

        # 如果返回内容为空，抛出异常触发重试
        if not content:
            raise ValueError("LLM returned empty response")

        # 清理 markdown 代码块标记
        if content.startswith("```json"):
            content = content[7:]
        elif content.startswith("```"):
            content = content[3:]
        if content.endswith("```"):
            content = content[:-3]

        content = content.strip()

        # 移除 <think> 标签（如果存在）
        import re
        # 移除 <think>...</think> 标签及其内容
        content = re.sub(r'<think>.*?</think>', '', content, flags=re.DOTALL)
        content = content.strip()

        # 再次检查清理后的内容是否为空
        if not content:
            raise ValueError("Content is empty after cleaning markdown blocks and think tags")

        result = json.loads(content)

        # 验证必需字段
        if not result.get("chinese_proposal"):
            raise ValueError("Missing chinese_proposal in response")

        return {
            "chinese_proposal": result.get("chinese_proposal", "现代极简专业风格。我们使用干净的线条和微妙的渐变，结合大面积留白，为您的内容提供一个高级、清晰的展示空间。"),
            "english_cliche_bans": result.get("english_cliche_bans", "No glowing brains, no handshakes, no generic 3D funnels, no floating data."),
            "visual_diversity_strategy": result.get("visual_diversity_strategy", "")
        }
    except Exception as e:
        logger.error(f"Failed to generate Design Manifesto: {e}")
        logger.error(f"Response content: {content if 'content' in locals() else 'N/A'}")

        # 返回默认值，但记录详细错误信息
        return {
            "chinese_proposal": "现代极简专业风格。我们使用干净的线条和微妙的渐变，结合大面积留白，为您的内容提供一个高级、清晰的展示空间。",
            "english_cliche_bans": "No glowing brains, no handshakes, no generic 3D funnels, no floating data.",
            "visual_diversity_strategy": ""
        }


def _generate_batch_visual_suggestions(
    batch_pages: List[Dict],
    style_config: Dict,
    api_key: str,
    api_base: Optional[str] = None,
    visual_constraints: List[str] = None,  # 新增参数
) -> Dict[int, str]:
    """
    为一批页面生成视觉描述（内部函数，供并行调用）
    """
    from .llm_client import chat_completion_with_fallback, MODEL_FALLBACK_CHAIN
    from openai import OpenAI
    import json
    import re

    client = OpenAI(api_key=api_key, base_url=get_llm_api_base(api_base))

    palette = style_config.get("palette", [])
    style_desc = style_config.get("description", "Professional presentation")
    palette_str = ", ".join(palette) if palette else "auto"

    # 构建这批页面的上下文
    pages_context = []
    for p in batch_pages:
        pnum = p.get("page_num", 0)
        ptype = p.get("type", "content")
        tc = p.get("text_content", {})
        headline = tc.get("headline", "")
        subhead = tc.get("subhead", "")
        body = tc.get("body", [])

        ctx = f"P{pnum} [{ptype}] 标题:{headline}"
        if subhead:
            ctx += f" | 副标题:{subhead}"
        if body:
            ctx += f" | 正文:{'; '.join(str(b) for b in body[:3])}"
        pages_context.append(ctx)

    pages_text = "\n".join(pages_context)

    # 构建视觉约束部分
    constraints_section = ""
    if visual_constraints:
        constraints_list = "\n".join([f"- {c}" for c in visual_constraints])
        constraints_section = f"\n\n【用户视觉约束】\n{constraints_list}\n\n请在生成每页视觉描述时严格遵循以上约束。"

    system_prompt = (
        "You are a world-class Art Director. "
        "For each slide listed, you must propose a CONCRETE, SPECIFIC visual scene description "
        "in natural Chinese. Be precise — state exact visual metaphors, objects, and composition."
        f"{constraints_section}"
    )

    user_prompt = (Path(__file__).parent / "prompts" / "review_plan_visual_suggestions.txt").read_text(encoding="utf-8").format(
        style_desc=style_desc,
        palette_str=palette_str,
        pages_text=pages_text,
    )

    response = chat_completion_with_fallback(
        client,
        model=DEFAULT_LLM_MODEL,
        model_fallback=[DEFAULT_LLM_MODEL],
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ],
        temperature=0.3
    )
    content = response.choices[0].message.content.strip()

    # 移除 <think> 标签
    content = re.sub(r'<think>.*?</think>', '', content, flags=re.DOTALL).strip()

    # Extract JSON
    json_match = re.search(r'\{[\s\S]+\}', content)
    if json_match:
        data = json.loads(json_match.group())
        slides_data = data.get("slides", {})
        return {int(k): v for k, v in slides_data.items()}

    return {}


def generate_per_slide_visual_suggestions(
    narrative_outline: List[Dict],
    style_config: Dict,
    api_key: str,
    api_base: Optional[str] = None,
    visual_constraints: List[str] = None,  # 新增参数
) -> Dict[int, str]:
    """
    为每一页生成具体的「配图/画面」人类语言描述（并行化版本）
    返回 dict: {page_num: visual_suggestion_string}
    """
    from concurrent.futures import ThreadPoolExecutor, as_completed
    from functools import partial
    import logging

    logger = logging.getLogger(__name__)

    # 分批（每批 6 页）
    batch_size = 6
    batches = [narrative_outline[i:i+batch_size] for i in range(0, len(narrative_outline), batch_size)]

    logger.info(f"📋 将 {len(narrative_outline)} 页分为 {len(batches)} 批并行生成视觉描述...")

    # 使用 partial 简化参数传递
    batch_generator = partial(
        _generate_batch_visual_suggestions,
        style_config=style_config,
        api_key=api_key,
        api_base=api_base,
        visual_constraints=visual_constraints
    )

    # 并行调用
    all_results = {}
    with ThreadPoolExecutor(max_workers=4) as executor:
        future_to_batch = {
            executor.submit(batch_generator, batch): i
            for i, batch in enumerate(batches)
        }

        for future in as_completed(future_to_batch):
            batch_idx = future_to_batch[future]
            try:
                batch_results = future.result()
                all_results.update(batch_results)
                logger.info(f"✅ 批次 {batch_idx + 1}/{len(batches)} 完成")
            except Exception as e:
                logger.error(f"❌ 批次 {batch_idx + 1} 失败: {e}")

    return all_results


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
        lines.append(f"- **正文形态**：{tc.get('body_format', 'bullets')}")

        if table_data:
            # 支持两种格式：dict {{"headers": [...], "rows": [[...]]}} 或 string (原始markdown)
            if isinstance(table_data, str):
                # 解析原始markdown表格字符串
                lines_t = table_data.strip().split('\n')
                headers = [c.strip() for c in lines_t[0].split('|') if c.strip()]
                rows = [[c.strip() for c in line.split('|') if c.strip() and not re.match(r'^[-:\s]+$', c)]
                        for line in lines_t[2:] if line.strip()]
            else:
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
            # 过滤掉 body 中混入的 headline/subhead/speaker_notes/正文 等项（它们应该由顶层变量输出）
            filtered_body = [b for b in body if not (
                '**标题**' in b or
                '**副标题**' in b or
                '**演讲备注' in b or
                '**正文**' in b
            )]
            if body_format in ("paragraph", "quote", "data") and len(body) <= 2:
                for b in filtered_body:
                    lines.append(f"  {b}")
            else:
                for b in filtered_body:
                    lines.append(f"  - {b}")
            lines.append("")

        # 演讲备注（如果还没有被 body 中的项提取，则单独输出）
        speaker_notes = page.get("speaker_notes", "")
        if speaker_notes:
            lines.append("- **🎙️ 演讲备注 (Speaker Notes)**：")
            lines.append(f"  > {speaker_notes.strip().replace(chr(10), chr(10) + '  > ')}")
            lines.append("")

        native_images = page.get("native_images", [])

        if native_images:
            lines.append("- **📥 原生图片**：")
            for idx, img in enumerate(native_images):
                path = img.get('path', 'unknown_path')
                role = img.get('semantic_role', '')
                mode = img.get('mode', img.get('integration_mode', 'blend'))
                mode_str = _mode_to_review_label(mode)
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


def _default_seed_usage_rule(seed_role: str) -> str:
    if seed_role == "family_seed":
        return "种子页：负责定义这一类页面的风格、排版语言和视觉语法，供后续同类页面继承。"
    return (
        "后续页：只能继承种子页的风格、字体、配色、间距和版式语法；"
        "禁止复用种子页的文字、示例内容、核心画面主体、独特图形组合或信息图骨架。"
    )


def build_review_md(
    narrative_outline: List[Dict],
    style_config: Dict,
    meta: Dict,
    manifesto: str = "",
    include_execution_prompts: bool = False,
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
        visual_description = page.get("visual_description", page.get("visual_suggestion", ""))
        seed_role = page.get("seed_role", "")
        seed_usage_rule = page.get("seed_usage_rule", "") or _default_seed_usage_rule(seed_role)
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
            # 支持两种格式：dict {{"headers": [...], "rows": [[...]]}} 或 string (原始markdown)
            if isinstance(table_data, str):
                # 解析原始markdown表格字符串
                lines_t = table_data.strip().split('\n')
                headers = [c.strip() for c in lines_t[0].split('|') if c.strip()]
                rows = [[c.strip() for c in line.split('|') if c.strip() and not re.match(r'^[-:\s]+$', c)]
                        for line in lines_t[2:] if line.strip()]
            else:
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
            lines.append(f"  > {speaker_notes.strip().replace(chr(10), chr(10) + '  > ')}")
            lines.append("")

        native_images = page.get("native_images", [])

        if native_images:
            lines.append("- **📥 原生图片**：")
            for idx, img in enumerate(native_images):
                # 支持字符串格式（如 "native_images/slide3_img1.png"）或字典格式
                if isinstance(img, str):
                    path = img
                    role = ''
                    mode = 'INTENT_FUSION'
                    bbox_str = 'center'
                else:
                    path = img.get('path', 'unknown_path')
                    role = img.get('semantic_role', '')
                    mode = img.get('mode', img.get('integration_mode', 'blend'))
                    bbox = img.get('bounding_box', {})
                    if bbox:
                        bbox_str = f"left: {bbox.get('left')}, top: {bbox.get('top')}, width: {bbox.get('width')}, height: {bbox.get('height')}"
                    else:
                        bbox_str = img.get('layout', 'center')
                mode_str = _mode_to_review_label(mode)
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

        lines.append(f"- **配图/画面**：{visual_description}")
        lines.append(f"- **种子页使用说明**：{seed_usage_rule}")
        if include_execution_prompts:
            final_visual_prompt = page.get("final_visual_prompt", page.get("visual_prompt", ""))
            lines.append("- **最终执行提示词**：")
            lines.append("```text")
            lines.append(final_visual_prompt or "")
            lines.append("```")
            lines.append("")
        lines.append("---")
        lines.append("")

    return "\n".join(lines)


def parse_review_md(md_text: str, project_dir: str = None) -> Dict[str, Any]:
    """
    解析 plan_for_review.md，返回结构化数据。
    返回: { "meta": {...}, "style": {...}, "pages": [ {...}, ... ] }
    project_dir: 可选，用于解析 native_images 相对路径
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

    type_map = {
        "封面": "cover", "章节": "section", "内容": "content",
        "金句": "hero", "核心/金句": "hero", "名人金句": "quote", "呼吸": "breathing", "目录": "toc",
        "数据": "data", "流程": "flowchart", "框架": "framework",
        "对比": "comparison", "封底": "ending", "尾页": "back",
    }

    # 按页解析：匹配 ## 或 ### 第 N 页 · 类型 及其后内容块
    page_blocks = re.findall(
        r"#+\s*第\s*(\d+)\s*页\s*·\s*\[?([^\]\n]+)\]?\s*\n\n(.*?)(?=\n#+\s*第|\n[-─]{3,}\s*\n|\Z)",
        md_text,
        re.DOTALL,
    )

    for pnum_str, ptype_cn, block in page_blocks:
        pnum = int(pnum_str)
        # 页面类型不再在 markdown 中体现，从原始数据或者推测，或者默认为 content
        # 我们需要保留它如果原本就在 JSON 中，但因为 plan_for_review 会被重新解析生成 JSON，
        # 所以我们需要尽量保证不要丢失信息。既然我们在 title 里写了 "### 第 X 页 · 页面类型"
        # 我们可以从标题里提取类型（支持方括号格式如 [COVER 封面]）
        ptype_cn_clean = ptype_cn.replace("COVER", "").replace("CHAPTER", "").replace("GOLD_QUOTE", "").replace("CASE", "").replace("IMAGE", "").replace("DATA", "").replace("INFO", "").replace("CAMPAIGN", "").replace("PROPOSAL", "").replace("MAP", "").replace("ENDING", "").strip()
        for key in type_map:
            if key in ptype_cn or key in ptype_cn.upper():
                ptype = type_map[key]
                break
        else:
            ptype = type_map.get(ptype_cn.strip().split()[0] if ptype_cn.strip() else "", "content")
            if ptype == "content" and ptype_cn:
                # 尝试从方括号内的英文类型名映射
                en_type_match = re.search(r'\b(Cover|Chaper|Gold_quote|Case|Image|Data|Info|Campaign|Proposal|Map|Ending)\b', ptype_cn, re.IGNORECASE)
                if en_type_match:
                    en_type = en_type_match.group(1).lower()
                    type_map_lower = {k.lower(): v for k, v in type_map.items()}
                    ptype = type_map_lower.get(en_type, "content")
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
        visual_description = ""
        final_visual_prompt_lines = []
        final_visual_prompt = ""
        seed_role = ""
        seed_usage_rule = ""
        speaker_notes_lines = []
        native_images = []

        in_body = False
        in_notes = False
        in_native_images = False
        in_final_prompt = False
        in_final_prompt_block = False
        
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
                in_final_prompt = False
                in_final_prompt_block = False
            elif line.strip().startswith("- **🎙️ 演讲备注"):
                in_body = False
                in_notes = True
                in_native_images = False
                in_final_prompt = False
                in_final_prompt_block = False
            elif line.strip().startswith("- **📥 原生图片"):
                in_body = False
                in_notes = False
                in_native_images = True
                in_final_prompt = False
                in_final_prompt_block = False
            elif re.match(r"^-\s*\*\*种子页使用说明\*\*\s*[：:]\s*", line):
                seed_usage_rule = re.sub(r"^-\s*\*\*种子页使用说明\*\*\s*[：:]\s*", "", line).strip()
                in_body = False
                in_notes = False
                in_native_images = False
                in_final_prompt = False
                in_final_prompt_block = False
            elif re.match(r"^-\s*\*\*最终执行提示词\*\*\s*[：:]\s*", line):
                in_body = False
                in_notes = False
                in_native_images = False
                in_final_prompt = True
                in_final_prompt_block = False
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
            elif in_final_prompt and line.strip().startswith("```"):
                if not in_final_prompt_block:
                    in_final_prompt_block = True
                else:
                    in_final_prompt = False
                    in_final_prompt_block = False
            elif in_final_prompt:
                final_visual_prompt_lines.append(line)
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
                    integration_mode = "blend"
                    mode_match = re.match(r"^\[(INTENT_FUSION|ELEMENT_PRESERVE|ORIGINAL_PRESENT|融合|叠加)\]\s*(.*)$", raw_role)
                    if mode_match:
                        mode_value = _normalize_image_mode_value(mode_match.group(1))
                        role = mode_match.group(2).strip()
                    else:
                        mode_value = "INTENT_FUSION"
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
                        integration_mode = "blend"
                        mode_match = re.match(r"^\[(INTENT_FUSION|ELEMENT_PRESERVE|ORIGINAL_PRESENT|融合|叠加)\]\s*(.*)$", raw_role)
                        if mode_match:
                            mode_value = _normalize_image_mode_value(mode_match.group(1))
                            role = mode_match.group(2).strip()
                        else:
                            mode_value = "INTENT_FUSION"
                            role = raw_role
                        path = img_match.group(2).strip()
                        bbox_str = img_match.group(3).strip()
                    else:
                        img_match = re.search(r"\[([^\]]+)\]\(([^)]+)\)\s*->\s*(.*?)\s*\(`bounding_box`:\s*(.*?)\)", line)
                        if img_match:
                            path = img_match.group(2).strip()
                            raw_role = img_match.group(3).strip()
                            mode_match = re.match(r"^\[(INTENT_FUSION|ELEMENT_PRESERVE|ORIGINAL_PRESENT|融合|叠加)\]\s*(.*)$", raw_role)
                            if mode_match:
                                mode_value = _normalize_image_mode_value(mode_match.group(1))
                                role = mode_match.group(2).strip()
                            else:
                                mode_value = "INTENT_FUSION"
                                role = raw_role
                            bbox_str = img_match.group(4).strip()
                        else:
                            img_match = re.search(r"`([^`]+)`\s*->\s*(.*?)\s*\(`bounding_box`:\s*(.*?)\)", line)
                            if img_match:
                                path = img_match.group(1).strip()
                                raw_role = img_match.group(2).strip()
                                mode_match = re.match(r"^\[(INTENT_FUSION|ELEMENT_PRESERVE|ORIGINAL_PRESENT|融合|叠加)\]\s*(.*)$", raw_role)
                                if mode_match:
                                    mode_value = _normalize_image_mode_value(mode_match.group(1))
                                    role = mode_match.group(2).strip()
                                else:
                                    mode_value = "INTENT_FUSION"
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
                    # Use project_dir first since native_images are relative to project_dir
                    # Fallback to content_file dir only if needed
                    resolved_path = None
                    if project_dir and not os.path.isabs(path):
                        abs_path = os.path.normpath(os.path.join(project_dir, path))
                        if os.path.exists(abs_path):
                            resolved_path = abs_path

                    if not resolved_path:
                        content_file = meta.get("content_file", "")
                        base_dir = os.path.dirname(os.path.abspath(content_file)) if content_file else ""
                        if not os.path.isabs(path) and base_dir:
                            abs_path = os.path.normpath(os.path.join(base_dir, path))
                            if os.path.exists(abs_path):
                                resolved_path = abs_path
                        elif not os.path.exists(path):
                            # Attempt to resolve if it's just a filename
                            filename = os.path.basename(path)
                            if base_dir:
                                abs_path = os.path.normpath(os.path.join(base_dir, filename))
                                if os.path.exists(abs_path):
                                    resolved_path = abs_path

                    path = resolved_path if resolved_path else path
                    
                    native_images.append({
                        "path": path,
                        "semantic_role": role,
                        "integration_mode": "blend",
                        "mode": mode_value,
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
                in_final_prompt = False
                in_final_prompt_block = False
                visual_description = re.sub(r"^-\s*\*\*配图/画面\*\*\s*[：:]\s*", "", line).strip()
            elif line.strip() != "":
                # If we are not in notes or body, don't clear flags for empty lines, but clear for other markers
                pass

        # 正文去重（保持顺序），避免如 P18 出现「核心命题」重复两遍
        body = list(dict.fromkeys(body))

        final_visual_prompt = "\n".join(final_visual_prompt_lines).strip()
        if seed_usage_rule:
            if seed_usage_rule.startswith("种子页"):
                seed_role = "family_seed"
            elif seed_usage_rule.startswith("后续页"):
                seed_role = "follow_up"

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
            "visual_description": visual_description,
            "final_visual_prompt": final_visual_prompt,
            "speaker_notes": "\n".join(speaker_notes_lines) if speaker_notes_lines else ""
        }
        if visual_description:
            page_dict["visual_suggestion"] = visual_description
        if seed_role:
            page_dict["seed_role"] = seed_role
        if seed_usage_rule:
            page_dict["seed_usage_rule"] = seed_usage_rule
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

def _bbox_to_position(bbox: Dict[str, Any]) -> str:
    """将 bbox 近似还原为位置描述，便于 visual_plan.json 复用。"""
    if not bbox:
        return "center"

    left = bbox.get("left", 0.0)
    top = bbox.get("top", 0.0)
    width = bbox.get("width", 0.0)
    height = bbox.get("height", 0.0)

    if left <= 0.05 and top <= 0.05 and width >= 0.9 and height >= 0.9:
        return "full"
    if width <= 0.45 and left >= 0.55:
        return "right"
    if width <= 0.45 and left <= 0.05:
        return "left"
    if height <= 0.45 and top <= 0.05:
        return "top"
    if height <= 0.45 and top >= 0.55:
        return "bottom"
    return "center"


def _build_visual_plan_pages(parsed_pages: List[Dict], slides: List[Dict]) -> List[Dict]:
    """从解析后的页面和执行 slides 构建 visual_plan.json 的 pages 结构。"""
    slides_by_num = {slide.get("page_num"): slide for slide in slides}
    visual_pages = []

    for page in parsed_pages:
        page_num = page.get("page_num", 0)
        slide = slides_by_num.get(page_num, {})
        text_content = page.get("text_content", {})
        headline = text_content.get("headline", "") or page.get("title", "") or f"第 {page_num} 页"
        title = f"第 {page_num} 页 · {headline}"

        images = []
        for img in slide.get("native_images", []) or []:
            images.append({
                "path": img.get("path", ""),
                "mode": _normalize_image_mode_value(img.get("mode")),
                "role": img.get("semantic_role", ""),
                "position": _bbox_to_position(img.get("bounding_box", {})),
                "semantic_anchor": img.get("semantic_anchor"),
                "final_visual_prompt": slide.get("final_visual_prompt", slide.get("visual_prompt", "")),
            })

        if not images:
            images.append({
                "path": "__GENERATED__",
                "mode": "INTENT_FUSION",
                "role": "generated_slide",
                "position": "full",
                "semantic_anchor": None,
                "final_visual_prompt": slide.get("final_visual_prompt", slide.get("visual_prompt", "")),
            })

        visual_pages.append({
            "page_number": page_num,
            "title": title,
            "type": slide.get("type", page.get("type", "content")),
            "visual_description": slide.get(
                "visual_description",
                page.get("visual_description", page.get("visual_suggestion", "")),
            ),
            "final_visual_prompt": slide.get("final_visual_prompt", slide.get("visual_prompt", "")),
            "seed_role": slide.get("seed_role", page.get("seed_role", "")),
            "seed_usage_rule": slide.get("seed_usage_rule", page.get("seed_usage_rule", "")),
            "images": images,
        })

    return visual_pages


def _extract_existing_slides(existing_plan: Optional[Dict[str, Any]]) -> Dict[int, Dict[str, Any]]:
    if not existing_plan:
        return {}
    slides = existing_plan.get("slides", [])
    if isinstance(slides, list):
        return {slide.get("page_num"): slide for slide in slides}
    return {}


def _build_slide_from_page(page: Dict[str, Any]) -> Dict[str, Any]:
    final_prompt = page.get("final_visual_prompt", page.get("visual_prompt", ""))
    slide = {
        "page_num": page.get("page_num"),
        "type": page.get("type", "content"),
        "text_content": page.get("text_content", {}),
        "visual_description": page.get("visual_description", page.get("visual_suggestion", "")),
        "final_visual_prompt": final_prompt,
        "visual_prompt": final_prompt,
        "speaker_notes": page.get("speaker_notes", ""),
        "seed_role": page.get("seed_role", ""),
        "seed_usage_rule": page.get("seed_usage_rule", ""),
    }
    if page.get("native_images"):
        slide["native_images"] = page.get("native_images")
    for field in (
        "reference_image",
        "reference_images",
        "layout",
        "logo_path",
        "logo_location",
        "style_config",
        "table_data",
        "visualization",
        "use_data_visualizer",
        "chart_type",
        "narrative_role",
        "one_takeaway",
        "visual_intent",
        "image_need_level",
        "recommended_layout_family",
        "image_selection_reason",
        "lift_rate",
    ):
        if field in page and page.get(field) is not None:
            slide[field] = page.get(field)
    return slide


def derive_technical_plan(
    parsed: Dict,
    project_dir: str,
    content_file: str,
    api_key: str,
    api_base: Optional[str] = None,
    model_fallback: Optional[List[str]] = None,
    existing_plan: Optional[Dict[str, Any]] = None,
) -> Dict:
    """
    从解析后的 MD 数据，生成完整的 visual_plan.json 结构（含 visual_prompt）。
    调用 VisualAgent 生成 visual_prompt。
    """
    from .llm_client import MODEL_FALLBACK_CHAIN

    model_fallback = model_fallback or MODEL_FALLBACK_CHAIN

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

    if existing_plan is None:
        existing_plan_path = Path(project_dir) / "visual_plan.json"
        if existing_plan_path.exists():
            try:
                with open(existing_plan_path, "r", encoding="utf-8") as f:
                    existing_plan = json.load(f)
            except Exception:
                existing_plan = None

    existing_slides = _extract_existing_slides(existing_plan)
    pages_needing_regen = set()

    for page in pages:
        page_num = page.get("page_num")
        current_desc = page.get("visual_description", page.get("visual_suggestion", ""))
        current_prompt = page.get("final_visual_prompt", "").strip()
        previous_slide = existing_slides.get(page_num, {})
        previous_desc = previous_slide.get(
            "visual_description",
            previous_slide.get("visual_suggestion", ""),
        )
        previous_prompt = previous_slide.get(
            "final_visual_prompt",
            previous_slide.get("visual_prompt", ""),
        ).strip()

        if current_prompt:
            if previous_slide and current_desc != previous_desc and current_prompt == previous_prompt:
                pages_needing_regen.add(page_num)
            continue

        if previous_slide and previous_prompt and current_desc == previous_desc:
            page["final_visual_prompt"] = previous_prompt
            page["visual_prompt"] = previous_prompt
            continue

        pages_needing_regen.add(page_num)

    regenerated_slides_by_num = {}
    if pages_needing_regen:
        from tools.nano_banana_ppt.agents.visual import VisualAgent

        prompt_mode = os.getenv("PROMPT_MODE", "verbose")
        visual_agent = VisualAgent(api_key=api_key, api_base=api_base, prompt_mode=prompt_mode)
        generated_slides = visual_agent.generate_visual_plan(
            narrative_outline=pages,
            style_definition_tuple=(style_config['description'], style_config),
            assets=assets,
            template_info=template_info
        )
        regenerated_slides_by_num = {
            slide.get("page_num"): slide
            for slide in generated_slides
            if slide.get("page_num") in pages_needing_regen
        }

    merged_pages = []
    for page in pages:
        page_num = page.get("page_num")
        merged_page = dict(page)
        generated_slide = regenerated_slides_by_num.get(page_num)

        if generated_slide:
            merged_page.update(generated_slide)
            merged_page["visual_description"] = generated_slide.get(
                "visual_description",
                merged_page.get("visual_description", merged_page.get("visual_suggestion", "")),
            )
            merged_page["final_visual_prompt"] = generated_slide.get(
                "final_visual_prompt",
                generated_slide.get("visual_prompt", ""),
            )

        merged_page["visual_description"] = merged_page.get(
            "visual_description",
            merged_page.get("visual_suggestion", ""),
        )
        merged_page["seed_role"] = merged_page.get("seed_role", "")
        merged_page["seed_usage_rule"] = merged_page.get(
            "seed_usage_rule",
            _default_seed_usage_rule(merged_page.get("seed_role", "")),
        )
        merged_pages.append(merged_page)

    slides = [_build_slide_from_page(page) for page in merged_pages]

    return {
        "meta": meta,
        "style": style,
        "manifesto": manifesto,
        "pages": _build_visual_plan_pages(merged_pages, slides),
        "slides": slides,
        "source_file": str(Path(project_dir) / REVIEW_MD_FILENAME),
    }
