"""
Narrative Architecture Agent
负责将用户输入转化为深度叙事大纲
"""
import os
import json
import logging
from typing import Dict, List, Optional
from openai import OpenAI

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class NarrativeAgent:
    def __init__(self, api_key: str, api_base: str = None):
        self.client = OpenAI(
            api_key=api_key,
            base_url=api_base or "https://generativelanguage.googleapis.com/v1beta/openai",
            timeout=120.0,
            max_retries=3
        )
        self.model = "gemini-2.0-flash" # Use faster model for stability

    def collect_constraints(self) -> Dict:
        """
        交互式收集用户约束参数 (CLI模式)
        """
        print("\n=== 🎯 PPT 叙事目标设定 ===")
        
        target_audience = input("1. 目标受众是谁？(例如：投资人、公司高管、大众): ").strip() or "通用受众"
        presentation_type = input("2. 演讲类型？(例如：Pitch Deck、年终汇报、教育课件): ").strip() or "商业演示"
        duration = input("3. 预计演讲时长？(例如：10分钟、30分钟): ").strip() or "15分钟"
        page_count = input("4. 期望页数？(默认为 10-15 页): ").strip()
        style_preference = input("5. 风格偏好？(例如：极简、科技感、国潮): ").strip() or "专业商务"
        
        return {
            "target_audience": target_audience,
            "presentation_type": presentation_type,
            "duration": duration,
            "page_count": page_count,
            "style_preference": style_preference
        }
        
    def analyze_content(self, content_context: str) -> Dict:
        """
        [自动推导] 分析源文档，提取元数据
        """
        logger.info("🧠 Narrative Agent: 正在分析源文档元数据...")
        prompt = f"""请分析这份文档，提取以下关键信息：
1. 目标受众 (Target Audience)
2. 核心主题 (Core Topic)
3. 建议的演讲时长 (Duration)
4. 适合的演示风格 (Style)

文档内容前 5000 字:
{content_context[:5000]}

请输出 JSON 格式：
{{
  "target_audience": "...",
  "presentation_type": "...",
  "duration": "...",
  "style_preference": "..."
}}"""
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.1
            )
            result = response.choices[0].message.content.strip()
            if result.startswith('```json'): result = result[7:]
            if result.endswith('```'): result = result[:-3]
            return json.loads(result)
        except Exception:
            return {}

    def extract_images_from_markdown(self, content: str) -> List[str]:
        """
        从 Markdown 内容中提取图片链接
        """
        import re
        # 匹配 ![alt](url) 格式
        images = re.findall(r'!\[.*?\]\((.*?)\)', content)
        # 过滤掉非图片链接（简单的扩展名检查）
        valid_images = [img for img in images if img.lower().endswith(('.png', '.jpg', '.jpeg', '.gif', '.webp'))]
        return valid_images

    def generate_narrative_outline(self, content_context: str, constraints: Dict) -> List[Dict]:
        """
        生成深度叙事大纲
        """
        logger.info("🧠 Narrative Agent: 正在构建叙事架构...")
        
        # 提取源文档中的图片
        source_images = self.extract_images_from_markdown(content_context)
        source_images_str = "\n".join([f"- {img}" for img in source_images[:5]]) # 仅列出前5张作为参考
        
        prompt = f"""你是一位顶尖的商业演示设计专家和视觉传达顾问。
请运用《演说之禅》、麦肯锡《金字塔原理》以及《高桥流简洁法》的核心技巧，帮我设计一份逻辑清晰且极具说服力的演示文稿大纲。

【项目背景】
- 目标受众: {constraints['target_audience']}
- 演示类型: {constraints['presentation_type']}
- 预计时长: {constraints['duration']}
- 期望页数: {constraints['page_count'] or '根据内容自动规划(约10-15页)'}
- 风格偏好: {constraints['style_preference']}

【输入内容】
{content_context[:50000]} ... (内容过长已截断)

【可用素材图片】
(如果内容涉及到以下图片所代表的场景或产品，请在 visual_suggestion 中明确引用)
{source_images_str}

【任务要求】
1. **结构化叙事 (Structure)**：
   - 引入 **Part / Section** 概念。将 PPT 划分为 3-5 个逻辑章节（如：背景、挑战、解决方案、愿景）。
   - 每一页都必须归属于某个 Section。

2. **内容精细度 (Granularity)**：
   - **首页极简**：封面页只包含标题、副标题和演讲人信息，**严禁堆砌其他素材**，保持纯粹的设计感。
   - **Content 页详实度**：每页包含 3-4 个核心论据。**每个论据的字数控制在 30-100 字之间**。既要讲透，又不能太长。保留原文的关键数据和案例。
   - **智能拆页**：如果某章节内容过多，请自动拆分为多页（如 P2-1, P2-2）。

3. **连贯性 (Flow)**：
   - 使用 `transition` 字段描述逻辑承接。

4. **页面类型强制**：
   - `cover`: 封面 (仅第1页)
   - `toc`: 目录
   - `section`: 章节页 (转场)
   - `content`: 标准内容页
   - `hero`: 英雄页
   - `back`: 封底

【JSON 数据结构】
[
  {{
    "page_num": 1,
    "section_title": "Part 1: 市场背景", 
    "type": "content", 
    "title": "页面标题",
    "core_message": "本页核心传递的信息",
    "transition": "逻辑过渡...", 
    "text_content": {{
        "headline": "大标题 (例如：盲区：为何我们看不见？)",
        "subhead": "导语/总起句 (CRITICAL)：这一页的核心观点或承接语。",
        "body": [
            "详细论据1 (30-100字)：...", 
            "详细论据2 (30-100字)：..."
        ]
    }},
    "visual_suggestion": "画面建议。如果可以使用源文档中的图片，请注明：'Use source image: [url]'"
  }},
  ...
]

请确保输出严格的 JSON 格式，不要包含 Markdown 代码块标记。"""

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "你是一个精通商业叙事的 PPT 架构师。请输出严格的 JSON 格式。"},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7
            )
            content = response.choices[0].message.content.strip()
            # 清理 Markdown 标记
            if content.startswith('```json'):
                content = content[7:]
            if content.endswith('```'):
                content = content[:-3]
            
            return json.loads(content)
            
        except Exception as e:
            logger.error(f"叙事大纲生成失败: {e}")
            raise

    def preview_outline(self, outline: List[Dict]) -> str:
        """
        生成大纲的自然语言预览文本
        """
        preview_text = "=== 📋 PPT 叙事大纲预览 (Story Flow) ===\n\n"
        preview_text += f"**🤖 AI 策划师**：为了还原文章的深度逻辑，我为您规划了这份 **{len(outline)} 页** 的连贯叙事大纲。请重点关注每一页的【逻辑承接】：\n\n"
        
        for page in outline:
            preview_text += f"#### **P{page['page_num']}: {page.get('text_content', {}).get('headline', page['title'])}**\n"
            
            # 增加过渡语展示，体现逻辑流
            if page.get('transition'):
                preview_text += f"> *🗣️ 逻辑承接*：{page['transition']}\n\n"
            
            # 内容展示
            text_content = page.get('text_content', {})
            
            # 始终展示大标题和副标题（如果有）
            if text_content.get('headline'):
                preview_text += f"   **📌 大标题**：{text_content['headline']}\n"
            if text_content.get('subhead'):
                preview_text += f"   **📝 导语/副标**：{text_content['subhead']}\n"
                
            if page['type'] == 'hero':
                # Hero 页通常不需要冗长的 body，重点是 subhead 或 core_message
                pass
            elif page['type'] == 'content' and text_content.get('body'):
                preview_text += f"   **📄 正文内容**：\n"
                for item in text_content['body']:
                    preview_text += f"     - {item}\n"
            
            preview_text += "\n"
            
        preview_text += "---\n**🤖 系统提示**：这个逻辑流是否足够连贯？(Y/N/修改意见)"
        return preview_text

if __name__ == "__main__":
    pass
