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
from .style_library import get_curated_style, STYLE_LIBRARY

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# 问题3和问题7: Visual Prompt 约束模板
VISUAL_PROMPT_CONSTRAINTS = """
【页面布局规范 - 严格遵守】

### 绝对禁止
- 任何英文文字或字母
- 卡通人物、动漫角色
- 3D渲染效果
- 与内容无关的装饰元素

### 布局约束
- 标题区：顶部10-15%，居左或居中
- 内容区：中部60-70%
- 结论区：底部15-20%，结论文字必须最大最醒目

### 重复内容约束
- 标题文字只出现在标题位置，不出现在画面装饰中
- 每个关键信息只允许在一个位置出现
- 禁止在画面中重复核心信息（最多出现1次）

### 数据展示规范
- 数字超过3个时用卡片/列表，不用柱状图对比
- 避免排名展示（抖音>视频号>快手）
- 强调用红色，背景/次要用灰色
"""


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

    def __init__(self, api_key: str, api_base: str = None, prompt_mode: str = "verbose"):
        self.client = OpenAI(
            api_key=api_key,
            base_url=api_base or "https://generativelanguage.googleapis.com/v1beta/openai",
            timeout=120.0,
            max_retries=3
        )
        self.model = "MiniMax-M2.7"
        self.prompt_mode = prompt_mode  # "verbose" or "minimal"

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
            content = response.choices[0].message.content.strip()

            # 清理 <think> 标签（MiniMax 模型特有）
            content = re.sub(r'<think>.*?</think>', '', content, flags=re.DOTALL | re.IGNORECASE).strip()

            # 清理 markdown 代码块标记
            content = re.sub(r"^```(?:json)?\s*|```$", "", content, flags=re.MULTILINE|re.IGNORECASE).strip()

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

        prompt = f"""You are a world-class Art Director. Define a cohesive visual style guide for a presentation.

【Context】
- Topic: {topic}
- Audience: {audience}
- User Preference Vibe: "{user_preference}"
{brand_color_text}

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

            # 清理 <think> 标签（MiniMax 模型特有）
            content = re.sub(r'<think>.*?</think>', '', content, flags=re.DOTALL | re.IGNORECASE).strip()

            # 清理 markdown 代码块标记
            content = re.sub(r"^```(?:json)?\s*|```$", "", content, flags=re.MULTILINE|re.IGNORECASE).strip()

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

    def generate_visual_plan(self, narrative_outline: List[Dict], style_definition_tuple: tuple, assets: Dict, template_info: Dict = None) -> List[Dict]:
        """生成完整的视觉执行计划 (Visual Plan)"""
        logger.info("🎨 Visual Agent: 正在生成视觉执行计划...")

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
            f"- P{p['page_num']} ({p.get('type','content')}): {p.get('text_content', {}).get('headline', p.get('title', ''))} - {p.get('one_takeaway', p.get('core_message', ''))}" 
            for p in narrative_outline[:10]
        ])
        if len(narrative_outline) > 10:
            outline_summary += "\n... (more slides)"

        visual_plan = []
        prev_layout = None
        
        # 预先处理所有需要的提示词和变量，以便后续可以并行化
        tasks = []

        # Track which page types have been seen — first of each type is a potential seed page
        seen_types = set()

        for idx, page in enumerate(narrative_outline):
            page_type = page.get('type', 'content').lower()
            text_content = page.get('text_content', {})
            visual_suggestion = page.get('visual_suggestion', '')

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

            # Task 3: Handle table/chart pages (DataVisualizer)
            if layout_name in ('chart_from_table',):
                logger.info(f"📊 Visual Agent: Skipping prompt gen for data page (layout={layout_name})")
                plan_item = page.copy()
                plan_item['visual_prompt'] = "DATA_VISUALIZATION_PLACEHOLDER"
                plan_item['reference_image'] = reference_image_path
                plan_item['layout'] = layout_name
                plan_item['logo_path'] = assets.get('logo_path') or (template_info.get('logo_path') if template_info else None)
                plan_item['logo_location'] = template_info.get('logo_location', 'Top-Right') if template_info else 'Top-Right'
                plan_item['style_config'] = style_config
                plan_item['use_data_visualizer'] = True

                plan_item['chart_type'] = page.get('visualization', 'bar')

                tasks.append({'skip_llm': True, 'result': plan_item})
                continue

            # 3. Text rendering block — soft guidance, let the model decide hierarchy
            render_text_block = "TEXT CONTENT TO DISPLAY (render ONLY these, nothing else):\n"
            render_text_block += "(Design goal: the reader should instantly see what matters most on this slide. Use size, weight, and color differences from the palette to create natural visual hierarchy — you decide how.)\n\n"
            if text_content.get('headline'):
                render_text_block += f'Headline: "{text_content["headline"]}"\n'
            if text_content.get('subhead'):
                render_text_block += f'Subtitle: "{text_content["subhead"]}"\n'
            if text_content.get('body'):
                render_text_block += "Body:\n"
                for i, item in enumerate(text_content['body']):
                    item_clean = item.lstrip('-•* ').strip()
                    render_text_block += f'  {i+1}. "{item_clean}"\n'

            # 表格内容必须完整渲染
            # table_data 可能存在于 text_content 里，也可能直接在 page 根级别
            table_data = text_content.get('table_data') or page.get('table_data')
            if table_data:
                render_text_block += "\nTable Data (MUST be fully rendered with ALL rows and columns):\n"
                # 支持三种格式：
                # 1. {headers: [...], rows: [[...], [...]]} - 标准格式
                # 2. [{...}, {...}] - list of dicts
                # 3. [[...], [...]] - list of lists (第一行是表头)
                # 4. 字符串格式
                if isinstance(table_data, dict) and 'headers' in table_data and 'rows' in table_data:
                    # 标准格式 {headers: [...], rows: [[...], [...]]}
                    headers = table_data['headers']
                    render_text_block += "Columns: " + " | ".join(headers) + "\n"
                    for row_idx, row in enumerate(table_data['rows']):
                        row_str = " | ".join([str(cell) for cell in row])
                        render_text_block += f"Row {row_idx+1}: {row_str}\n"
                elif isinstance(table_data, list) and len(table_data) > 0:
                    if isinstance(table_data[0], dict):
                        # 列表 of dicts - 获取列名
                        headers = list(table_data[0].keys())
                        render_text_block += "Columns: " + " | ".join(headers) + "\n"
                        for row_idx, row in enumerate(table_data):
                            row_values = [str(row.get(h, '')) for h in headers]
                            render_text_block += f"Row {row_idx+1}: " + " | ".join(row_values) + "\n"
                    elif isinstance(table_data[0], list):
                        # 列表 of lists - 第一个是表头
                        for row_idx, row in enumerate(table_data):
                            row_str = " | ".join([str(cell) for cell in row])
                            prefix = "Header" if row_idx == 0 else f"Row {row_idx}"
                            render_text_block += f"{prefix}: {row_str}\n"
                elif isinstance(table_data, str):
                    render_text_block += table_data
                render_text_block += "[END TABLE]\n"
            
            # 4. Page Type & Native Image Instruction
            type_instruction = self._get_page_type_specific_instruction(page_type)

            # 4.5 Seed page vs follow-up page soft guidance
            CONTENT_FAMILY = {'content', 'framework', 'flowchart', 'comparison', 'data', 'toc', 'breathing', 'infographic'}
            type_family = 'content' if page_type in CONTENT_FAMILY else page_type
            is_seed_page = type_family not in seen_types
            seen_types.add(type_family)

            if is_seed_page:
                seed_guidance = (
                    "\n\n【SEED PAGE — Sets the visual tone for all similar pages】\n"
                    "This is the first page of its type. The typography and color choices you make here "
                    "will be used as a visual reference for all subsequent pages of the same type. "
                    "Pay special attention to creating clear visual hierarchy — the reader should instantly "
                    "distinguish headlines from body text through natural differences in size, weight, and color. "
                    "Make thoughtful use of the accent colors from the palette where it adds clarity."
                )
            else:
                seed_guidance = (
                    "\n\n【FOLLOW-UP PAGE — A reference image of a previous slide will be provided】\n"
                    "Match the overall visual language (colors, typography style, mood) of the reference image. "
                    "Focus your creative energy on the unique content and visual subject of THIS slide."
                )
            
            # Anti-hallucination constraint for native images
            native_images = page.get('native_images', [])
            has_blend = any(img.get('integration_mode') == 'blend' for img in native_images)
            has_overlay = any(img.get('integration_mode', 'overlay') == 'overlay' for img in native_images)
            
            native_image_constraint = ""
            if has_blend or has_overlay:
                native_image_constraint = "\n\n【Native Image & Anti-Hallucination Constraints (EXTREMELY CRITICAL)】\n"
                if has_blend:
                    native_image_constraint += "1. A reference photo will be provided to BLEND into this scene. Your prompt MUST explicitly state: 'seamlessly blend the provided reference subject into the background environment'.\n"
                    native_image_constraint += "2. DO NOT INVENT IRRELEVANT COMMERCIAL OBJECTS: The image generation model tends to hallucinate magazines, watches, advertisements, or product placements when given 'editorial' or 'premium' prompts. Your prompt MUST explicitly FORBID generating commercial products, brand items, or advertisements that are not described in the text content. However, contextually appropriate scene elements (people silhouettes, architecture, nature, atmospheric objects that serve the slide's metaphor) ARE allowed and encouraged for visual richness.\n"
                if has_overlay:
                    native_image_constraint += "3. A separate screenshot or graphic will be OVERLAID on top of the final image later. You MUST include an instruction to leave a massive, completely empty, clean safe zone (flat gradient or solid color, NO graphics, NO text, NO objects) for this overlay.\n"

            # 5. Build prompt
            system_prompt = (
                "You are an expert Prompt Engineer for Nano Banana 2 (Gemini Image). "
                "Your top priority is maintaining strict visual and typographic consistency across all generated slides. "
                "\n\nCRITICAL OUTPUT REQUIREMENTS:\n"
                "Your output MUST include TWO mandatory sections:\n"
                "1. TEXT TO RENDER section - List ALL text elements that must appear in the image, EXACTLY as provided in the user's TEXT CONTENT section. Do NOT omit, summarize, or paraphrase any text.\n"
                "2. VISUAL SCENE section - Describe the visual composition, layout, colors, textures, lighting, and styling.\n"
                "\n"
                "OUTPUT FORMAT: You must output EXACTLY one plain-text string with clear section markers. "
                "Use simple section headers like '【TEXT TO RENDER】' and '【VISUAL SCENE】' to separate the sections. "
                "DO NOT use markdown formatting: no asterisks, no hashes, no backticks, no bullet markers, no bold, no italic, no code blocks."
            )

            if template_info:
                prompt_mode = f"""【Mode: STYLE CLONING & TEMPLATE SAFE ZONES】
