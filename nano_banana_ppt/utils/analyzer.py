"""
PPT 视觉差异分析代理
使用 Gemini Vision 对比分析两组 PPT 幻灯片
"""
import os
import base64
import logging
from io import BytesIO
from PIL import Image
from openai import OpenAI

from .llm_client import chat_completion_with_fallback, MODEL_FALLBACK_CHAIN

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class PPTAnalyst:
    def __init__(self, api_key: str, api_base: str = None):
        self.client = OpenAI(
            api_key=api_key,
            base_url=api_base or "https://generativelanguage.googleapis.com/v1beta/openai",
            timeout=120.0,
            max_retries=3
        )
        self.model = "gemini-3.1-pro-preview"

    def analyze_slides(self, notebooklm_images, our_images):
        """对比分析两组幻灯片"""
        
        # 准备图片数据
        messages = [
            {"role": "system", "content": """你是一位世界级的演示文稿设计总监和视觉批评家。
你的任务是深入对比两组 PPT 幻灯片的视觉质量、排版逻辑和信息传达效率。

【左侧/第一组】是 Google NotebookLM 生成的标杆案例 (Benchmark)。
【右侧/第二组】是我们当前生成的版本 (Our Version)。

请从以下维度进行严厉而深刻的批评与对比分析：

1. **信息层级与排版 (Hierarchy & Layout)**：
   - NotebookLM 是如何处理标题、正文和图表的？它的留白是否更高级？
   - 我们的版本是否显得拥挤？信息重点是否突出？

2. **视觉风格与一致性 (Style & Consistency)**：
   - NotebookLM 的风格是否更统一？它的配色方案有何特点（如深色模式的运用）？
   - 我们的版本在风格一致性上差距在哪里？

3. **图文结合 (Text-Image Integration)**：
   - NotebookLM 的文字是如何融入画面的？（注意：它可能使用了特殊的文本渲染技术）
   - 我们的文字是否显得"浮"在图片上？或者与背景冲突？

4. **数据可视化 (Data Viz)**：
   - 如果有图表，NotebookLM 的图表是否更具语义性和美感？

5. **总结差距 (The Gap)**：
   - 用一句话总结我们的版本最致命的弱点是什么。
   - 提出 3 个最优先的改进建议。

请用中文输出报告。"""},
            {"role": "user", "content": []}
        ]
        
        content = messages[1]["content"]
        content.append({"type": "text", "text": "这是 NotebookLM 生成的 PPT (Benchmark):"})
        
        # 添加 NotebookLM 图片
        for img_path in notebooklm_images[:3]: # 取前3页对比
            with open(img_path, "rb") as f:
                b64 = base64.b64encode(f.read()).decode()
                content.append({
                    "type": "image_url",
                    "image_url": {"url": f"data:image/png;base64,{b64}"}
                })
        
        content.append({"type": "text", "text": "\n\n这是我们生成的 PPT (Our Version):"})
        
        # 添加我们的图片
        for img_path in our_images[:3]: # 取前3页对比
            with open(img_path, "rb") as f:
                b64 = base64.b64encode(f.read()).decode()
                content.append({
                    "type": "image_url",
                    "image_url": {"url": f"data:image/png;base64,{b64}"}
                })
        
        # 调用模型
        try:
            logger.info("正在进行视觉对比分析...")
            response = chat_completion_with_fallback(
                self.client, model=self.model, model_fallback=MODEL_FALLBACK_CHAIN,
                messages=messages,
                temperature=0.5,
                max_tokens=2000
            )
            return response.choices[0].message.content
        except Exception as e:
            logger.error(f"分析失败: {e}")
            return str(e)

if __name__ == "__main__":
    notebooklm_imgs = [f"analysis_temp/notebooklm_slide_{i}.png" for i in range(1, 4)]
    our_imgs = [f"analysis_temp/ours_slide_{i}.png" for i in range(1, 4)]
    
    # 检查文件是否存在
    notebooklm_imgs = [p for p in notebooklm_imgs if os.path.exists(p)]
    our_imgs = [p for p in our_imgs if os.path.exists(p)]
    
    if not notebooklm_imgs or not our_imgs:
        print("错误: 找不到足够的图片文件进行对比")
        import sys; sys.exit(1)
        
    api_key = os.getenv("OPENAI_API_KEY")
    analyst = PPTAnalyst(api_key)
    report = analyst.analyze_slides(notebooklm_imgs, our_imgs)
    
    print("\n" + "="*50)
    print("PPT 视觉差异分析报告")
    print("="*50 + "\n")
    print(report)








