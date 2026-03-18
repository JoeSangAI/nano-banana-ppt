import json
import logging
import re
from typing import List, Dict, Union
from .visual import VisualAgent
from tools.nano_banana_ppt.utils.llm_client import chat_completion_with_fallback, MODEL_FALLBACK_CHAIN

logger = logging.getLogger(__name__)

class VisualAgentFlash(VisualAgent):
    """
    Flash 版本的 Visual Agent。
    特点：
    1. 继承原 VisualAgent 的所有规则和工具（Layout Library, Type Instruction）。
    2. 覆盖 `generate_visual_plan`，使用 Batch + Flash 的逻辑，极大降低 Token 成本和生成时间。
    """
    def __init__(self, api_key: str, api_base: str = None):
        super().__init__(api_key, api_base)
        # 强制降级到 Flash 模型
        self.model = "gemini-3.1-flash"
        
    def generate_visual_plan(self, narrative_outline: List[Dict], style_definition_tuple: tuple, assets: Dict, template_info: Dict = None) -> List[Dict]:
        logger.info("⚡ Visual Agent Flash: 正在批量生成视觉执行计划 (Batch Mode)...")

        if isinstance(style_definition_tuple, tuple):
            style_definition, style_config = style_definition_tuple
        else:
            style_definition = str(style_definition_tuple)
            style_config = {}

        # 1. 提取全局颜色限制
        palette = style_config.get('palette', [])
        color_constraint = f"Palette: {', '.join(palette)}." if palette else ""
        font_constraint = f"\n- Fonts: {', '.join(style_config.get('fonts', []))}." if style_config.get('fonts') else ""
        manifesto = style_config.get('manifesto', '')
        if manifesto:
            manifesto_block = f"\n- **Design System Manifesto (Art Director)**:\n{manifesto}\n\nSTRICT INSTRUCTION: You MUST follow the 'Visual Motif' and 'Shape Language' exactly. DO NOT invent your own semantic metaphors for the slides. Adhere to the 'Cliche Avoidance' list strictly."
        else:
            manifesto_block = ""
        
        color_constraint_block = f"\n- {color_constraint}" if color_constraint else ""

        design_system = f"""【Visual Design System (STRICT)】
- Global Style: {style_definition}{color_constraint_block}{font_constraint}{manifesto_block}

ALL slides MUST use exactly these colors and style."""

        # 2. 数据分块 (Chunking) - 避免超过输出长度，每批最多处理 15 页
        CHUNK_SIZE = 15
        visual_plan = []
        prev_layout = None
        
        for i in range(0, len(narrative_outline), CHUNK_SIZE):
            chunk = narrative_outline[i:i + CHUNK_SIZE]
            
            # 准备发送给模型的数据（剔除冗余字段，减小输入 Token）
            chunk_request_data = []
            for page in chunk:
                page_type = page.get('type', 'content').lower()
                text_content = page.get('text_content', {})
                
                # Assign Layout (复用父类逻辑)
                layout_name, layout_desc = self._assign_layout(page_type, text_content, prev_layout, page)
                prev_layout = layout_name
                
                page_data = {
                    "page_num": page.get('page_num'),
                    "type": page_type,
                    "assigned_layout": layout_name,
                    "layout_description": layout_desc,
                    "text_headline": text_content.get('headline', ''),
                    "text_subhead": text_content.get('subhead', ''),
                    "text_body": text_content.get('body', []),
                    "visual_suggestion": page.get('visual_suggestion', '')
                }
                
                # Check for table
                table_data = page.get('text_content', {}).get('table_data') or page.get('table_data')
                if table_data and page.get('visualization', '') in ('bar', 'line', 'pie'):
                     page_data['skip_prompt_generation'] = True
                     page_data['chart_type'] = page.get('visualization')
                
                # Store full page temporarily in request data for later reconstruction
                page_data['_original_page'] = page
                chunk_request_data.append(page_data)

            template_instruction = ""
            if template_info:
                template_instruction = """
【Mode: STYLE CLONING & TEMPLATE SAFE ZONES】
- Match the COLOR PALETTE, FONTS, and VISUAL TONE of the reference image.
- Since a template is being used, generate graphics that act as a thematic backdrop or localized illustration. 
- STRICTLY leave vast empty negative space where template text/content resides. 
- Blend the edges of any generated illustration into the background color. 
- Do not generate full-bleed chaotic graphics that overlap text.
"""

            # 3. 构建批量 Prompt
            manifesto_ban = "\n- ENFORCE MANIFESTO BANS: Absolutely NO elements from the 'Cliche Avoidance' list." if manifesto else ""
            
            batch_prompt = f"""You are an expert Prompt Engineer for image generation models.
Your task is to generate {len(chunk_request_data)} image generation prompts simultaneously.

{design_system}
{template_instruction}
【Task】
For each slide provided in the JSON array below, generate a highly detailed image generation prompt.
Adapt the "visual_suggestion" into the Global Style.
CRITICAL: 
- DO NOT generate logos or watermarks.
- DO NOT include exact Chinese text in the prompt unless necessary, describe the layout.
- NO black blocks, full bleed composition.{manifesto_ban}

【Input Data】
{json.dumps([{k: v for k, v in p.items() if k != '_original_page'} for p in chunk_request_data], ensure_ascii=False, indent=2)}

【Output Format】
You MUST output a valid JSON array matching the exact order and length of the input.
Format:
[
  {{
    "page_num": 1,
    "layout": "chosen_layout_name",
    "visual_prompt": "A detailed description of the slide background, shapes, and layout..."
  }},
  ...
]
"""
            try:
                logger.info(f"  正在请求 Flash 模型生成第 {i+1} - {min(i+CHUNK_SIZE, len(narrative_outline))} 页的 Prompts...")
                response = chat_completion_with_fallback(
                    self.client, model=self.model, model_fallback=["gemini-2.5-flash"],
                    messages=[
                        {"role": "system", "content": "You output only valid JSON arrays."},
                        {"role": "user", "content": batch_prompt}
                    ],
                    temperature=0.5
                )
                
                content = response.choices[0].message.content.strip()
                content = re.sub(r"^```(?:json)?\s*|```$", "", content, flags=re.MULTILINE|re.IGNORECASE).strip()
                
                batch_results = json.loads(content)
                
                if len(batch_results) != len(chunk_request_data):
                    raise ValueError(f"Length mismatch: LLM returned {len(batch_results)} prompts, expected {len(chunk_request_data)}.")
                
                # 组合结果
                for req_item, res_item in zip(chunk_request_data, batch_results):
                    original_page = req_item['_original_page'].copy()
                    
                    if req_item.get('skip_prompt_generation'):
                        original_page['visual_prompt'] = "DATA_VISUALIZATION_PLACEHOLDER"
                        original_page['use_data_visualizer'] = True
                        original_page['chart_type'] = req_item['chart_type']
                    else:
                        original_page['visual_prompt'] = res_item.get('visual_prompt', f"Fallback prompt for page {req_item['page_num']}")
                        
                    original_page['layout'] = req_item['assigned_layout']
                    original_page['style_config'] = style_config
                    
                    # 补充缺失字段
                    refs = template_info.get('reference_images', {}) if template_info else {}
                    original_page['reference_image'] = refs.get('ref_content') # Simplified for Flash
                    original_page['logo_path'] = assets.get('logo_path') or (template_info.get('logo_path') if template_info else None)
                    original_page['logo_location'] = template_info.get('logo_location', 'Top-Right') if template_info else 'Top-Right'
                    
                    visual_plan.append(original_page)
                    
            except Exception as e:
                logger.error(f"批量生成 Prompt 失败 (Chunk {i}): {e}")
                # 失败降级：给空 Prompt 避免崩溃
                for req_item in chunk_request_data:
                    original_page = req_item['_original_page'].copy()
                    original_page['visual_prompt'] = f"A simple background for {original_page.get('type')} page."
                    original_page['layout'] = req_item['assigned_layout']
                    original_page['style_config'] = style_config
                    visual_plan.append(original_page)

        # 4. 追加空白模板页 (复用 Pro 的逻辑，或者简化)
        is_pptx_template = template_info and template_info.get("source_type") == "pptx"
        if visual_plan and not is_pptx_template:
            logger.info("➕ 追加模板页 (Blank Template Slides)...")
            # 简化的模板页提示词
            tpl_prompt = f"A blank presentation template background. {style_config.get('description', '')} style. Use color palette: {', '.join(style_config.get('palette', []))}. DO NOT generate any text, logos, or content. Only abstract structural elements."
            
            visual_plan.append({
                "page_num": len(visual_plan) + 1,
                "type": "template_content",
                "title": "空白内容模板",
                "visual_prompt": tpl_prompt,
                "reference_image": None,
                "style_config": style_config,
                "layout": "centered_headline"
            })
            visual_plan.append({
                "page_num": len(visual_plan) + 1,
                "type": "template_split",
                "title": "空白分栏模板",
                "visual_prompt": tpl_prompt,
                "reference_image": None,
                "style_config": style_config,
                "layout": "left_text_right_visual"
            })

        return visual_plan
