"""
Visual Prompt Agent
负责将叙事大纲转化为 Nano Banana 2 的生图指令
实现风格路由（模版克隆 vs AI 铸模）+ 内容感知布局分配
"""
import os
import json
import logging
import re
from typing import Dict, List, Optional, Union
from openai import OpenAI

from ..utils.llm_client import chat_completion_with_fallback, MODEL_FALLBACK_CHAIN
from ..utils.provider_config import DEFAULT_LLM_MODEL, get_llm_api_base
from ..utils.prompt_spec import format_prompt_sections, prompt_has_required_sections
from .style_library import get_curated_style
from ..utils.image_assets import ImageMode

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class VisualAgent:
    # ── Layout library for content-aware variety ──
    LAYOUT_LIBRARY = {
        "centered_headline": "Centered large headline with minimal supporting text. Text dominates. Best for key messages or powerful statements.",
        "left_text_right_visual": "Left 60% for structured text, right 40% for an abstract graphic or icon cluster.",
        "top_visual_bottom_text": "Top 40% bold visual banner or key graphic, bottom 60% structured text content.",
        "three_column_grid": "Three equal columns, each with an icon/number header and short text. Best for 3 parallel concepts or steps.",
        "full_screen_immersive": "Full-screen cinematic background with large overlay text. Minimal body text, maximum visual impact.",
        "process_flow": "Horizontal flow showing 2-4 stages connected by arrows. Each stage has a label and short description.",
        "big_number_data": "Large key number/metric with supporting label. High impact data visualization.",
        "split_screen_contrast": "50/50 vertical split. One side dark, one side light (or image vs text). Good for comparisons.",
        "minimalist_hero": "Extreme minimalism. Massive typography, nearly zero chrome. For 'Hero' slides.",
        "chart_from_table": "Data visualization chart (bar/line/pie) derived from table data.",
        "bento_grid": "Asymmetrical Bento Grid. Multiple rounded rectangular glass/card modules of varying sizes (one main hero module, several smaller metric modules). Highly structured yet dynamic.",
        "dense_infographic": "High-density Infographic layout. A central visual hub connected to surrounding modules, or a highly structured modular grid. Uses icons, connectors, and clear data hierarchy to organize complex information.",
        "wide_quote_card": "Wide Quote Card. 1/3 of the space for a realistic portrait with a subtle gradient transition, 2/3 for a massive quotation text with an oversized faint quotation mark in the background.",
        "content": "A versatile content layout suitable for presenting a mix of text, lists, and visual elements with balanced spacing.",
        "infographic": "A dense, modular layout designed to hold multiple distinct data points or content blocks in a structured, easy-to-read grid."
    }

    def __init__(self, api_key: str, api_base: str = None, prompt_mode: str = "verbose", model_name: str = None):
        self.client = OpenAI(
            api_key=api_key,
            base_url=get_llm_api_base(api_base),
            timeout=120.0,
            max_retries=3
        )
        self.model = model_name if model_name else DEFAULT_LLM_MODEL
        self.prompt_mode = prompt_mode  # "verbose" or "minimal"

    def analyze_content_depth(self, narrative_outline: List[Dict]) -> Dict:
        """
        深度分析内容的情感核心和叙事结构
        
        这个函数会：
        1. 识别每个故事的核心主题
        2. 标注关键情节和泪点
        3. 提取可以反复出现的视觉符号
        4. 分析叙事节奏和情感曲线
        
        Returns:
            {
              "overall_theme": "AI 陪伴孤独的人...",
              "stories": [
                {
                  "story_name": "父亲与豆包",
                  "core_emotion": "孤独中的坚强",
                  "key_moments": [
                    {
                      "page": 5,
                      "moment": "父亲对女儿笑着说'没事'，挂断后对豆包说'我要去世了'",
                      "emotional_peak": "泪点",
                      "visual_emphasis": "对比：笑脸 vs 独自面对死亡"
                    }
                  ],
                  "symbolic_elements": ["手机屏幕的微光", "病房的孤独"]
                }
              ]
            }
        """
        logger.info("🔍 Visual Agent: 正在深度分析内容情感核心...")

        # 构建内容摘要
        content_summary = []
        for page in narrative_outline:
            page_num = page.get('page_num', 0)
            page_type = page.get('type', 'content')
            text_content = page.get('text_content', {})
            headline = text_content.get('headline', '')
            body = text_content.get('body', [])
            visual_suggestion = page.get('visual_suggestion', '')

            content_summary.append({
                'page': page_num,
                'type': page_type,
                'headline': headline,
                'body': body[:3],
                'visual_suggestion': visual_suggestion[:200]
            })

        prompt = f"""你是一位资深的内容分析师和叙事专家。请深度分析以下演示文稿的内容，识别其情感核心和叙事结构。

【内容概览】
{json.dumps(content_summary, ensure_ascii=False, indent=2)}

【分析任务】
1. 识别整体主题和核心情感
2. 如果内容包含多个故事，分别分析每个故事的：
   - 故事名称
   - 核心情感
   - 关键情节点（特别是情感高潮/泪点）
   - 可以反复出现的视觉符号
3. 分析叙事节奏和情感曲线

【输出格式】
输出严格的 JSON 格式：
{{
  "overall_theme": "整体主题描述",
  "stories": [
    {{
      "story_name": "故事名称",
      "core_emotion": "核心情感",
      "key_moments": [
        {{
          "page": 页码,
          "moment": "关键情节描述",
          "emotional_peak": "情感类型（如：泪点、高潮、转折）",
          "visual_emphasis": "视觉强调建议"
        }}
      ],
      "symbolic_elements": ["视觉符号1", "视觉符号2"]
    }}
  ]
}}

如果内容不是故事性的（如商业报告、技术文档），则 stories 数组可以为空，但仍需分析 overall_theme。
"""

        try:
            response = chat_completion_with_fallback(
                self.client, model=self.model, model_fallback=MODEL_FALLBACK_CHAIN,
                messages=[
                    {"role": "system", "content": "You are a content analysis expert. Output valid JSON only."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.5
            )
            content = self._clean_llm_json_response(response.choices[0].message.content)

            analysis = json.loads(content)
            logger.info(f"✅ 内容深度分析完成: {analysis.get('overall_theme', 'N/A')}")
            return analysis

        except Exception as e:
            logger.error(f"内容深度分析失败: {e}")
            return {
                "overall_theme": "未能分析",
                "stories": []
            }

    def review_visual_prompt(self, visual_prompt: str, visual_suggestion: str, text_content: Dict) -> str:
        """
        Review visual prompt 的质量
        
        检查项：
        1. 结构清晰度：是否有明确的 TEXT TO RENDER 和 VISUAL SCENE 部分？
        2. 语义准确性：是否准确传达了 Visual Suggestion 的核心意图？
        3. 文字完整性：是否包含所有必要的文字内容？
        4. 重点突出度：关键情节是否被强调？
        5. 自洽性：是否有矛盾或冲突的描述？
        6. 精简度：是否用精简但准确的语言表达？
        
        Returns:
            改进后的 visual_prompt
        """
        logger.info("🔍 Visual Agent: 正在审查 visual prompt 质量...")
        required_sections = format_prompt_sections(prefix="   - ")

        review_prompt = f"""你是一位资深的 Prompt 质量审查专家。请审查以下执行 prompt 的质量，并在必要时做轻量改进。

【当前页视觉目标】
{visual_suggestion}

【批准的主文字内容】
Headline: {text_content.get('headline', '')}
Subhead: {text_content.get('subhead', '')}
Body: {text_content.get('body', [])}

【当前执行 Prompt】
{visual_prompt}

【审查目标】
1. 保留完整结构：必须保留原有 section headers，尤其是：
{required_sections}
2. 文字正确性优先：TEXT TO RENDER 中的文字必须与批准内容完全一致，不得删减、改写、翻译或补写。
3. 中文渲染优先：如果目标语言是中文，必须强化“中文主文字正常、清晰、稳定”的优先级。
4. 精简但不降级：删除重复、冲突、空话和低价值废话，但不要丢失关键信息。
5. Seed / Reference 边界清晰：保留“当前页语义优先，seed 只控制视觉语法”的规则。
6. 视觉场景忠实：VISUAL SCENE 必须忠于当前页的 visual suggestion，不得擅自换题。

【工作方式】
- 如果当前 prompt 已经结构完整且表达清楚，可直接原样返回。
- 如果需要修改，只做必要的小幅优化。
- 不要把 prompt 改写成别的结构。
- 不要输出解释、注释或总结。

【输出格式】
直接输出改进后的完整 prompt 文本，不要添加任何解释或评论。
"""

        try:
            response = chat_completion_with_fallback(
                self.client, model=self.model, model_fallback=MODEL_FALLBACK_CHAIN,
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "You are a prompt quality reviewer. Preserve section structure, preserve approved text exactly, "
                            "and only make minimal high-value improvements. Output the improved prompt directly."
                        ),
                    },
                    {"role": "user", "content": review_prompt}
                ],
                temperature=0.3
            )
            improved_prompt = response.choices[0].message.content.strip()
            improved_prompt = re.sub(r'<think>.*?</think>', '', improved_prompt, flags=re.DOTALL | re.IGNORECASE).strip()

            logger.info("✅ Visual prompt 审查完成")
            return improved_prompt

        except Exception as e:
            logger.error(f"Visual prompt 审查失败: {e}")
            return visual_prompt

    @staticmethod
    def _normalize_page_type(page_type: str) -> str:
        return (page_type or "content").strip().lower()

    @staticmethod
    def _infer_seed_family(page_type: str) -> str:
        page_type = VisualAgent._normalize_page_type(page_type)
        if page_type in {"section"}:
            return "section"
        if page_type in {"cover", "back", "ending", "hero", "quote"}:
            return "hero"
        if page_type == "background_only":
            return "background_only"
        return "content"

    @staticmethod
    def _page_behavior_instruction(page_type: str) -> str:
        page_type = VisualAgent._normalize_page_type(page_type)
        behavior = {
            "cover": "Establish the opening visual impression with strong hierarchy and a unified focal point.",
            "section": "Emphasize pause and transition with fewer elements and one dominant message.",
            "hero": "Emphasize one dominant message and one dominant visual subject.",
            "quote": "Emphasize one dominant quotation and keep the visual support restrained.",
            "content": "Prioritize structure, readability, and clean grouping of information.",
            "comparison": "Make the contrast immediately legible while keeping the layout disciplined.",
            "flowchart": "Organize the process clearly with readable progression and stable grouping.",
            "data": "Prioritize data clarity and hierarchy over decorative complexity.",
            "infographic": "Organize density through modular grouping and clear scanning paths.",
            "toc": "Keep chapter structure highly legible and easy to scan.",
            "ending": "End with clarity and restraint, avoiding visual clutter.",
            "back": "Keep the closing page clean, quiet, and brand-consistent.",
        }
        return behavior.get(page_type, behavior["content"])

    @staticmethod
    def _collect_text_samples(text_content: Dict, page: Dict) -> List[str]:
        samples: List[str] = []
        for key in ("headline", "subhead"):
            value = text_content.get(key, "")
            if value:
                samples.append(str(value))

        body = text_content.get("body", [])
        if isinstance(body, list):
            samples.extend(str(item).strip() for item in body if str(item).strip())
        elif body:
            samples.append(str(body))

        table_data = text_content.get("table_data") or page.get("table_data")
        if isinstance(table_data, dict):
            samples.extend(str(h) for h in table_data.get("headers", []) if str(h).strip())
            for row in table_data.get("rows", []):
                if isinstance(row, list):
                    samples.extend(str(cell) for cell in row if str(cell).strip())
        elif isinstance(table_data, list):
            for row in table_data:
                if isinstance(row, dict):
                    samples.extend(str(v) for v in row.values() if str(v).strip())
                elif isinstance(row, list):
                    samples.extend(str(v) for v in row if str(v).strip())
                elif row:
                    samples.append(str(row))
        elif table_data:
            samples.append(str(table_data))

        return samples

    def _detect_target_language(self, text_content: Dict, page: Dict) -> str:
        text_blob = "\n".join(self._collect_text_samples(text_content, page))
        cjk_count = len(re.findall(r"[\u4e00-\u9fff]", text_blob))
        latin_count = len(re.findall(r"[A-Za-z]", text_blob))

        if cjk_count > 0 and cjk_count >= latin_count:
            return "Chinese (Simplified)"
        if latin_count > 0 and cjk_count == 0:
            return "English"
        if cjk_count > 0 and latin_count > 0:
            return "Mixed"
        return "Follow approved content plan"

    @staticmethod
    def _format_table_content(table_data) -> str:
        if not table_data:
            return ""

        lines: List[str] = []
        if isinstance(table_data, dict) and "headers" in table_data and "rows" in table_data:
            headers = [str(h) for h in table_data.get("headers", [])]
            if headers:
                lines.append("Columns: " + " | ".join(headers))
            for idx, row in enumerate(table_data.get("rows", []), start=1):
                row_values = [str(cell) for cell in row]
                lines.append(f"Row {idx}: " + " | ".join(row_values))
            return "\n".join(lines)

        if isinstance(table_data, list):
            for idx, row in enumerate(table_data):
                if isinstance(row, dict):
                    if idx == 0:
                        lines.append("Columns: " + " | ".join(str(k) for k in row.keys()))
                    lines.append(f"Row {idx + 1}: " + " | ".join(str(v) for v in row.values()))
                elif isinstance(row, list):
                    prefix = "Header" if idx == 0 else f"Row {idx}"
                    lines.append(f"{prefix}: " + " | ".join(str(v) for v in row))
                elif row:
                    lines.append(str(row))
            return "\n".join(lines)

        return str(table_data)

    def _build_text_to_render_block(self, text_content: Dict, page: Dict) -> str:
        body = text_content.get("body", [])
        if not isinstance(body, list):
            body = [body] if body else []
        body_lines = "\n".join(
            f"{idx}. {str(item).lstrip('-•* ').strip()}"
            for idx, item in enumerate(body, start=1)
            if str(item).strip()
        )
        table_content = self._format_table_content(text_content.get("table_data") or page.get("table_data"))

        return (
            "Headline:\n"
            f"{text_content.get('headline', '')}\n\n"
            "Subtitle:\n"
            f"{text_content.get('subhead', '')}\n\n"
            "Body:\n"
            f"{body_lines}\n\n"
            "Table:\n"
            f"{table_content}"
        ).strip()

    @staticmethod
    def _parse_in_scene_text(visual_suggestion: str) -> tuple[str, str]:
        if not visual_suggestion:
            return "", ""

        lines = visual_suggestion.splitlines()
        cleaned_lines: List[str] = []
        unique = []
        seen = set()

        def add_entry(raw_text: str) -> None:
            cleaned = str(raw_text).strip().lstrip("-•*0123456789.、)）").strip()
            if not cleaned or cleaned in seen:
                return
            seen.add(cleaned)
            unique.append(cleaned)

        header_with_content = re.compile(
            r"^\s*(?:【(?:IN-SCENE TEXT|SCENE TEXT|场景内文字|画面内文字)】|(?:IN-SCENE TEXT|SCENE TEXT|场景内文字|画面内文字)\s*[:：])\s*(.+?)\s*$",
            re.IGNORECASE,
        )
        header_only = re.compile(
            r"^\s*(?:【(?:IN-SCENE TEXT|SCENE TEXT|场景内文字|画面内文字)】|(?:IN-SCENE TEXT|SCENE TEXT|场景内文字|画面内文字)\s*[:：]?)\s*$",
            re.IGNORECASE,
        )
        section_header = re.compile(r"^\s*【[^】]+】\s*$")
        list_item = re.compile(r"^\s*(?:[-•*]|\d+[.)、．]|[A-Za-z][.)])\s+")

        idx = 0
        while idx < len(lines):
            line = lines[idx]
            inline_match = header_with_content.match(line)
            if inline_match:
                add_entry(inline_match.group(1))
                idx += 1
                continue

            if header_only.match(line):
                idx += 1
                block_entries = 0
                while idx < len(lines):
                    block_line = lines[idx]
                    stripped = block_line.strip()
                    if not stripped:
                        idx += 1
                        if block_entries:
                            break
                        continue
                    if section_header.match(block_line):
                        break
                    if block_entries and not list_item.match(block_line):
                        break
                    add_entry(block_line)
                    block_entries += 1
                    idx += 1
                continue

            cleaned_lines.append(line)
            idx += 1

        cleaned_description = "\n".join(cleaned_lines).strip()
        return cleaned_description, "\n".join(unique)

    def _build_style_system_block(
        self,
        *,
        style_definition: str,
        style_config: Dict,
        chapter_theme_hint: str = "",
    ) -> str:
        fonts = style_config.get("fonts", [])
        heading_font = fonts[0] if len(fonts) > 0 else "System heading font"
        body_font = fonts[1] if len(fonts) > 1 else (fonts[0] if fonts else "System body font")
        palette = ", ".join(style_config.get("palette", [])) or "(Follow approved deck palette)"
        chapter_hint_line = f"\nChapter cue: {chapter_theme_hint}" if chapter_theme_hint else ""

        if self.prompt_mode == "minimal":
            return f"""【STYLE SYSTEM】
Deck theme: {style_config.get('user_preference') or style_config.get('description') or style_definition}
Style: {style_definition}{chapter_hint_line}
Palette: {palette}
Typography: Heading={heading_font}; Body={body_font}

- Keep typography stable across the deck.
- Use the palette cleanly and sparingly.
- Prioritize readability and a controlled visual hierarchy."""

        accent_usage = style_config.get("accent_usage", "")
        accent_usage_line = f"\nAccent strategy: {accent_usage}" if accent_usage else ""
        manifesto = style_config.get("manifesto", "")
        manifesto_block = (
            f"\nArt Director manifesto:\n{manifesto}"
            if manifesto else ""
        )

        return f"""【STYLE SYSTEM】
Deck theme: {style_config.get('user_preference') or style_config.get('description') or style_definition}
Style: {style_definition}{chapter_hint_line}
Palette: {palette}
Heading font: {heading_font}
Body font: {body_font}{accent_usage_line}{manifesto_block}

- The font system is chosen once from the deck style and then locked across the entire deck.
- Do not switch font families from slide to slide.
- Default to clean, standard, highly legible typography.
- Do not stylize main text unless explicitly required.
- Use accent colors only where they improve hierarchy or comprehension.
- Follow the manifesto's mood direction while avoiding clichéd default metaphors."""

    def _build_negative_constraints_block(self) -> str:
        if self.prompt_mode == "minimal":
            return """【NEGATIVE CONSTRAINTS】
- No garbled or malformed text
- No duplicate main text
- No extra text
- No text-background conflict"""

        return """【NEGATIVE CONSTRAINTS】
- No garbled or malformed text
- No duplicate main text
- No extra text
- No text-background conflict
- No copied reference impurities
- No multiple competing focal points
- No sacrificing readability for visual flair"""

    @staticmethod
    def _summarize_reference_inputs(reference_image_path: Optional[str], native_images: List[Dict]) -> tuple[str, str, str]:
        summary_lines: List[str] = []
        modes: List[str] = []
        roles: List[str] = []

        if reference_image_path:
            summary_lines.append(f"Template/style anchor: {os.path.basename(reference_image_path)}")
            modes.append("STYLE_ANCHOR")
            roles.append("template style anchor")

        for idx, img in enumerate(native_images, start=1):
            mode = str(img.get("mode", "INTENT_FUSION")).upper()
            role = img.get("semantic_role") or img.get("role") or f"native image {idx}"
            modes.append(mode)
            roles.append(role)
            summary_lines.append(f"Native image {idx}: mode={mode}; role={role}")

        if not summary_lines:
            summary_lines.append("No explicit page-level reference image.")

        unique_modes = []
        for mode in modes:
            if mode not in unique_modes:
                unique_modes.append(mode)

        unique_roles = []
        for role in roles:
            if role not in unique_roles:
                unique_roles.append(role)

        return (
            ", ".join(unique_modes) if unique_modes else "NONE",
            ", ".join(unique_roles) if unique_roles else "none",
            "\n".join(summary_lines),
        )

    @staticmethod
    def _build_seed_reference_summary(seed_family: str, seed_role: str) -> str:
        if seed_role == "family_seed":
            return (
                f"This slide is the seed reference for the {seed_family} family. "
                "It defines visual grammar for follow-up slides, but its specific content must not be reused."
            )
        return (
            f"Use the {seed_family} seed slide only as a visual-grammar reference when it is attached at execution time."
        )

    @staticmethod
    def _build_chapter_theme_hint(page_num: int, chapter_themes: Dict) -> str:
        for chapter in chapter_themes.get("chapters", []):
            pages = chapter.get("pages", [])
            if page_num not in pages:
                continue
            theme = chapter.get("visual_theme", {})
            parts = [
                chapter.get("chapter_name", "").strip(),
                theme.get("accent_color", "").strip(),
                theme.get("visual_motif", "").strip(),
                theme.get("emotional_tone", "").strip(),
            ]
            parts = [part for part in parts if part]
            if parts:
                return " | ".join(parts)
        return ""

    def _build_execution_prompt(
        self,
        *,
        page: Dict,
        page_type: str,
        text_content: Dict,
        visual_suggestion: str,
        style_definition: str,
        style_config: Dict,
        reference_image_path: Optional[str],
        native_images: List[Dict],
        seed_family: str,
        seed_role: str,
        chapter_theme_hint: str = "",
    ) -> str:
        target_language = self._detect_target_language(text_content, page)
        text_to_render = self._build_text_to_render_block(text_content, page)
        visual_description_en, in_scene_text = self._parse_in_scene_text(visual_suggestion)
        communication_goal = (
            page.get("one_takeaway")
            or page.get("core_message")
            or page.get("visual_intent")
            or text_content.get("headline")
            or page.get("section_title")
            or "Communicate the approved content clearly."
        )
        page_behavior = self._page_behavior_instruction(page_type)
        reference_mode, reference_role, reference_summary = self._summarize_reference_inputs(
            reference_image_path, native_images
        )

        chinese_rule = (
            "- Main Chinese text must be normal, clean, readable Simplified Chinese."
            if target_language in {"Chinese (Simplified)", "Mixed"}
            else "- Main text in the target language must be clean, readable, and well-formed."
        )

        if not visual_description_en:
            visual_description_en = "Generate a suitable visual that matches the approved content and page type."

        in_scene_text_block = in_scene_text or "None. Do not invent incidental in-scene text."
        style_system_block = self._build_style_system_block(
            style_definition=style_definition,
            style_config=style_config,
            chapter_theme_hint=chapter_theme_hint,
        )
        negative_constraints_block = self._build_negative_constraints_block()

        scene_guidance = [
            "- Stay faithful to the approved current-slide visual goal.",
            "- Preserve the key objects, actions, mood, spatial relationships, and narrative focus of this slide.",
            "- Build one clear primary visual subject.",
            "- Reserve stable, clean, readable areas for the main text.",
            "- Follow the page behavior for this slide type.",
            "- Keep the deck style consistent while fully using the model's image-generation strength.",
        ]
        if self.prompt_mode != "minimal":
            scene_guidance.extend([
                "- Keep secondary details subordinate to the main narrative focus.",
                "- If references and current-slide semantics conflict, follow the current slide.",
            ])

        prompt = f"""You are generating a single presentation slide image.

【LANGUAGE RULE】
Target language: {target_language}

- All rendered main text must remain exactly in the target language from the approved content plan.
- Do not translate, rewrite, summarize, shorten, or mix languages.
- Prompt instructions may be in English, but rendered slide text must strictly follow the target language.

【NON-NEGOTIABLE】
- Render all approved main text exactly as provided.
{chinese_rule}
- No garbled text, malformed characters, pseudo-Chinese, missing strokes, duplicate text, or random symbols.
- If visual complexity conflicts with text clarity, preserve text clarity.
- You may improve readability through hierarchy, grouping, cards, spacing, and modular layout.
- You must not change the wording itself.
- Main slide text must follow the global deck typography system.
- In-scene incidental text may use a context-specific style only when explicitly required by the visual description, and must not compete with main slide text.

【TEXT TO RENDER】
{text_to_render}

- If a field is empty, do not invent content.
- If text is long, reorganize layout, not wording.
- If a table exists, render all rows and columns completely.

【PAGE SEMANTICS】
Page type: {page_type}
Page behavior: {page_behavior}
Communication goal: {communication_goal}

{style_system_block}

【SEED / REFERENCE CONTROL】
Seed family: {seed_family}
Seed reference: {self._build_seed_reference_summary(seed_family, seed_role)}
Reference mode: {reference_mode}
Reference role: {reference_role}
Reference summary: {reference_summary}

- Current-slide semantics always override references.
- Seed references are only for visual grammar: palette behavior, typography feel, spacing rhythm, material treatment, composition discipline, and module organization.
- Do not inherit the seed slide's specific text, subject matter, scene, infographic skeleton, icon cluster, or unique metaphor.
- Apply the current slide's explicit reference only according to its assigned mode.
- Do not copy accidental text, UI fragments, watermarks, logos, or noise from references.
- Do not let references overpower the main slide text.

【VISUAL SCENE】
{visual_description_en}

Required in-scene text, if any:
{in_scene_text_block}

{chr(10).join(scene_guidance)}

{negative_constraints_block}

【FINAL INSTRUCTION】
This slide succeeds only if:
- the main text is rendered correctly in the target language
- the hierarchy is immediately clear
- the slide matches the approved deck style
- the image feels strong, clean, and controlled"""

        return prompt.strip()

    def _prompt_has_required_sections(self, prompt: str) -> bool:
        return prompt_has_required_sections(prompt)

    def _prompt_preserves_required_text(self, prompt: str, text_content: Dict, page: Dict) -> bool:
        for text in self._collect_text_samples(text_content, page):
            text = str(text).strip()
            if text and text not in prompt:
                return False
        return True

    @staticmethod
    def _extract_first_json_block(content: str) -> Optional[str]:
        text = content or ""
        start_indices = [idx for idx in (text.find("{"), text.find("[")) if idx != -1]
        if not start_indices:
            return None

        for start in sorted(start_indices):
            stack = []
            in_string = False
            escaped = False

            for idx in range(start, len(text)):
                char = text[idx]

                if in_string:
                    if escaped:
                        escaped = False
                    elif char == "\\":
                        escaped = True
                    elif char == '"':
                        in_string = False
                    continue

                if char == '"':
                    in_string = True
                    continue

                if char in "{[":
                    stack.append("}" if char == "{" else "]")
                    continue

                if char in "}]":
                    if not stack or char != stack.pop():
                        break
                    if not stack:
                        return text[start:idx + 1]

        return None

    @classmethod
    def _clean_llm_json_response(cls, content: str) -> str:
        content = re.sub(r'<think>.*?</think>', '', (content or ''), flags=re.DOTALL | re.IGNORECASE).strip()
        content = re.sub(r"^```(?:json)?\s*|```$", "", content, flags=re.MULTILINE | re.IGNORECASE).strip()
        extracted = cls._extract_first_json_block(content)
        return extracted.strip() if extracted else content

    @staticmethod
    def _default_chapter_visual_themes(heading_font: str, body_font: str, base_color: str) -> Dict:
        return {
            "global_consistency": {
                "paper_texture": "统一的纸张质感",
                "typography": f"{heading_font} + {body_font}",
                "composition": "统一的构图方式",
                "base_color": base_color
            },
            "chapters": []
        }


    def _parse_user_color_preference(self, user_preference: str) -> list:
        """
        智能解析用户的配色意图
        使用 LLM 理解用户的颜色描述，返回对应的 hex 色值列表
        """
        try:
            # 使用 LLM 理解用户的配色意图
            prompt = f"""Extract color palette from user preference: "{user_preference}"

Output ONLY a JSON array of hex colors (2-4 colors). Examples:
- "红白黑" → ["#E53935", "#FFFFFF", "#000000"]
- "蓝色科技风" → ["#1E88E5", "#FFFFFF", "#263238"]
- "warm and professional" → ["#FF6B6B", "#4ECDC4", "#F7FFF7"]

Output format: ["#HEX1", "#HEX2", "#HEX3"]"""

            response = chat_completion_with_fallback(
                self.client, model=self.model, model_fallback=MODEL_FALLBACK_CHAIN,
                messages=[
                    {"role": "system", "content": "You are a color expert. Output valid JSON array only."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3
            )
            content = self._clean_llm_json_response(response.choices[0].message.content)

            colors = json.loads(content)
            if isinstance(colors, list) and len(colors) >= 2:
                logger.info(f"✅ 从用户偏好 '{user_preference}' 中解析到配色: {colors}")
                return colors
        except Exception as e:
            logger.warning(f"⚠️ 配色解析失败: {e}")

        # 简单的关键词匹配作为最终 fallback
        if any(kw in user_preference.lower() for kw in ['红', 'red', '白', 'white', '黑', 'black']):
            logger.info(f"✅ 使用关键词匹配: 红白黑配色")
            return ["#E53935", "#FFFFFF", "#000000"]

        # 默认商务配色
        logger.warning(f"⚠️ 使用默认商务配色")
        return ["#FFFFFF", "#000000", "#757575"]

    def generate_chapter_visual_themes(self, narrative_outline: List[Dict], style_config: Dict) -> Dict:
        """
        分析内容大纲，为每个故事章节生成视觉主题

        这个函数会：
        1. 识别内容中的不同故事章节
        2. 为每个章节定义视觉主题（点缀色、视觉母题、纸艺技法、情感基调）
        3. 确保全局一致性（纸张、字体、构图、基础色调）

        Returns:
            {
              "global_consistency": {...},
              "chapters": [...]
            }
        """
        logger.info("🎨 Visual Agent: 正在生成章节视觉主题...")

        # 构建内容大纲摘要
        outline_summary = "\n".join([
            f"P{p.get('page_num', p.get('slide_number', i+1))} ({p.get('type','content')}): {p.get('text_content', {}).get('headline', '') if p.get('text_content') else p.get('title', '')} | Section: {p.get('section_title', 'N/A')}"
            for i, p in enumerate(narrative_outline)
        ])

        # 提取全局风格信息
        fonts = style_config.get('fonts', [])
        heading_font = fonts[0] if len(fonts) > 0 else "Sans-serif"
        body_font = fonts[1] if len(fonts) > 1 else "Sans-serif"
        palette = style_config.get('palette', [])
        base_color = palette[0] if palette else "#FFFFFF"

        # 构建 prompt（使用字符串拼接避免 f-string 格式化问题）
        outline_for_prompt = outline_summary
        palette_str = ", ".join(palette)

        prompt = (
            "分析这份 PPT 大纲，识别故事章节，生成视觉主题。\n\n"
            "【PPT 大纲】\n" + outline_for_prompt + "\n\n"
            "【全局风格】\n"
            "字体=" + heading_font + "/" + body_font + "\n"
            "基础色=" + base_color + "\n"
            "调色板=" + palette_str + "\n\n"
            "【任务】识别故事章节，定义每章节：点缀色、视觉母题、纸艺技法、情感基调。\n\n"
            "【输出格式】只输出 JSON，不要任何其他文字：\n"
            '{"g":{"pt":"纸张","ty":"字体","co":"构图","bc":"基础色"},"c":[{"n":"章节名","p":[2,3],"a":"点缀色","m":"母题","t":"技法","e":"情感"}]}\n\n'
            "【重要】点缀色在调色板内，母题有辨识度，全局约束严格"
        )


        try:
            response = chat_completion_with_fallback(
                self.client, model=self.model, model_fallback=MODEL_FALLBACK_CHAIN,
                messages=[
                    {"role": "system", "content": "你是一位专业的艺术总监。严格只输出 JSON，不要输出任何其他文字。"},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3
            )

            result_text = self._clean_llm_json_response(response.choices[0].message.content)

            # 解析 JSON
            chapter_themes = json.loads(result_text)

            logger.info(f"✅ 已生成 {len(chapter_themes.get('chapters', []))} 个章节的视觉主题")
            return chapter_themes

        except json.JSONDecodeError as e:
            logger.warning(f"⚠️ 章节视觉主题 JSON 解析失败，使用默认值: {e}")
            return self._default_chapter_visual_themes(heading_font, body_font, base_color)
        except Exception as e:
            logger.warning(f"⚠️ 生成章节视觉主题失败，使用默认值: {e}")
            return self._default_chapter_visual_themes(heading_font, body_font, base_color)

    def define_style(self, constraints: Dict, assets: Dict, template_info: Dict = None) -> Union[str, Dict]:
        """
        Step 1: 风格定义 (Style Definition)
        无限风格生成：根据 NarrativeAgent 提取的 style_preference 实时铸造。
        """
        if template_info:
            logger.info("🎨 Visual Agent: 进入【模版克隆模式】(Template Mode)")
            style_desc = template_info.get('style_description', '')
            palette = template_info.get('color_palette', [])
            fonts = template_info.get('fonts', [])

            palette_str = ", ".join(palette)
            style_desc_str = f"TEMPLATE_MODE: Follow the provided template style. {style_desc}. Palette: {palette_str}"

            style_config = {
                "mode": "template",
                "description": style_desc,
                "palette": palette,
                "fonts": fonts
            }
            return style_desc_str, style_config

        logger.info("🎨 Visual Agent: 正在定义视觉风格 (AI Minting - Content Aware)...")
        
        # 提取用户偏好，默认为 "Modern Professional Business"
        user_preference = constraints.get('style_preference', '') or 'Modern Professional Business'
        
        brand_colors = constraints.get('brand_colors', [])

        # 检查是否命中系统内置风格库 (Curated Style Library)
        curated_style = get_curated_style(user_preference)
        if curated_style:
            logger.info(f"✨ 命中系统内置风格库: {user_preference} -> {curated_style['description'][:50]}...")
            style_desc_str = f"Style: {curated_style.get('description')}. Palette: {', '.join(curated_style.get('palette', []))}."
            style_config = curated_style.copy()
            if "aliases" in style_config:
                del style_config["aliases"]
            style_config['mode'] = 'ai_minting_curated'
            
            if brand_colors:
                brand_colors_str = ', '.join(brand_colors)
                brand_integration_msg = f" The user provided a logo with dominant colors: {brand_colors_str}. As an expert Art Director, judge if these colors naturally fit the requested style. If yes, seamlessly incorporate them as subtle accents or main colors. If they severely clash (e.g. neon green logo on a dark luxury theme), prioritize the requested style's aesthetics and ignore the logo colors for the background generation."
                style_desc_str += brand_integration_msg
                style_config['description'] = style_config.get('description', '') + brand_integration_msg

            return style_desc_str, style_config

        topic = constraints.get('presentation_type', 'Business Presentation')
        audience = constraints.get('target_audience', 'General Professional')

        brand_color_text = f"- Brand Colors (Extracted from Logo): {', '.join(brand_colors)}\nIf Brand Colors are provided, USE THEM as the primary inspiration for the palette, ensuring high contrast for text reading." if brand_colors else ""

        # 如果有设计指导文件，注入到 prompt
        style_guide_section = ""
        if constraints.get("style_guide_content"):
            style_guide_content = constraints.get("style_guide_content", "")
            style_guide_section = f"""
【Design Guide from User】
The user provided the following design guide. You MUST strictly follow these visual principles:

---
{style_guide_content}
---

Based on the above guide, define the visual style for this presentation.
"""

        prompt = f"""You are a world-class Art Director. Define a cohesive visual style guide for a presentation.

【Context】
- Topic: {topic}
- Audience: {audience}
- User Preference Vibe: "{user_preference}"
{brand_color_text}
{style_guide_section}

【Task】
If User Preference is vague, default to a **"Modern Professional Business"** style (Clean, Minimalist, San Francisco/Inter font, High legibility, subtle gradients, "Apple Keynote" quality).
If User Preference is specific (e.g. "Cyberpunk", "Warm Retro", "Academic"), adapt strictly to that.

Output a STRICT visual design system in JSON format.

Format:
{{
    "description": "A comprehensive visual description for image generation prompts...",
    "palette": ["#Hex1", "#Hex2", "#Hex3"],
    "fonts": ["TitleFont", "BodyFont"],
    "shape_language": "Rounded/Sharp/Organic",
    "imagery_style": "Photorealistic/Minimalist/3D/Illustration"
}}

Ensure the palette has high contrast for text reading.
"""

        try:
            response = chat_completion_with_fallback(
                self.client, model=self.model, model_fallback=MODEL_FALLBACK_CHAIN,
                messages=[
                    {"role": "system", "content": "You are an expert Art Director. Output valid JSON only."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7
            )
            content = response.choices[0].message.content.strip()

            # 记录原始返回内容用于调试
            logger.info(f"LLM 原始返回内容: {content[:200]}...")

            content = self._clean_llm_json_response(content)

            style_data = json.loads(content)

            style_desc_str = f"Style: {style_data.get('description')}. Palette: {', '.join(style_data.get('palette', []))}."
            style_config = style_data
            style_config['mode'] = 'ai_minting'

            return style_desc_str, style_config

        except Exception as e:
            logger.error(f"风格定义失败: {e}")
            logger.error(f"LLM 返回内容: {content if 'content' in locals() else 'N/A'}")

            # 智能 fallback：解析用户的配色意图
            fallback_palette = self._parse_user_color_preference(user_preference)
            fallback_desc = f"Minimalist Business style with {user_preference}. Clean, professional, high contrast."

            return fallback_desc, {
                "mode": "fallback",
                "description": fallback_desc,
                "palette": fallback_palette,
                "user_preference": user_preference
            }

    # ── Content-aware layout assignment ──

    @staticmethod
    def _assign_layout(page_type: str, text_content: dict, prev_layout: str = None, page: dict = None) -> tuple:
        """Pick a layout based on semantic page type."""
        # Check for table/chart data
        if page:
            table_data = page.get('text_content', {}).get('table_data') or page.get('table_data')
            visualization = page.get('visualization', '')
            if table_data:
                if visualization in ('bar', 'line', 'pie'):
                    return 'chart_from_table', "Data visualization chart (bar/line/pie) derived from table data."
                return 'content', VisualAgent.LAYOUT_LIBRARY.get('content', '')

        # Map semantic page types to basic layout hints (without forcing rigid boxes)
        layout_map = {
            'cover': ('full_screen_immersive', VisualAgent.LAYOUT_LIBRARY.get('full_screen_immersive', '')),
            'back': ('centered_headline', VisualAgent.LAYOUT_LIBRARY.get('centered_headline', '')),
            'ending': ('centered_headline', VisualAgent.LAYOUT_LIBRARY.get('centered_headline', '')),
            'section': ('minimalist_hero', VisualAgent.LAYOUT_LIBRARY.get('minimalist_hero', '')),
            'hero': ('minimalist_hero', VisualAgent.LAYOUT_LIBRARY.get('minimalist_hero', '')),
            'quote': ('wide_quote_card', VisualAgent.LAYOUT_LIBRARY.get('wide_quote_card', '')),
            'infographic': ('dense_infographic', VisualAgent.LAYOUT_LIBRARY.get('dense_infographic', '')),
            'toc': ('three_column_grid', VisualAgent.LAYOUT_LIBRARY.get('three_column_grid', '')),
            'data': ('big_number_data', VisualAgent.LAYOUT_LIBRARY.get('big_number_data', '')),
            'flowchart': ('process_flow', VisualAgent.LAYOUT_LIBRARY.get('process_flow', '')),
            'comparison': ('split_screen_contrast', VisualAgent.LAYOUT_LIBRARY.get('split_screen_contrast', ''))
        }
        
        pick = layout_map.get(page_type, ('content', VisualAgent.LAYOUT_LIBRARY.get('content', '')))[0]

        # Avoid duplicates for generic content pages
        if pick == prev_layout and pick in ['content', 'left_text_right_visual', 'top_visual_bottom_text', 'three_column_grid']:
            for alt in ['left_text_right_visual', 'top_visual_bottom_text', 'three_column_grid']:
                if alt != prev_layout:
                    pick = alt
                    break

        return pick, VisualAgent.LAYOUT_LIBRARY.get(pick, "Standard Layout")

    def _get_page_type_specific_instruction(self, page_type: str) -> str:
        """根据页面类型生成特定的设计指令，更侧重语义而非死板构图"""
        instructions = {
            "cover": "【COVER DESIGN】Max visual impact. Title must be MASSIVE and clearly legible. Use a symbolic, high-end visual anchor.",
            "section": "【SECTION TRANSITION】Minimalist and bold. The Section Title should be the absolute focus. Create a sense of 'pause'.",
            "hero": "【HERO / GOLDEN SENTENCE】Impact over detail. Use massive typography for the core message. The background visual should organically support the metaphor of the text.",
            "quote": "【QUOTE CARD】High impact quotation. The quote text must be large and prominent, elegantly balanced with the visual context.",
            "toc": "【TABLE OF CONTENTS】Structured and clean. Organize chapters clearly with high legibility.",
            "content": "【CONTENT SLIDE】Organize the text logically. Let the text structure dictate the layout naturally, balancing it with a relevant visual element without forcing it into rigid boxes.",
            "data": "【DATA VISUALIZATION】Focus on the key metric. Integrate the data visualization seamlessly into the scene's aesthetic.",
            "infographic": "【INFOGRAPHIC】Organize complex information clearly. Use logical grouping and visual hierarchy to manage high density, allowing the specific semantic structure (like a cycle, pyramid, or web) to form naturally.",
            "flowchart": "【PROCESS / FLOW】Visually connect the steps. Draw a clear directional flow that matches the text, blending the nodes organically into the environment.",
            "comparison": "【COMPARISON】Create a visual duality. Contrast the two concepts clearly using layout, lighting, or composition.",
            "ending": "【ENDING】Simple and memorable. Clean background, elegant text placement.",
            "back": "【BACK COVER】Simple and clean. Contact info or final branding element. Minimal decorative elements, visually echo the cover page."
        }
        return instructions.get(page_type, instructions['content'])

    # ── Main plan generation ──

    def save_visual_plan_md(
        self,
        narrative_outline: List[Dict],
        style_config: Dict,
        image_assets_manager,
        output_path: str = "output/visual_plan.md"
    ) -> None:
        """
        生成 visual_plan.md 文件

        根据 content_plan.md 中的语义锚点和 image_assets.json 中的图片资产，
        为每个页面分配图片并生成图片块。

        Args:
            narrative_outline: 叙事大纲（来自 content_plan.json）
            style_config: 风格配置
            image_assets_manager: 图片资产管理器
            output_path: 输出路径
        """
        logger.info("🎨 Visual Agent: 正在生成 visual_plan.md...")

        from pathlib import Path
        from ..utils.doc_normalizer import ImageBlock

        # 确保输出目录存在
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)

        # 构建 Markdown 内容
        lines = ["# Visual Plan", "", ""]

        # 遍历每个页面
        for page in narrative_outline:
            page_num = page.get('page_num', 0)
            page_type = page.get('type', 'content')
            text_content = page.get('text_content', {})
            headline = text_content.get('headline', '')

            # 添加页面标题
            lines.append(f"## 第 {page_num} 页 · {headline or page_type}")
            lines.append("")

            # 查找该页面的图片锚点
            image_anchors = page.get('image_anchors', [])

            # 为每个锚点分配图片
            for anchor in image_anchors:
                # 从 image_assets_manager 中查找匹配的图片
                matching_assets = image_assets_manager.get_assets_by_anchor(anchor)

                if not matching_assets:
                    # 如果没有匹配的图片，创建待补图占位
                    image_block = ImageBlock(
                        path="PLACEHOLDER",
                        mode="INTENT_FUSION",
                        role=f"图片锚点：{anchor}",
                        position="center"
                    )
                    lines.append(image_block.to_markdown())
                    lines.append("")
                else:
                    # 为每个匹配的图片生成图片块
                    for asset in matching_assets:
                        # 推荐模式：优先使用用户指定的 mode，否则使用推荐模式
                        mode = asset.mode or asset.recommended_mode or ImageMode.INTENT_FUSION

                        # 根据图片类型推荐位置
                        position = self._recommend_position(asset.image_type, page_type)

                        # 生成角色描述
                        role = asset.role or asset.description or f"图片锚点：{anchor}"

                        # 转换 mode 为大写格式
                        if hasattr(mode, 'value'):
                            mode_str = mode.value.upper()
                        else:
                            mode_str = str(mode).upper()

                        image_block = ImageBlock(
                            path=asset.path,
                            mode=mode_str,
                            role=role,
                            position=position
                        )
                        lines.append(image_block.to_markdown())
                        lines.append("")

            # 如果页面没有图片锚点，但根据页面类型需要图片，添加占位
            if not image_anchors and page_type in ['cover', 'section', 'hero']:
                image_block = ImageBlock(
                    path="PLACEHOLDER",
                    mode="INTENT_FUSION",
                    role=f"{page_type} 页面背景图",
                    position="full"
                )
                lines.append(image_block.to_markdown())
                lines.append("")

            lines.append("---")
            lines.append("")

        # 写入文件
        content = '\n'.join(lines)
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(content)

        logger.info(f"✅ visual_plan.md 已生成: {output_path}")

    def _recommend_position(self, image_type: Optional[str], page_type: str) -> str:
        """
        根据图片类型和页面类型推荐图片位置

        Args:
            image_type: 图片类型（截图/人物/产品/图表/场景）
            page_type: 页面类型

        Returns:
            推荐的位置（center/left/right/full）
        """
        # 封面和章节页通常使用全屏
        if page_type in ['cover', 'section', 'hero']:
            return 'full'

        # 根据图片类型推荐位置
        if image_type == '截图':
            return 'center'
        elif image_type == '人物':
            return 'right'
        elif image_type == '产品':
            return 'center'
        elif image_type == '图表':
            return 'center'
        elif image_type == '场景':
            return 'full'
        else:
            return 'center'

    def generate_visual_plan(self, narrative_outline: List[Dict], style_definition_tuple: tuple, assets: Dict, template_info: Dict = None, meta: Dict = None) -> List[Dict]:
        """生成完整的视觉执行计划 (Visual Plan)"""
        logger.info("🎨 Visual Agent: 正在生成视觉执行计划...")

        # 处理默认参数
        meta = meta or {}

        if isinstance(style_definition_tuple, tuple):
            style_definition, style_config = style_definition_tuple
        else:
            style_definition = str(style_definition_tuple)
            style_config = {}

        palette = style_config.get('palette', [])

        # Minimal mode: simplified color constraints
        if self.prompt_mode == "minimal":
            if len(palette) >= 2:
                color_constraint = f"Use palette: {', '.join(palette[:3])}. Background: {palette[0]}, Text: {palette[1]}."
            elif palette:
                color_constraint = f"Palette: {', '.join(palette)}."
            else:
                color_constraint = ""
        else:
            # Verbose mode: color palette as design reference, not rigid rules
            if len(palette) >= 3:
                accents = ", ".join(palette[2:])
                color_constraint = (
                    f"Color Palette: Background={palette[0]}, Primary Text={palette[1]}, Accent/Highlight={accents}. "
                    f"Use this palette as your design foundation. "
                    f"Your goal is to make the most important information on each slide immediately obvious to the reader — "
                    f"use color, size, and weight differences naturally to create visual hierarchy. "
                    f"The accent colors are available for emphasis where YOU judge it adds clarity (e.g., a key number, a critical word, a decorative element)."
                )
            elif palette:
                color_constraint = f"Palette: {', '.join(palette)}. Primary Background MUST BE {palette[0]}, Primary Text MUST BE {palette[1]}."
            else:
                color_constraint = ""

        font_constraint = ""
        if style_config.get('fonts'):
            fonts_str = ', '.join(style_config['fonts'])
            if self.prompt_mode == "minimal":
                font_constraint = f"\n- Typography: Use {fonts_str} for consistency."
            else:
                font_constraint = f"\n- Typography (STRICTLY ENFORCED): You MUST use these exact fonts on EVERY single slide: {fonts_str}. Headings must ALWAYS use the heading font, and body text must ALWAYS use the body font. Never change font families between slides. NEVER use random or generic fonts."

        manifesto = style_config.get('manifesto', '')
        if manifesto:
            if self.prompt_mode == "minimal":
                # Minimal mode: extract only key points from manifesto
                manifesto_block = f"\n- Design Direction: {manifesto.split('.')[0]}. Use diverse visual subjects across slides."
            else:
                # Verbose mode: full manifesto with detailed instructions
                manifesto_block = (
                    f"\n- Design System Manifesto (Art Director):\n{manifesto}\n\n"
                    "INSTRUCTION: Follow the color strategy and mood direction above. Adhere to the 'Cliche Avoidance' bans (these ban specific clichéd elements, NOT entire categories like people, architecture, or nature). "
                    "Beyond these constraints, you have FULL creative freedom and are STRONGLY ENCOURAGED to use diverse, figurative visual metaphors: "
                    "human silhouettes, architectural scenes, natural landscapes, dramatic lighting on real-world objects, aerial perspectives, close-up textures of meaningful materials, etc. "
                    "AVOID falling back on generic abstract geometric shapes (plain stone monoliths, glass cubes, floating rectangles) as the primary visual subject for every slide — these should be used sparingly, not as default. "
                    "Each slide should feature a DISTINCT visual subject that serves its specific content, creating variety across the deck."
                )
        else:
            manifesto_block = ""

        accent_usage = style_config.get('accent_usage', '')
        accent_usage_block = f"\n- Accent color design reference: {accent_usage}" if accent_usage else ""

        if self.prompt_mode == "minimal":
            design_system = f"""【Visual Style】
- Style: {style_definition}
- Colors: {color_constraint}{font_constraint}{manifesto_block}
- Maintain visual consistency across all slides."""
        else:
            design_system = f"""【Visual Design System】
- Global Style: {style_definition}
- Color Palette: {color_constraint}{accent_usage_block}
- Consistency: ALL slides must use the same palette and fonts for a cohesive deck.{font_constraint}{manifesto_block}"""

        # 5. Global Context Injection (Summary of the whole deck)
        # Create a condensed outline string
        outline_summary = "\n".join([
            f"- P{p.get('page_num', p.get('slide_number', idx+1))} ({p.get('type','content')}): {p.get('text_content', {}).get('headline', p.get('title', ''))} - {p.get('one_takeaway', p.get('core_message', ''))}"
            for idx, p in enumerate(narrative_outline[:10])
        ])
        if len(narrative_outline) > 10:
            outline_summary += "\n... (more slides)"

        # ========== 新增：生成章节视觉主题和内容深度分析 ==========
        # 1. 生成章节视觉主题（确保视觉一致性 + 章节辨识度）
        chapter_themes = self.generate_chapter_visual_themes(narrative_outline, style_config)

        # 2. 分析内容深度（识别关键情节和泪点）
        content_analysis = self.analyze_content_depth(narrative_outline)

        # 提取全局一致性约束
        global_consistency = chapter_themes.get('global_consistency', {})
        chapters = chapter_themes.get('chapters', [])
        key_pages = {kp['page']: kp for kp in content_analysis.get('key_pages', [])}

        logger.info(f"📋 章节主题: {len(chapters)} 个章节")
        logger.info(f"📋 关键页面: {len(key_pages)} 个")
        # ========================================================

        visual_plan = []
        prev_layout = None
        
        # 预先处理所有需要的提示词和变量，以便后续可以并行化
        tasks = []

        # Track which page types have been seen — first of each type is a potential seed page
        seen_types = set()

        for idx, page in enumerate(narrative_outline):
            page_type = page.get('type', 'content').lower()
            text_content = page.get('text_content', {})
            visual_suggestion = page.get('visual_description', page.get('visual_suggestion', ''))

            # 1. Reference image routing
            reference_image_path = None
            source_img_match = re.search(r'Use source image: \[(.*?)\]', visual_suggestion)
            if source_img_match:
                logger.info(f"📸 发现源图片引用: {source_img_match.group(1)}")

            if template_info and not reference_image_path:
                refs = template_info.get('reference_images', {})
                routing = {
                    'cover': refs.get('ref_cover'),
                    'toc': refs.get('ref_toc') or refs.get('ref_cover'),
                    'hero': refs.get('ref_hero') or refs.get('ref_section') or refs.get('ref_cover'),
                    'section': refs.get('ref_section') or refs.get('ref_cover'),
                    'back': refs.get('ref_back') or refs.get('ref_cover'),
                    'ending': refs.get('ref_back') or refs.get('ref_cover'),
                    'data': refs.get('ref_content'), # fallback to content ref for data
                }
                reference_image_path = routing.get(page_type, refs.get('ref_content'))
                if not reference_image_path and refs:
                    reference_image_path = list(refs.values())[0]

            # 2. Content-aware layout assignment
            layout_name, layout_desc = self._assign_layout(page_type, text_content, prev_layout, page)
            prev_layout = layout_name

            # Seed page vs follow-up page metadata
            CONTENT_FAMILY = {'content', 'framework', 'flowchart', 'comparison', 'data', 'toc', 'breathing', 'infographic'}
            type_family = 'content' if page_type in CONTENT_FAMILY else page_type
            is_seed_page = type_family not in seen_types
            seen_types.add(type_family)
            seed_role = 'family_seed' if is_seed_page else 'follow_up'

            if is_seed_page:
                seed_usage_rule = (
                    "种子页：负责定义这一类页面的风格、排版语言和视觉语法，供后续同类页面继承。"
                )
            else:
                seed_usage_rule = (
                    "后续页：只能继承种子页的风格、字体、配色、间距和版式语法；禁止复用种子页的文字、示例内容、"
                    "核心画面主体、独特图形组合或信息图骨架。"
                )

            # Task 3: Handle table/chart pages (DataVisualizer)
            if layout_name in ('chart_from_table',):
                logger.info(f"📊 Visual Agent: Skipping prompt gen for data page (layout={layout_name})")
                plan_item = page.copy()
                plan_item['visual_description'] = page.get('visual_description', visual_suggestion)
                plan_item['final_visual_prompt'] = "DATA_VISUALIZATION_PLACEHOLDER"
                plan_item['visual_prompt'] = plan_item['final_visual_prompt']
                plan_item['reference_image'] = reference_image_path
                plan_item['layout'] = layout_name
                plan_item['logo_path'] = (assets.get('logo_path') or meta.get('logo_file') or (template_info.get('logo_path') if template_info else None))
                plan_item['logo_location'] = template_info.get('logo_location', 'Top-Right') if template_info else 'Top-Right'
                plan_item['style_config'] = style_config
                plan_item['use_data_visualizer'] = True
                plan_item['seed_role'] = seed_role
                plan_item['seed_usage_rule'] = seed_usage_rule

                plan_item['chart_type'] = page.get('visualization', 'bar')

                tasks.append({'skip_llm': True, 'result': plan_item})
                continue

            page_num = page.get('page_num', idx + 1)
            chapter_theme_hint = self._build_chapter_theme_hint(page_num, chapter_themes)
            native_images = page.get('native_images', [])
            seed_family = self._infer_seed_family(page_type)

            base_prompt = self._build_execution_prompt(
                page=page,
                page_type=page_type.upper(),
                text_content=text_content,
                visual_suggestion=visual_suggestion,
                style_definition=style_definition,
                style_config=style_config,
                reference_image_path=reference_image_path,
                native_images=native_images,
                seed_family=seed_family,
                seed_role=seed_role,
                chapter_theme_hint=chapter_theme_hint,
            )

            tasks.append({
                'skip_llm': False,
                'page': page,
                'layout_name': layout_name,
                'reference_image_path': reference_image_path,
                'seed_family': seed_family,
                'seed_role': seed_role,
                'seed_usage_rule': seed_usage_rule,
                'base_prompt': base_prompt
            })

        # 并发执行所有 LLM 调用
        from concurrent.futures import ThreadPoolExecutor, as_completed
        logger.info(f"🎨 Visual Agent: 正在并行生成 {len([t for t in tasks if not t['skip_llm']])} 页的视觉提示词...")

        def generate_single_prompt(idx, task):
            if task.get('skip_llm'):
                return idx, task['result']
            
            page = task['page']
            text_content = page.get('text_content', {})
            seed_role = task.get('seed_role', '')
            seed_usage_rule = task.get('seed_usage_rule', '')
            try:
                final_prompt = task['base_prompt']

                # Reviewer 已降级为工具能力，这里做轻量审查与去冗余
                reviewed_prompt = self.review_visual_prompt(
                    visual_prompt=final_prompt,
                    visual_suggestion=page.get('visual_description', page.get('visual_suggestion', '')),
                    text_content=text_content
                )

                if reviewed_prompt:
                    final_prompt = reviewed_prompt

                # 清理 <think> 标签及禁止格式
                forbidden_patterns = [
                    (r'<think>.*?</think>', 'reasoning tag'),
                    (r'```', 'markdown code block'),
                    (r'\*\*[^*]+\*\*', 'markdown bold'),
                    (r'\*[^*]+\*', 'markdown italic'),
                ]
                cleaned_prompt = final_prompt
                for pattern, desc in forbidden_patterns:
                    if re.search(pattern, cleaned_prompt, re.MULTILINE):
                        cleaned_prompt = re.sub(pattern, '', cleaned_prompt, flags=re.MULTILINE | re.DOTALL)
                        logger.warning(f"⚠️ P{page.get('page_num')} 已清理禁止格式 ({desc})，已自动修复")

                # 清理多余空行
                cleaned_prompt = re.sub(r'\n{3,}', '\n\n', cleaned_prompt)
                final_prompt = cleaned_prompt.strip()

                if (
                    not self._prompt_has_required_sections(final_prompt) or
                    not self._prompt_preserves_required_text(final_prompt, text_content, page)
                ):
                    logger.warning(f"⚠️ P{page.get('page_num')} 审查后的 prompt 结构或文字不完整，回退到基础模板")
                    final_prompt = task['base_prompt']

                plan_item = page.copy()
                plan_item['visual_description'] = page.get('visual_description', page.get('visual_suggestion', ''))
                plan_item['final_visual_prompt'] = final_prompt
                plan_item['visual_prompt'] = final_prompt
                plan_item['reference_image'] = task['reference_image_path']
                plan_item['layout'] = task['layout_name']
                plan_item['logo_path'] = (assets.get('logo_path') or meta.get('logo_file') or (template_info.get('logo_path') if template_info else None))
                plan_item['logo_location'] = template_info.get('logo_location', 'Top-Right') if template_info else 'Top-Right'
                plan_item['style_config'] = style_config
                plan_item['seed_family'] = task.get('seed_family', '')
                plan_item['seed_role'] = seed_role
                plan_item['seed_usage_rule'] = seed_usage_rule

                return idx, plan_item

            except Exception as e:
                logger.error(f"Prompt生成失败 (Page {page.get('page_num')}): {e}")
                # fallback item
                plan_item = page.copy()
                plan_item['visual_description'] = page.get('visual_description', page.get('visual_suggestion', ''))
                plan_item['final_visual_prompt'] = "A professional slide background."
                plan_item['visual_prompt'] = plan_item['final_visual_prompt']
                plan_item['layout'] = task['layout_name']
                plan_item['style_config'] = style_config
                plan_item['seed_role'] = seed_role
                plan_item['seed_usage_rule'] = seed_usage_rule
                return idx, plan_item

        results = [None] * len(tasks)
        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = {executor.submit(generate_single_prompt, i, task): i for i, task in enumerate(tasks)}
            for future in as_completed(futures):
                idx, plan_item = future.result()
                results[idx] = plan_item

        visual_plan = results

        # Bonus: generate blank template slides (reuse main pipeline constraints)
        if visual_plan:
            logger.info("➕ 追加模板页 (Blank Template Slides)...")

            manifesto_ban = "\n- ENFORCE MANIFESTO BANS: Avoid the specific clichéd elements listed in 'Cliche Avoidance'." if manifesto else ""

            tpl_neg_constraints = f"""【Negative Constraints (CRITICAL)】
- ABSOLUTELY ZERO TEXT of any kind. No titles, no labels, no numbers, no letters, no placeholders, no watermarks, no captions. Not even single characters.
- ABSOLUTELY ZERO LOGOS or brand marks.
- NO black blocks, NO solid black rectangles. Use seamless full-bleed composition.
- Do NOT use random, inconsistent fonts or typography elements.{manifesto_ban}"""

            tpl_system_prompt = (
                "You are an expert Prompt Engineer for Nano Banana 2 (Gemini Image). "
                "OUTPUT FORMAT: You must output EXACTLY one plain-text string. "
                "DO NOT use any markup symbols: no asterisks, no hashes, no backticks, no bullet markers, no bold, no italic, no code blocks."
            )

            tpl_shared_prompt = f"""Generate a high-fidelity image generation prompt for a BLANK TEMPLATE slide background.

{design_system}

【TEMPLATE SLIDE PURPOSE】
This is a blank canvas slide appended at the end of the deck. The user will place their own text, images, and tables directly on top. Your job is to describe an EXTREMELY RESTRAINED, MINIMAL background that:
1. Perfectly matches the color palette and mood of the deck — but keeps it FAR simpler than regular content slides.
2. Uses AT LEAST 70% of the canvas as a flat, solid color or very subtle tonal gradient — no patterns, no textures, no scattered shapes in the central area.
3. May have ONLY quiet, small accent touches (e.g., a thin geometric border, a delicate corner motif, or a gentle edge fade) confined to the outermost 15% of the frame. The centre MUST be clean empty space.
4. Contains ABSOLUTELY ZERO TEXT — no titles, no labels, no numbers, no placeholders, nothing resembling written characters.
5. Prioritises LEGIBILITY above all else. If in doubt, keep it even simpler — a near-empty background is always better than one that interferes with text.

Think of it as a premium, barely-decorated editorial page — restrained, spacious, and text-ready.

{tpl_neg_constraints}

【Output】
CRITICAL: Output ONLY the raw image-generation prompt text. No markdown formatting (no bold, no italic, no bullet markers, no headings, no code blocks). Pure plain text only."""

            def generate_template(tpl_type, title, layout):
                try:
                    resp = chat_completion_with_fallback(
                        self.client, model=self.model, model_fallback=MODEL_FALLBACK_CHAIN,
                        messages=[
                            {"role": "system", "content": tpl_system_prompt},
                            {"role": "user", "content": tpl_shared_prompt}
                        ],
                        temperature=0.4
                    )
                    # 清理 MiniMax 模型返回的 <think> 思考过程标签
                    raw_prompt = resp.choices[0].message.content.strip()
                    clean_prompt = re.sub(r'<think>.*?</think>', '', raw_prompt,
                                          flags=re.DOTALL | re.IGNORECASE).strip()

                    return {
                        "type": tpl_type,
                        "title": title,
                        "visual_description": "空白模板页背景，供用户后续叠加自定义内容。",
                        "final_visual_prompt": clean_prompt,
                        "visual_prompt": clean_prompt,
                        "reference_image": None,
                        "style_config": style_config,
                        "layout": layout,
                        "seed_role": "follow_up",
                        "seed_usage_rule": "模板页：保持整套 deck 的风格一致，但不得引入额外文本或抢占内容层级。",
                    }
                except Exception as e:
                    logger.error(f"模板页生成失败: {e}")
                    palette = style_config.get("palette", [])
                    base_bg = palette[0] if palette else "#F7F4EE"
                    edge_accent = palette[2] if len(palette) > 2 else (palette[1] if len(palette) > 1 else "#C8B8A6")
                    fallback_prompt = (
                        f"A blank premium presentation slide background with a clean full-bleed surface in {base_bg}, "
                        f"extremely subtle tonal variation, restrained edge accents in {edge_accent} confined to the outer frame, "
                        "a calm editorial presentation mood, a spacious center reserved for future text, absolutely no visible text, "
                        "no logos, no icons, no labels, no UI fragments, no clutter, and no decorative elements intruding into the central reading area."
                    )
                    return {
                        "type": tpl_type,
                        "title": title,
                        "visual_description": "空白模板页背景，供用户后续叠加自定义内容。",
                        "final_visual_prompt": fallback_prompt,
                        "visual_prompt": fallback_prompt,
                        "reference_image": None,
                        "style_config": style_config,
                        "layout": layout,
                        "seed_role": "follow_up",
                        "seed_usage_rule": "模板页：保持整套 deck 的风格一致，但不得引入额外文本或抢占内容层级。",
                    }

            with ThreadPoolExecutor(max_workers=2) as executor:
                f1 = executor.submit(generate_template, "template_content", "空白内容模板", "centered_headline")
                f2 = executor.submit(generate_template, "template_split", "空白分栏模板", "left_text_right_visual")

                res1 = f1.result()
                if res1:
                    res1["page_num"] = len(visual_plan) + 1
                    visual_plan.append(res1)

                res2 = f2.result()
                if res2:
                    res2["page_num"] = len(visual_plan) + 1
                    visual_plan.append(res2)

        return visual_plan


# 向后兼容别名
VisualAgentFlash = VisualAgent
