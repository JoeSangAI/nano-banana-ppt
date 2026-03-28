"""
Template Agent - 新增 PNG/JPG 图片模板解析方法
"""

def process_image_template(self, image_path: str) -> Dict:
    """
    解析 PNG/JPG 图片模板，提取主色调和风格信息

    Args:
        image_path: 图片文件路径

    Returns:
        模板信息字典，包含配色、参考图等
    """
    logger.info(f"🎨 Template Agent: 正在解析图片模板 {image_path}...")

    try:
        # 打开图片
        img = Image.open(image_path)

        # 提取主色调
        from ..utils.image_utils import extract_dominant_colors
        colors = extract_dominant_colors(image_path, num_colors=5)

        logger.info(f"   提取到的主色调: {', '.join(colors)}")

        # 保存参考图到输出目录
        ref_filename = f"ref_image_{os.path.basename(image_path)}"
        ref_path = os.path.join(self.output_dir, ref_filename)
        img.save(ref_path)

        # 构建模板信息
        template_info = {
            "source_type": "image",
            "file_path": image_path,
            "color_palette": colors,
            "primary_color": colors[0] if colors else "#FFFFFF",
            "secondary_color": colors[1] if len(colors) > 1 else "#000000",
            "accent_color": colors[2] if len(colors) > 2 else "#CC0000",
            "reference_images": [ref_path],
            "page_types": ["Cover"],  # 图片模板默认作为封面参考
            "logo_path": None
        }

        logger.info(f"✅ 图片模板解析完成")
        logger.info(f"   主色: {template_info['primary_color']}")
        logger.info(f"   辅色: {template_info['secondary_color']}")
        logger.info(f"   强调色: {template_info['accent_color']}")

        return template_info

    except Exception as e:
        logger.error(f"图片模板解析失败: {e}")
        # 返回默认配色
        return {
            "source_type": "image",
            "file_path": image_path,
            "color_palette": ["#FFFFFF", "#000000", "#CC0000"],
            "primary_color": "#FFFFFF",
            "secondary_color": "#000000",
            "accent_color": "#CC0000",
            "reference_images": [],
            "page_types": [],
            "logo_path": None
        }
