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
        "wide_quote_card": "Wide Quote Card. 1/3 of the space for a realistic portrait with a subtle gradient transition, 2/3 for a massive quotation text with an oversized faint quotation mark in the background."
    }

    def __init__(self, api_key: str, api_base: str = None):
        self.client = OpenAI(
            api_key=api_key,
            base_url=api_base or "https://generativelanguage.googleapis.com/v1beta/openai",
            timeout=120.0,
            max_retries=3
        )
        self.model = "gemini-3.1-pro-preview"

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
        
        # 检查是否命中系统内置风格库 (Curated Style Library)
        curated_style = get_curated_style(user_preference)
        if curated_style:
            logger.info(f"✨ 命中系统内置风格库: {user_preference} -> {curated_style['description'][:50]}...")
            style_desc_str = f"Style: {curated_style.get('description')}. Palette: {', '.join(curated_style.get('palette', []))}."
            style_config = curated_style.copy()
            if "aliases" in style_config:
                del style_config["aliases"]
            style_config['mode'] = 'ai_minting_curated'
            return style_desc_str, style_config

        topic = constraints.get('presentation_type', 'Business Presentation')
        audience = constraints.get('target_audience', 'General Professional')

        prompt = f"""You are a world-class Art Director. Define a cohesive visual style guide for a presentation.

【Context】
- Topic: {topic}
- Audience: {audience}
- User Preference Vibe: "{user_preference}"

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
            if content.startswith('```json'): content = content[7:]
            if content.endswith('```'): content = content[:-3]

            style_data = json.loads(content)

            style_desc_str = f"Style: {style_data.get('description')}. Palette: {', '.join(style_data.get('palette', []))}."
            style_config = style_data
            style_config['mode'] = 'ai_minting'

            return style_desc_str, style_config

        except Exception as e:
            logger.error(f"风格定义失败: {e}")
            fallback_desc = "Modern Professional Business style, clean #F5F5F7 background, #333333 text, minimalistic and high-end."
            return fallback_desc, {"mode": "fallback", "description": fallback_desc, "palette": ["#F5F5F7", "#333333"]}

    # ── Content-aware layout assignment ──

    @staticmethod
    def _assign_layout(page_type: str, text_content: dict, prev_layout: str = None, page: dict = None) -> tuple:
        """Pick a layout based on content characteristics, avoiding consecutive duplicates."""
        body = text_content.get('body', [])

        # Check for table/chart data
        if page:
            table_data = page.get('text_content', {}).get('table_data') or page.get('table_data')
            visualization = page.get('visualization', '')
            if table_data:
                if visualization in ('bar', 'line', 'pie'):
                    return 'chart_from_table', "Data visualization chart (bar/line/pie) derived from table data."
                return 'content', VisualAgent.LAYOUT_LIBRARY['content']

        if page_type == 'cover':
            return 'full_screen_immersive', VisualAgent.LAYOUT_LIBRARY['full_screen_immersive']
        elif page_type in ('back', 'ending'):
            return 'centered_headline', VisualAgent.LAYOUT_LIBRARY['centered_headline']
        elif page_type == 'section':
            return 'minimalist_hero', VisualAgent.LAYOUT_LIBRARY['minimalist_hero']
        elif page_type == 'hero':
            return 'minimalist_hero', VisualAgent.LAYOUT_LIBRARY['minimalist_hero']
        elif page_type == 'quote':
            return 'wide_quote_card', VisualAgent.LAYOUT_LIBRARY['wide_quote_card']
        elif page_type == 'infographic':
            return 'dense_infographic', VisualAgent.LAYOUT_LIBRARY['dense_infographic']
        elif page_type == 'toc':
            return 'three_column_grid', VisualAgent.LAYOUT_LIBRARY['three_column_grid']
        elif page_type == 'data':
            return 'big_number_data', VisualAgent.LAYOUT_LIBRARY['big_number_data']
            
        # 2. Content page adaptation
        elif len(body) == 0:
            pick = 'centered_headline'
        elif any(kw in ''.join(body) for kw in ['步', '第一', '第二', '阶段', 'Step', '->', '→']):
            pick = 'process_flow'
        elif len(body) >= 4 and all(len(b) < 30 for b in body):
            pick = 'bento_grid'
        elif len(body) == 3 and all(len(b) < 100 for b in body):
            pick = 'three_column_grid'
        elif len(body) <= 2:
            pick = 'left_text_right_visual'
        else:
            pick = 'top_visual_bottom_text'

        # Avoid duplicates for content pages
        if pick == prev_layout and page_type == 'content':
            for alt in ['left_text_right_visual', 'top_visual_bottom_text', 'three_column_grid']:
                if alt != prev_layout:
                    pick = alt
                    break

        return pick, VisualAgent.LAYOUT_LIBRARY.get(pick, "Standard Layout")

    def _get_page_type_specific_instruction(self, page_type: str) -> str:
        """根据页面类型生成特定的设计指令"""
        instructions = {
            "cover": "【COVER DESIGN】Max visual impact. Title must be MASSIVE and center/left aligned. Use a symbolic, high-end 3D object or cinematic scene as the main visual anchor. Keep negative space for the title.",
            "section": "【SECTION TRANSITION】Minimalist and bold. Use a solid color or abstract texture background. The Section Title should be the only focus. Create a sense of 'pause' or 'new chapter'.",
            "hero": "【HERO / GOLDEN SENTENCE】Impact over detail. Use massive typography for the core message. Typography (Font, Weight, Positioning) MUST match the reference/style exactly. However, the Background Visual should be unique and relevant to the specific content (e.g. specific metaphor or scene).",
            "quote": "【QUOTE CARD】High impact quotation. Usually split into portrait (1/3) and text (2/3). The quote text must be large and prominent. Use a faint large quotation mark in the background.",
            "toc": "【TABLE OF CONTENTS】Structured and clean. Use a grid or list layout. Use icons or large numbers for each chapter. High legibility is key.",
            "content": "【CONTENT SLIDE】Structured information. Use Bento grids or clean dividers to organize text. Ensure body text is legible (min 24pt equivalent). Balance text with a relevant visual on the side or top.",
            "data": "【DATA VISUALIZATION】Focus on the chart/number. If there is a big number, make it huge. If there is a chart description, visualize it as a sleek, modern chart (bar/line/pie) integrated into the scene.",
            "infographic": "【INFOGRAPHIC / HIGH DENSITY】Modular and structured layout. Use a Bento Grid or central hub connector design. Organize complex information into clear, distinct sections (cards/glass panes). Use icons and visual hierarchy to manage high information density while keeping it clean and professional.",
            "ending": "【ENDING / BACK COVER】Simple and memorable. usually 'Thank You' or contact info. Clean background, centered text."
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
        if len(palette) >= 3:
            accents = ", ".join(palette[2:])
            color_constraint = (
                f"Background base MUST BE strictly {palette[0]} (Never use {palette[1]} for background). "
                f"All main text (Headlines and Body) MUST BE {palette[1]} to ensure high contrast and readability. "
                f"Use {accents} strictly for accents, highlights, shapes, or small decorative elements ONLY."
            )
        elif palette:
            color_constraint = f"Palette: {', '.join(palette)}. Primary Background MUST BE {palette[0]}, Primary Text MUST BE {palette[1]}."
        else:
            color_constraint = ""

        font_constraint = ""
        if style_config.get('fonts'):
            fonts_str = ', '.join(style_config['fonts'])
            font_constraint = f"\n4. **Typography (STRICTLY ENFORCED)**: You MUST use these exact fonts on EVERY single slide: {fonts_str}. Headings must ALWAYS use the heading font, and body text must ALWAYS use the body font. Never change font families between slides. NEVER use random or generic fonts."

        # 4. Design system
        design_system = f"""【Visual Design System (STRICT)】
