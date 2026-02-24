"""
PPT Generation Executor
读取 ppt_generation_plan.json 并调用 Nano Banana Pro 生成最终 PPT
"""
import os
import sys
import json
import logging
from pathlib import Path
from PIL import Image
from pptx import Presentation
from pptx.util import Inches

# 复用 PPTGenerator 类
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../..')))
from nano_banana_ppt.core.generator import PPTGenerator

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def execute_plan(plan_file: str, output_name: str = "Final_Presentation"):
    if not os.path.exists(plan_file):
        print(f"❌ 找不到计划文件: {plan_file}")
        return

    with open(plan_file, 'r', encoding='utf-8') as f:
        visual_plan = json.load(f)
        
    api_key = os.getenv("OPENAI_API_KEY")
    api_base = os.getenv("OPENAI_API_BASE")
    generator = PPTGenerator(api_key, api_base)
    
    output_dir = Path("output")
    output_dir.mkdir(exist_ok=True)
    
    images = []
    
    print(f"\n🚀 开始执行生成任务，共 {len(visual_plan)} 页...")
    
    master_slide_image = None
    
    for i, slide in enumerate(visual_plan):
        print(f"\n[{i+1}/{len(visual_plan)}] Generating Page {slide['page_num']} ({slide.get('type', 'content')})...")
        
        prompt = slide['visual_prompt']
        
        # 准备参考图
        reference_images = []
        
        # 如果计划中有指定的 reference_image (来自模版)，优先使用
        if slide.get('reference_image') and os.path.exists(slide['reference_image']):
            try:
                ref_img = Image.open(slide['reference_image'])
                reference_images = [ref_img]
                print(f"  - 使用模版参考图: {os.path.basename(slide['reference_image'])}")
            except Exception as e:
                logger.warning(f"无法加载参考图: {e}")

        # 如果没有指定参考图，且是 AI 铸模模式 (Template Mode)，使用生成的 Master Slide
        if not reference_images and slide.get('type') == 'content' and master_slide_image:
            reference_images = [master_slide_image]
            print("  - 使用生成的母版 (AI Minted Master) 作为参考")
            
        try:
            # 调用生图
            is_background_only = slide.get('type') == 'background_only'
            image = generator.generate_image(prompt, aspect_ratio="16:9", reference_images=reference_images, is_background_only=is_background_only)
            images.append(image)
            
            # 如果是第一张内容页且当前没有参考图，将其设为母版
            if slide.get('type') == 'content' and master_slide_image is None and not reference_images:
                master_slide_image = image
                print("  - 已捕获为母版 (Master Slide)")
                
        except Exception as e:
            logger.error(f"生成失败: {e}")
            # 占位
            from PIL import Image
            images.append(Image.new('RGB', (1920, 1080), color='gray'))

    # 组装 PPT
    output_path = output_dir / f"{output_name}.pptx"
    generator.create_pptx(images, str(output_path))
    print(f"\n✅ PPT 生成完成: {output_path}")

if __name__ == "__main__":
    pass
