"""
Visual Prompt Agent
负责将叙事大纲转化为 Nano Banana Pro 的生图指令
实现风格路由（模版克隆 vs AI 铸模）
"""
import os
import json
import logging
from typing import Dict, List, Optional
from openai import OpenAI

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class VisualAgent:
    def __init__(self, api_key: str, api_base: str = None):
        self.client = OpenAI(
            api_key=api_key,
            base_url=api_base or "https://generativelanguage.googleapis.com/v1beta/openai",
            timeout=120.0,
            max_retries=3
        )
        self.model = "gemini-2.0-flash" # 用于 Prompt Engineering

    def define_style(self, constraints: Dict, assets: Dict, template_info: Dict = None) -> str:
        """
        Step 1: 风格定义 (Style Definition)
        """
        if template_info:
            logger.info("🎨 Visual Agent: 进入【模版克隆模式】")
            style_desc = template_info.get('style_description', '')
            palette = ", ".join(template_info.get('color_palette', []))
            return f"TEMPLATE_MODE: Follow the provided template style. {style_desc}. Palette: {palette}"
            
        logger.info("🎨 Visual Agent: 正在定义视觉风格...")
        
        # 允许 AI 自主选择最合适的字体，但要求其明确指定
        prompt = f"""You are a world-class Art Director. Define a cohesive visual style guide for a PPT presentation.

【Context】
- Topic: {constraints.get('presentation_type', 'Business')}
- Audience: {constraints.get('target_audience', 'General')}
- Vibe: {constraints.get('style_preference', 'Professional')}

【Task】
Output a STRICT visual design system in plain English. Include:
1. **Color Palette**: Specify HEX codes for Background, Text, and Accents. (e.g., "Midnight Blue #0A192F bg, Gold #FFD700 accents")
2. **Typography**: Choose a specific font pair appropriate for the vibe. (e.g., "Title: Playfair Display (Serif), Body: Lato (Sans-serif)" OR "Title: Helvetica (Sans-serif), Body: Roboto")
3. **Shape Language**: (e.g., "Rounded corners, organic blobs" OR "Sharp angles, geometric grids")
4. **Imagery Style**: (e.g., "Photorealistic, cinematic lighting" OR "Flat vector illustrations, minimal")

Output the style description directly. Do not include markdown code blocks."""

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are an expert Art Director."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            logger.error(f"风格定义失败: {e}")
            return "Professional corporate style, #FFFFFF background, #333333 text, Arial font."

    def _search_visual_appearance(self, query: str) -> str:
        """
        [RAG] 使用 Google Search 增强实体视觉描述
        通过 requests 直接调用 Gemini API 并启用 Google Search 工具
        """
        logger.info(f"🔍 Visual Agent: 正在搜索实体外观 '{query}'...")
        
        api_key = self.client.api_key
        if not api_key: 
            return query
            
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-pro:generateContent?key={api_key}"
        
        prompt_text = f"""Search for the visual appearance of '{query}'. 
Describe it in detail for an AI image generator. 
Focus on: Colors, Logo shapes, Packaging, Key visual identifiers.
Keep it under 50 words.
Example: "A white bottle with a large black Japanese character '気', fruit illustrations, clean minimalist design." """

        payload = {
            "contents": [{"parts": [{"text": prompt_text}]}],
            "tools": [{"google_search_retrieval": {}}] # 启用 Google Search
        }
        
        try:
            import requests
            response = requests.post(url, json=payload, headers={'Content-Type': 'application/json'}, timeout=30)
            if response.status_code == 200:
                data = response.json()
                # 尝试提取文本，通常在 candidates[0].content.parts[0].text
                if 'candidates' in data and data['candidates']:
                    return data['candidates'][0]['content']['parts'][0]['text']
            
            logger.warning(f"搜索失败: {response.status_code} - {response.text}")
            return query
            
        except Exception as e:
            logger.warning(f"搜索请求异常: {e}")
            return query

    def generate_visual_plan(self, narrative_outline: List[Dict], style_definition: str, assets: Dict, template_info: Dict = None) -> List[Dict]:
        """
        生成完整的视觉执行计划 (Visual Plan)
        """
        logger.info("🎨 Visual Agent: 正在生成视觉执行计划...")
        
        visual_plan = []
        
        # 遍历每一页
        for page in narrative_outline:
            page_type = page.get('type', 'content').lower()
            text_content = page.get('text_content', {})
            
            # 0. RAG 实体增强 (针对 Content 页面的 Body)
            # 简单的关键词提取逻辑：如果 body 里提到具体产品名，尝试增强
            # 这里简化处理：将 body 的前 50 个字作为上下文，让 AI 自动判断是否需要视觉增强
            # (在实际 Prompt 中，我们会让模型决定是否需要搜索，但为了效率，这里我们对特定关键词做预处理)
            # 比如检测 "元气森林", "Tesla" 等实体
            # 目前版本先跳过自动检测，依靠 Visual Prompt 里的 Instruction 让模型去描述细节
            
            # 1. 确定参考图 (Reference Image)
            reference_image_path = None
            
            # 检查是否有源文档图片引用 (Source Image)
            # 格式约定: visual_suggestion 中包含 "Use source image: [url]"
            visual_suggestion = page.get('visual_suggestion', '')
            import re
            source_img_match = re.search(r'Use source image: \[(.*?)\]', visual_suggestion)
            
            if source_img_match:
                # 如果是网络图片，这里仅作记录，实际下载逻辑需在 Executor 中实现
                # 或者如果已经下载到了 assets 目录，直接引用
                img_url = source_img_match.group(1)
                logger.info(f"📸 发现源图片引用: {img_url}")
                # TODO: 在 Executor 中增加下载逻辑，这里暂不处理路径
                
            if template_info and not reference_image_path:
                # 优先使用模版对应的页面类型
                refs = template_info.get('reference_images', {})
                if page_type == 'cover':
                    reference_image_path = refs.get('ref_cover')
                elif page_type == 'toc':
                    reference_image_path = refs.get('ref_toc') or refs.get('ref_cover')
                elif page_type == 'hero':
                    reference_image_path = refs.get('ref_hero') or refs.get('ref_content')
                elif page_type == 'back':
                    reference_image_path = refs.get('ref_back') or refs.get('ref_cover')
                else: # content
                    reference_image_path = refs.get('ref_content')
                
                # 如果没找到对应类型，回退到第一张图
                if not reference_image_path and refs:
                    reference_image_path = list(refs.values())[0]

            # 2. 构建 Text Rendering Instruction (中文)
            # 原文直给逻辑：直接将 narrative agent 生成的详细论据塞入，不进行删减
            render_text_block = "**TEXT CONTENT TO DISPLAY:**\n"
            render_text_block += "(Render exactly as written below. Do NOT translate.)\n\n"
            
            if text_content.get('headline'):
                render_text_block += f"Headline: \"{text_content['headline']}\"\n"
            if text_content.get('subhead'):
                render_text_block += f"Subtitle: \"{text_content['subhead']}\"\n"
            if page_type == 'content' and text_content.get('body'):
                render_text_block += "Body Points:\n"
                for item in text_content['body']: 
                    render_text_block += f"• \"{item}\"\n"

            # 3. 构建 Visual Prompt (英文)
            system_prompt = "You are an expert Prompt Engineer for Nano Banana Pro (Gemini Image)."
            
            # 视觉设计系统注入 (动态引用 style_definition)
            design_system = f"""
【Visual Design System (STRICT)】
1. **Global Style**: {style_definition}
2. **Layout Rule**:
   - Cover: Asymmetric or Centered high impact.
   - Content: Split screen (Left Text / Right Visual) OR Grid. Text MUST be on a clean, high-contrast background.
   - Hero: Full screen immersive visual with overlay text.
3. **Consistency Check**: Ensure all fonts, colors, and shapes match the Global Style defined above.
"""

            # 针对模版模式优化 Prompt
            if template_info:
                user_prompt = f"""Generate a high-fidelity image generation prompt for a PPT slide.
                
{design_system}

【Mode: TEMPLATE CLONING】
You MUST strictly follow the layout and style of the provided reference image.
- **Reference Image**: Using '{os.path.basename(reference_image_path) if reference_image_path else "None"}' as style anchor.
- **Goal**: Recreate the slide structure but replace the text content.

【Page Context】
- Current Section: {page.get('section_title', 'General')}
- Page Type: {page_type.upper()}
- Visual Suggestion: {visual_suggestion}
- Content Context: {str(text_content)[:300]}...

【Instruction】
1. **Scene Description**: Describe the visual elements in detail. 
   - If specific products/entities are mentioned (e.g. 'Genki Forest', 'Tesla'), describe their visual appearance accurately (colors, shapes).
   - Use the Global Style for background and decorations.
2. **Text Integration**: Plan the layout so the text fits naturally.

{render_text_block}

【Negative Constraints】
- Do NOT render instruction labels like "MUST RENDER TEXT", "Headline:", "Subtitle:", "Body Points:".
- Do NOT include generic placeholder text like "Lorem Ipsum".
- Do NOT include generic logos like "Strategic Cooperation", "Business Proposal", "Agency Logo".
- Do NOT translate the Chinese text.

【Output Format】
Directly output the final Prompt string.
"""
            else:
                # AI 铸模模式
                user_prompt = f"""Generate a high-fidelity image generation prompt for a PPT slide.

{design_system}

【Page Context】
- Current Section: {page.get('section_title', 'General')}
- Page Type: {page_type.upper()}
- Visual Suggestion: {visual_suggestion}
- Content Context: {str(text_content)[:300]}...

【Instruction】
1. **Scene Description**: Describe the visual elements in detail.
   - If specific products/entities are mentioned (e.g. 'Genki Forest', 'Tesla'), describe their visual appearance accurately (colors, shapes).
   - Use the Global Style for background and decorations.
2. **Text Integration**: Plan the layout so the text fits naturally.

{render_text_block}

【Negative Constraints】
- Do NOT render instruction labels like "MUST RENDER TEXT", "Headline:", "Subtitle:", "Body Points:".
- Do NOT include generic placeholder text like "Lorem Ipsum".
- Do NOT include generic logos like "Strategic Cooperation", "Business Proposal", "Agency Logo".
- Do NOT translate the Chinese text.

【Output Format】
Directly output the final Prompt string.
"""

            try:
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt}
                    ],
                    temperature=0.7
                )
                final_prompt = response.choices[0].message.content.strip()
                
                # 附加信息
                plan_item = page.copy()
                plan_item['visual_prompt'] = final_prompt
                plan_item['reference_image'] = reference_image_path
                plan_item['logo_path'] = assets.get('logo_path') or template_info.get('logo_path') if template_info else None
                
                visual_plan.append(plan_item)
                
            except Exception as e:
                logger.error(f"Prompt生成失败 (Page {page.get('page_num')}): {e}")
        
        # [新增] 自动追加一页“纯背景”作为最后一页
        if visual_plan:
            logger.info("➕ 追加纯背景页 (Bonus Slide)...")
            bg_prompt = f"""Generate a pure background image for a PPT slide.
            
{design_system}

【Instruction】
- Create a clean, high-quality background texture or gradient matching the Global Style.
- **CRITICAL**: NO TEXT, NO LOGOS, NO ICONS, NO FOREGROUND OBJECTS.
- This image will be used as a wallpaper for editable slides.

【Output Format】
Directly output the final Prompt string.
"""
            # 为了获取 Prompt，我们需要再调用一次 LLM，或者简单点，直接构造一个基于规则的 Prompt
            # 为了保证风格一致性，最好还是让 LLM 基于 design_system 生成
            try:
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {"role": "system", "content": "You are a background texture designer."},
                        {"role": "user", "content": bg_prompt}
                    ],
                    temperature=0.7
                )
                bg_final_prompt = response.choices[0].message.content.strip()
                
                visual_plan.append({
                    "page_num": len(visual_plan) + 1,
                    "type": "background_only",
                    "title": "Pure Background",
                    "visual_prompt": bg_final_prompt,
                    "reference_image": None # 背景页不强制参考特定布局，只参考风格
                })
            except Exception as e:
                logger.error(f"背景页生成失败: {e}")

        return visual_plan