1. **Global Style**: {style_definition}
2. **Color Palette (MANDATORY)**: {color_constraint}
3. **Consistency**: ALL slides must use the exact same fonts, colors, and decorative elements.{font_constraint}"""

        # 5. Global Context Injection (Summary of the whole deck)
        # Create a condensed outline string
        outline_summary = "\n".join([f"- P{p['page_num']} ({p.get('type','content')}): {p.get('title','')} - {p.get('core_message','')}" for p in narrative_outline[:10]])
        if len(narrative_outline) > 10:
            outline_summary += "\n... (more slides)"

        visual_plan = []
        prev_layout = None

        for page in narrative_outline:
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

                visual_plan.append(plan_item)
                continue

            # 3. Text rendering block
            render_text_block = "**TEXT CONTENT TO DISPLAY (render ONLY these, nothing else):**\n\n"
            if text_content.get('headline'):
                render_text_block += f'Headline: "{text_content["headline"]}"\n'
            if text_content.get('subhead'):
                render_text_block += f'Subtitle: "{text_content["subhead"]}"\n'
            if page_type == 'content' and text_content.get('body'):
                render_text_block += "Body Points (render EXACTLY the text inside quotes):\n"
                for i, item in enumerate(text_content['body']):
                    item_clean = item.lstrip('-•* ').strip()
                    render_text_block += f'Text {i+1}: "{item_clean}"\n'
            
            # 4. Page Type Instruction
            type_instruction = self._get_page_type_specific_instruction(page_type)

            # 5. Build prompt
            system_prompt = "You are an expert Prompt Engineer for Nano Banana 2 (Gemini Image). Your top priority is maintaining strict visual and typographic consistency across all generated slides."

            if template_info:
                prompt_mode = f"""【Mode: STYLE CLONING】
