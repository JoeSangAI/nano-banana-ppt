import os
from PIL import Image

def normalize_image_path(path: str, base_dir: str = "") -> str:
    """
    统一处理图片路径：file:// 协议、相对路径、绝对路径

    Args:
        path: 原始路径
        base_dir: 基准目录（用于解析相对路径）

    Returns:
        规范化后的绝对路径
    """
    if not path:
        return path

    # 1. 去除 file:// 协议
    if path.startswith("file://"):
        path = path[7:]

    # 2. 如果是绝对路径且存在，直接返回
    if os.path.isabs(path) and os.path.exists(path):
        return path

    # 3. 尝试相对于 base_dir 解析
    if base_dir:
        abs_path = os.path.normpath(os.path.join(base_dir, path))
        if os.path.exists(abs_path):
            return abs_path

    # 4. 返回原路径
    return path


def extract_dominant_colors(image_path: str, num_colors: int = 3) -> list:
    """
    Extract dominant hex colors from an image using Pillow's quantize.
    
    Args:
        image_path: Path to the image file (e.g., logo).
        num_colors: Number of dominant colors to extract.
        
    Returns:
        List of hex color strings, e.g., ['#ff0000', '#00ff00'].
    """
    try:
        img = Image.open(image_path).convert("RGBA")
        
        # Create a white background to composite over (avoids black background for transparent PNGs)
        bg = Image.new("RGBA", img.size, (255, 255, 255, 255))
        img_with_bg = Image.alpha_composite(bg, img).convert("RGB")
        
        # Resize to speed up processing and group similar colors
        img_with_bg.thumbnail((150, 150))
        
        # Quantize to find dominant colors
        q_img = img_with_bg.quantize(colors=num_colors, method=Image.Quantize.MEDIANCUT)
        palette = q_img.getpalette()[:num_colors*3]
        
        colors = []
        for i in range(0, len(palette), 3):
            r, g, b = palette[i:i+3]
            colors.append(f"#{r:02x}{g:02x}{b:02x}")
            
        return colors
    except Exception as e:
        print(f"Failed to extract colors from {image_path}: {e}")
        return []
