"""
Template Agent
负责解析 PDF/PPTX 模版，提取风格、Logo 和关键页面参考图
"""
import os
import json
import fitz  # PyMuPDF
from PIL import Image
import logging
from typing import Dict, List, Optional
from openai import OpenAI
import base64
import io

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class TemplateAgent:
    def __init__(self, api_key: str, api_base: str = None):
        self.client = OpenAI(
            api_key=api_key,
            base_url=api_base or "https://generativelanguage.googleapis.com/v1beta/openai",
            timeout=120.0,
            max_retries=3
        )
        self.model = "gemini-3-pro-preview" # Vision capability is crucial here
        self.output_dir = "template_assets"
        os.makedirs(self.output_dir, exist_ok=True)

    def process_template(self, template_path: str) -> Dict:
        """
        处理模版文件，返回模版资产信息
        """
        logger.info(f"🎨 Template Agent: 正在解析模版 {template_path}...")
        
        # 1. 将模版转换为图片序列
        images = self._convert_to_images(template_path)
        if not images:
            raise ValueError("无法解析模版文件")
            
        # 2. 使用 AI 分析页面类型并提取风格
        template_info = self._analyze_template_structure(images)
        
        # 3. 提取 Logo (尝试从封面提取)
        logo_path = self._extract_logo(images[0], template_info.get('logo_location'))
        template_info['logo_path'] = logo_path
        
        # 4. 保存关键参考图
        ref_paths = self._save_reference_images(images, template_info.get('page_types', []))
        template_info['reference_images'] = ref_paths
        
        return template_info

    def _convert_to_images(self, path: str) -> List[Image.Image]:
        """将 PDF/PPT 转为 PIL Image 列表"""
        images = []
        if path.lower().endswith('.pdf'):
            doc = fitz.open(path)
            for page in doc:
                pix = page.get_pixmap(matrix=fitz.Matrix(2, 2))
                img_data = pix.tobytes("png")
                images.append(Image.open(io.BytesIO(img_data)))
        # TODO: Add PPTX support via python-pptx -> image conversion service or simple placeholder
        # 目前 python-pptx 转图片比较复杂，建议先只支持 PDF 模版，或者假设 PPTX 用户已提供图片
        return images

    def _analyze_template_structure(self, images: List[Image.Image]) -> Dict:
        """调用 Vision 模型分析模版结构"""
        logger.info("🧠 正在分析模版结构与风格...")
        
        # 选取前 5 页进行分析
        sample_images = images[:5]
        
        # 构建多模态 Prompt
        content = [
            {"type": "text", "text": """你是专业的 UI/UX 设计师。请分析这组 PPT 模版图片。
            
任务 1: 识别每张图的页面类型 (Cover, TOC, Section, Content, Hero, Back)。
任务 2: 提取全局视觉风格 (配色、字体、装饰)。
任务 3: 找出 Logo 的位置 (Top-Left, Top-Right, Center 等)。

请输出 JSON 格式：
{
  "page_types": ["Cover", "Content", "Content", ...],
  "style_description": "Deep blue background...",
  "logo_location": "Top-Right",
  "color_palette": ["#000000", "#FFFFFF"]
}"""}
        ]
        
        for img in sample_images:
            buffered = io.BytesIO()
            img.save(buffered, format="PNG")
            b64 = base64.b64encode(buffered.getvalue()).decode()
            content.append({
                "type": "image_url", 
                "image_url": {"url": f"data:image/png;base64,{b64}"}
            })
            
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": content}],
                temperature=0.1
            )
            result = response.choices[0].message.content.strip()
            # Clean JSON
            if result.startswith('```json'): result = result[7:]
            if result.endswith('```'): result = result[:-3]
            return json.loads(result)
        except Exception as e:
            logger.error(f"模版分析失败: {e}")
            return {
                "page_types": ["Cover", "Content", "Content"],
                "style_description": "Professional business style",
                "logo_location": "Top-Right"
            }

    def _extract_logo(self, cover_image: Image.Image, location: str) -> Optional[str]:
        """
        简单的 Logo 提取逻辑 (裁剪)
        实际生产中应用 Object Detection 模型
        """
        if not location:
            return None
            
        w, h = cover_image.size
        crop_box = None
        
        if "Left" in location and "Top" in location:
            crop_box = (0, 0, w//3, h//4)
        elif "Right" in location and "Top" in location:
            crop_box = (w*2//3, 0, w, h//4)
        elif "Center" in location:
            crop_box = (w//3, h//3, w*2//3, h*2//3)
            
        if crop_box:
            try:
                logo_img = cover_image.crop(crop_box)
                save_path = os.path.join(self.output_dir, "extracted_logo.png")
                logo_img.save(save_path)
                logger.info(f"Logo 已提取: {save_path}")
                return save_path
            except Exception as e:
                logger.warning(f"Logo 提取失败: {e}")
                
        return None

    def _save_reference_images(self, images: List[Image.Image], page_types: List[str]) -> Dict:
        """保存分类后的参考图"""
        refs = {}
        # 确保 page_types 长度与 images 一致，不够则补 Content
        if len(page_types) < len(images):
            page_types.extend(['Content'] * (len(images) - len(page_types)))
            
        for img, p_type in zip(images, page_types):
            key = f"ref_{p_type.lower()}"
            if key not in refs: # 只存第一张遇到的该类型
                path = os.path.join(self.output_dir, f"{key}.png")
                img.save(path)
                refs[key] = path
        return refs

if __name__ == "__main__":
    pass