- Match the COLOR PALETTE, FONTS, and VISUAL TONE of the reference image.
- You have FREEDOM to choose the best LAYOUT for the content below.
- Assigned layout for this page: **{layout_name}** — {layout_desc}"""
            else:
                prompt_mode = f"""【Mode: AI MINTING】
- Create a cohesive, professional slide matching the Global Style.
- Assigned layout for this page: **{layout_name}** — {layout_desc}"""

            neg_constraints = """【Negative Constraints (CRITICAL)】
- Do NOT render any LOGO or brand mark anywhere.
- ONLY use bullet points or list markers (like '•') when explicitly formatting a list of multiple small points. Do not use them for diagrams, frameworks, or standalone blocks.
- NO black blocks, NO solid black rectangles, NO empty black corners. Use seamless full-bleed composition extending to all edges.
- The reference image contains TEMPLATE PLACEHOLDER labels such as "标题", "内容", "小标题", "副标题", "单击此处编辑". These are NOT real content. You MUST NOT reproduce ANY of them.
- Do NOT reproduce ANY text visible in the reference image that is not listed in the TEXT CONTENT section below.
- Do NOT translate any Chinese text. Render it exactly as provided.
- Do NOT add decorative text, watermarks, or labels not in the TEXT CONTENT section.
- Do NOT use random, inconsistent fonts. Typography MUST strictly adhere to the defined font families and weights in the Global Style."""

            user_prompt = f"""Generate a high-fidelity image generation prompt for a PPT slide.

{design_system}

{prompt_mode}
- **Reference Image**: Using '{os.path.basename(reference_image_path) if reference_image_path else "None"}' as style anchor.

【Global Context (For Consistency)】
{outline_summary}

【CURRENT PAGE TARGET】
- Section: {page.get('section_title', 'General')}
- Page Type: {page_type.upper()}
- Initial Visual Suggestion: {visual_suggestion}

【STYLE ADAPTATION RULE (CRITICAL)】
The "Initial Visual Suggestion" above describes the desired metaphor or object. 
You MUST ADAPT the subject matter/metaphor from the Initial Visual Suggestion so that it is rendered STRICTLY in the exact aesthetic of the Global Style and Color Palette. 
For example, if the Suggestion says "a bright sunny corporate office" but the Global Style is "Cyberpunk Dark Neon", you MUST generate "a cyberpunk dark neon corporate office with glowing accents". 
The Global Style ALWAYS OVERRIDES the stylistic implications of the Initial Visual Suggestion.