- Match the COLOR PALETTE, FONTS, and VISUAL TONE of the reference image.
- Since a template is being used, generate graphics that act as a thematic backdrop or localized illustration.
- STRICTLY leave vast empty negative space where template text/content resides.
- Blend the edges of any generated illustration into the background color.
- Do not generate full-bleed chaotic graphics that overlap text.
- Assigned layout for this page: [{layout_name}] — {layout_desc}"""
            else:
                prompt_mode = f"""【Mode: AI MINTING】
- Create a cohesive, professional slide matching the Global Style.
- Assigned layout for this page: [{layout_name}] — {layout_desc}
- VISUAL RICHNESS: Use figurative, concrete visual metaphors (landscapes, architecture, human silhouettes, natural phenomena, meaningful objects) rather than defaulting to abstract geometric shapes. The visual subject should directly serve the slide's specific message."""

            manifesto_ban = "\n- ENFORCE MANIFESTO BANS: Avoid the specific clichéd elements listed in 'Cliche Avoidance' (e.g., glowing brains, 3D funnels). Note: this does NOT ban people, architecture, nature, or real-world objects — those are encouraged for visual richness." if manifesto else ""

            # Warning for empty visual_suggestion
            vb_empty_warning = (
                "\n[WARNING: This slide's User-Confirmed Visual Description is EMPTY. "
                "Generate a suitable visual that matches the page's semantic content and type, "
                "using the headline, body, and one_takeaway as your guide. "
                "Do NOT leave the visual field blank or generic.]"
                if not visual_suggestion.strip() else ""
            )

            if self.prompt_mode == "minimal":
                # Minimal mode: only essential constraints
                neg_constraints = f"""【Key Guidelines】
- Do not render logos or brand marks.
- Render text exactly as provided in the TEXT CONTENT section.
- Use full-bleed composition.{manifesto_ban}"""
            else:
                # Verbose mode: detailed negative constraints
                neg_constraints = f"""【Negative Constraints (CRITICAL)】
- Do NOT render any LOGO or brand mark anywhere.
- ONLY use bullet points or list markers (like '•') when explicitly formatting a list of multiple small points. Do not use them for diagrams, frameworks, or standalone blocks.
- NO black blocks, NO solid black rectangles, NO empty black corners. Use seamless full-bleed composition extending to all edges.
- The reference image contains TEMPLATE PLACEHOLDER labels such as "标题", "内容", "小标题", "副标题", "单击此处编辑". These are NOT real content. You MUST NOT reproduce ANY of them.
- Do NOT reproduce ANY text visible in the reference image that is not listed in the TEXT CONTENT section below.
- Do NOT translate any Chinese text. Render it exactly as provided.
- Do NOT add decorative text, watermarks, or labels not in the TEXT CONTENT section.
- Do NOT repeat the exact same text multiple times. If the text content has two bullet points, do NOT render them four times. Avoid hallucinating duplicate text blocks.
- Do NOT use random, inconsistent fonts. Typography MUST strictly adhere to the defined font families and weights in the Global Style.
- TABLE RENDERING (CRITICAL): If a table is present in the TEXT CONTENT section, you MUST render the COMPLETE table with ALL rows and ALL columns. Do NOT summarize, truncate, or omit any row or column. Each cell's text must be clearly legible. The table should occupy a significant portion of the slide layout.{manifesto_ban}"""

            if self.prompt_mode == "minimal":
                # Minimal mode: simplified prompt structure
                user_prompt = f"""Generate an image generation prompt for a PPT slide.

【MANDATORY TEXT CONTENT — MUST RENDER EXACTLY】
The following text MUST appear in the generated image. Do NOT omit, summarize, or paraphrase.
Include this section in your output as '【TEXT TO RENDER】' with all text listed below:

{render_text_block}

【VISUAL SCENE DESCRIPTION】
{design_system}

{prompt_mode}
{seed_guidance}

【Current Slide (USER-CONFIRMED — STRICTLY FOLLOW)】
- Page Type: {page_type.upper()}
- User-Confirmed Visual: {visual_suggestion if visual_suggestion.strip() else "(empty — generate matching visual)"}
- Layout: {layout_name}

{neg_constraints}

【Output Format】
Your output MUST follow this structure:

【TEXT TO RENDER】
(List ALL text elements from the MANDATORY TEXT CONTENT section above, exactly as provided)

【VISUAL SCENE】
(Describe the visual composition, colors, textures, lighting, and styling that will bring the User-Confirmed Visual to life)

CRITICAL: Output as plain text with section markers. No markdown formatting."""
            else:
                # Verbose mode: detailed prompt structure
                user_prompt = f"""Generate a high-fidelity image generation prompt for a PPT slide.

【MANDATORY TEXT CONTENT — MUST RENDER EXACTLY】
The following text MUST appear in the generated image. Do NOT omit, summarize, or paraphrase.
Include this section in your output as '【TEXT TO RENDER】' with all text listed below:

{render_text_block}

【VISUAL SCENE DESCRIPTION】
{design_system}

{prompt_mode}
- Reference Image: Using '{os.path.basename(reference_image_path) if reference_image_path else "None"}' as style anchor.
{seed_guidance}

【Global Context (For Consistency)】
{outline_summary}

【CURRENT PAGE TARGET (USER-CONFIRMED — STRICTLY FOLLOW)】
- Section: {page.get('section_title', 'General')}
- Page Type: {page_type.upper()}
- User-Confirmed Visual Description: {visual_suggestion}

【VISUAL DESCRIPTION CONSTRAINT (CRITICAL — NON-NEGOTIABLE)】
The "User-Confirmed Visual Description" above is the EXACT visual the user has approved for this slide. You MUST follow it precisely and preserve ALL key details. Your job is to:
1. Preserve EVERY specific detail mentioned in the Visual Description (objects, actions, textures, compositions, emotional cues)
2. Apply the Global Style (colors, fonts, lighting, texture) to render this exact scene
3. Adapt the layout/placement only to fit the text content
4. NEVER substitute a different visual metaphor or generalize specific details into vague descriptions
5. If the Visual Description mentions specific text to be handwritten or displayed (e.g., "便签上用铅笔手写'胃肠溃疡哪家医院更好？'"), you MUST include that exact text in your TEXT TO RENDER section
{vb_empty_warning if not visual_suggestion.strip() else ""}

【VISUAL DIVERSITY RULE (CRITICAL)】
5. Each slide MUST feature a visually DISTINCT primary subject. Do NOT reuse the same visual motif (e.g., stone monolith, glass panel, abstract cube) across consecutive slides.
6. PREFER figurative, concrete imagery over abstract geometric shapes: human silhouettes in dramatic lighting, architectural elements (ruins, bridges, towers, corridors), natural landscapes (oceans, mountains, deserts, forests, storms), meaningful real-world objects (compass, hourglass, telescope, flame), aerial or cinematic perspectives.
7. Abstract geometric forms (monoliths, cubes, spheres, glass planes) should appear on NO MORE than 20% of slides in the deck. They are acceptable occasionally for breathing/transition pages but must not be the default.
8. If the Visual Diversity Strategy in the Manifesto lists specific motif categories, you MUST rotate through them across slides.
{native_image_constraint}

【Instruction】
1. {type_instruction}
2. Describe the visual scene in detail, preserving ALL specific elements from the User-Confirmed Visual Description.
3. Plan text placement organically based on the meaning of the content.

{neg_constraints}

【Output Format】
Your output MUST follow this structure:

【TEXT TO RENDER】
(List ALL text elements from the MANDATORY TEXT CONTENT section above, exactly as provided. Also include any text mentioned in the Visual Description that should be handwritten or displayed in the scene.)

【VISUAL SCENE】
(Describe the complete visual composition: layout, objects, actions, colors, textures, lighting, mood. Preserve ALL specific details from the User-Confirmed Visual Description. Do NOT generalize or simplify.)

CRITICAL: Output as plain text with section markers. No markdown formatting (no bold, no italic, no bullet markers, no headings, no code blocks)."""

            tasks.append({
                'skip_llm': False,
                'page': page,
                'layout_name': layout_name,
                'reference_image_path': reference_image_path,
                'system_prompt': system_prompt,
                'user_prompt': user_prompt
            })

        # 并发执行所有 LLM 调用
        from concurrent.futures import ThreadPoolExecutor, as_completed
        logger.info(f"🎨 Visual Agent: 正在并行生成 {len([t for t in tasks if not t['skip_llm']])} 页的视觉提示词...")

        def generate_single_prompt(idx, task):
            if task.get('skip_llm'):
                return idx, task['result']
            
            page = task['page']
            try:
                response = chat_completion_with_fallback(
                    self.client, model=self.model, model_fallback=MODEL_FALLBACK_CHAIN,
                    messages=[
                        {"role": "system", "content": task['system_prompt']},
                        {"role": "user", "content": task['user_prompt']}
                    ],
                    temperature=0.7
                )
                final_prompt = response.choices[0].message.content.strip()

                # 清理 <think> 思考过程标签（MiniMax 模型特有）
                final_prompt = re.sub(r'<think>.*?</think>', '', final_prompt, flags=re.DOTALL | re.IGNORECASE).strip()

                # 输出验证：检查并清理禁止的格式标记
                forbidden_patterns = [
                    (r'```', 'markdown code block'),
                    (r'\*\*[^*]+\*\*', 'markdown bold'),
                    (r'\*[^*]+\*', 'markdown italic'),
                    (r'^[-•*]\s', 'bullet marker at line start'),
                    (r'#{1,6}\s', 'markdown heading'),
                ]
                cleaned_prompt = final_prompt
                for pattern, desc in forbidden_patterns:
                    if re.search(pattern, cleaned_prompt, re.MULTILINE):
                        cleaned_prompt = re.sub(pattern, '', cleaned_prompt, flags=re.MULTILINE)
                        logger.warning(f"⚠️ P{page.get('page_num')} 已清理禁止格式 ({desc})，已自动修复")

                # 清理多余空行
                cleaned_prompt = re.sub(r'\n{3,}', '\n\n', cleaned_prompt)
                final_prompt = cleaned_prompt.strip()

                # 验证输出格式：检查是否包含必要的 TEXT TO RENDER 部分
                text_content = page.get('text_content', {})
                headline = text_content.get('headline', '')
                body = text_content.get('body', [])

                # 检查标题是否在输出中
                missing_text = []
                if headline and headline not in final_prompt:
                    missing_text.append(f'Headline: "{headline}"')

                # 检查正文关键内容是否在输出中
                for item in body[:2]:  # 只检查前2条，避免过度严格
                    item_clean = item.lstrip('-•* ').strip()
                    if item_clean and len(item_clean) > 10 and item_clean not in final_prompt:
                        # 只检查较长的内容项，避免误报
                        missing_text.append(f'Body: "{item_clean[:50]}..."')

                # 如果缺失关键文字内容，进行补充
                if missing_text:
                    logger.warning(f"⚠️ P{page.get('page_num')} 输出缺失文字内容，正在补充...")

                    # 构建补充的 TEXT TO RENDER 部分
                    text_to_render = "\n\n【TEXT TO RENDER】\n"
                    if headline:
                        text_to_render += f'Headline: "{headline}"\n'
                    if text_content.get('subhead'):
                        text_to_render += f'Subtitle: "{text_content["subhead"]}"\n'
                    if body:
                        text_to_render += "Body:\n"
                        for i, item in enumerate(body):
                            item_clean = item.lstrip('-•* ').strip()
                            text_to_render += f'  {i+1}. "{item_clean}"\n'

                    # 如果输出中已经有 TEXT TO RENDER 标记，替换它；否则在开头添加
                    if '【TEXT TO RENDER】' in final_prompt or 'TEXT TO RENDER' in final_prompt:
                        # 替换现有的 TEXT TO RENDER 部分
                        final_prompt = re.sub(
                            r'【?TEXT TO RENDER】?.*?(?=【|$)',
                            text_to_render,
                            final_prompt,
                            flags=re.DOTALL
                        )
                    else:
                        # 在开头添加 TEXT TO RENDER 部分
                        final_prompt = text_to_render + "\n" + final_prompt
                plan_item = page.copy()
                plan_item['visual_prompt'] = final_prompt
                plan_item['reference_image'] = task['reference_image_path']
                plan_item['layout'] = task['layout_name']
                plan_item['logo_path'] = assets.get('logo_path') or (template_info.get('logo_path') if template_info else None)
                plan_item['logo_location'] = template_info.get('logo_location', 'Top-Right') if template_info else 'Top-Right'
                plan_item['style_config'] = style_config

                return idx, plan_item

            except Exception as e:
                logger.error(f"Prompt生成失败 (Page {page.get('page_num')}): {e}")
                # fallback item
                plan_item = page.copy()
                plan_item['visual_prompt'] = "A professional slide background."
                plan_item['layout'] = task['layout_name']
                plan_item['style_config'] = style_config
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
                        "visual_prompt": clean_prompt,
                        "reference_image": None,
                        "style_config": style_config,
                        "layout": layout
                    }
                except Exception as e:
                    logger.error(f"模板页生成失败: {e}")
                    return None

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