【Instruction】
1. **{type_instruction}**
2. Describe the visual scene in detail (background, shapes, decorative elements).
3. Plan text placement according to the assigned layout.

{render_text_block}

{neg_constraints}

【Output】
Directly output the final image-generation Prompt string. No explanation."""

            try:
                response = chat_completion_with_fallback(
                    self.client, model=self.model, model_fallback=MODEL_FALLBACK_CHAIN,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt}
                    ],
                    temperature=0.7
                )
                final_prompt = response.choices[0].message.content.strip()

                plan_item = page.copy()
                plan_item['visual_prompt'] = final_prompt
                plan_item['reference_image'] = reference_image_path
                plan_item['layout'] = layout_name
                plan_item['logo_path'] = assets.get('logo_path') or (template_info.get('logo_path') if template_info else None)
                plan_item['logo_location'] = template_info.get('logo_location', 'Top-Right') if template_info else 'Top-Right'
                plan_item['style_config'] = style_config

                visual_plan.append(plan_item)

            except Exception as e:
                logger.error(f"Prompt生成失败 (Page {page.get('page_num')}): {e}")

        # Bonus: generate blank template slides
        if visual_plan:
            logger.info("➕ 追加模板页 (Blank Template Slides)...")
            
            # Template 1: Standard Content Layout
            tpl1_prompt = f"""Generate a blank presentation template slide.
            
{design_system}

【Instruction】
- Create a highly structured, professional blank slide for content.
- Include a distinct, subtle decorative area for the slide Title (e.g., a subtle header bar, a faint border, or a designated glowing area).
- Leave the main body area clean and spacious for the user to add their own text or images later.
- CRITICAL: NO ACTUAL TEXT, NO LOGOS, NO ICONS in the layout. Only abstract structural elements, frames, and background textures matching the Global Style.

【Output】
Directly output the final Prompt string."""

            # Template 2: Split / Double Column Layout
            tpl2_prompt = f"""Generate a blank presentation template slide with a split layout.
            
{design_system}

【Instruction】
- Create a highly structured, professional blank slide designed for a two-column or split layout.
- For example, left side has a subtle card/glass pane for text, right side is open for an image; or a 50/50 split with subtle divider lines.
- Include a distinct, subtle decorative area for the slide Title.
- CRITICAL: NO ACTUAL TEXT, NO LOGOS, NO ICONS in the layout. Only abstract structural elements, dividers, frames, and background textures matching the Global Style.

【Output】
Directly output the final Prompt string."""

            try:
                # Generate Template 1
                resp1 = chat_completion_with_fallback(
                    self.client, model=self.model, model_fallback=MODEL_FALLBACK_CHAIN,
                    messages=[
                        {"role": "system", "content": "You are a UI/UX designer specializing in presentation templates."},
                        {"role": "user", "content": tpl1_prompt}
                    ],
                    temperature=0.7
                )
                visual_plan.append({
                    "page_num": len(visual_plan) + 1,
                    "type": "template_content",
                    "title": "空白内容模板",
                    "visual_prompt": resp1.choices[0].message.content.strip(),
                    "reference_image": None,
                    "style_config": style_config,
                    "layout": "centered_headline" # will be used for placeholder insertion
                })
                
                # Generate Template 2
                resp2 = chat_completion_with_fallback(
                    self.client, model=self.model, model_fallback=MODEL_FALLBACK_CHAIN,
                    messages=[
                        {"role": "system", "content": "You are a UI/UX designer specializing in presentation templates."},
                        {"role": "user", "content": tpl2_prompt}
                    ],
                    temperature=0.7
                )
                visual_plan.append({
                    "page_num": len(visual_plan) + 1,
                    "type": "template_split",
                    "title": "空白分栏模板",
                    "visual_prompt": resp2.choices[0].message.content.strip(),
                    "reference_image": None,
                    "style_config": style_config,
                    "layout": "left_text_right_visual" # will be used for placeholder insertion
                })
            except Exception as e:
                logger.error(f"模板页生成失败: {e}")

        return visual_plan
