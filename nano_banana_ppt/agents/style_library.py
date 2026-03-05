"""
Curated Style Library for Nano Banana PPT

This module contains predefined, high-quality visual style definitions.
When a user selects one of these styles, the VisualAgent will use the curated
definition directly, ensuring consistent and high-quality results.
"""

STYLE_LIBRARY = {
    "claude_minimalist": {
        "aliases": ["claude", "claude风格", "克劳德风格", "claude minimalist", "claude minimal"],
        "description": "Claude Minimalist style. Warm, intellectual, and approachable. Uses soft off-white/cream backgrounds, elegant typography mixing serif (for headings) and sans-serif (for body). Conveys a sense of calm, thoughtful AI assistance.",
        "palette": ["#F9F8F6", "#2D2D2D", "#D97757", "#E6E2DD"],
        "fonts": ["Tiempos", "Inter"],
        "shape_language": "Soft rounded corners, organic but structured, lots of negative space.",
        "imagery_style": "Minimalist, subtle textures, editorial illustration, warm lighting."
    },
    "neo_brutalism": {
        "aliases": ["neo-brutalism", "neo brutalism", "新粗野主义", "新粗野主义宣言风格", "brutalist"],
        "description": "Neo-Brutalism style. Raw, bold, and unapologetic. High contrast with stark backgrounds and bright accent colors (lime green, bright yellow). Characterized by thick black borders, hard offset shadows, and grotesque typography. No gradients.",
        "palette": ["#FFFFFF", "#000000", "#E0FF4F", "#FF6666", "#4D96FF"],
        "fonts": ["Space Grotesk", "Helvetica Now Display"],
        "shape_language": "Harsh rectangles, thick black borders, hard drop shadows, sharp edges.",
        "imagery_style": "Pop-art, high-contrast, bold cutouts, flat colors, raw textures."
    },
    "japanese_aesthetic": {
        "aliases": ["japanese aesthetic", "wabi-sabi", "日式美学", "日式美学幻灯片", "和风", "日式极简"],
        "description": "Japanese Wabi-Sabi minimalist aesthetic. Zen, quiet, and balanced. Uses muted earth tones, extreme negative space, and asymmetrical balance. Emphasizes natural materials and tranquility.",
        "palette": ["#EAE7E0", "#4A4E4D", "#828C7E", "#B0A18F", "#2C3531"],
        "fonts": ["Shippori Mincho", "Noto Sans JP"],
        "shape_language": "Asymmetrical balance, subtle lines, extreme negative space, natural proportions.",
        "imagery_style": "Film photography, natural light, subtle shadows, ink wash, stone and wood textures."
    },
    "apple_keynote": {
        "aliases": ["apple keynote", "苹果风", "苹果发布会", "苹果发布会风格", "keynote"],
        "description": "Apple Keynote presentation style. Premium, cinematic, and dramatic. Deep black backgrounds with massive, bold white typography. Accentuated by vibrant, glowing gradients and hyper-realistic 3D elements.",
        "palette": ["#000000", "#FFFFFF", "#1D1D1F", "#0066CC", "#FF2D55"],
        "fonts": ["San Francisco", "SF Pro Display"],
        "shape_language": "Sleek, invisible grids, ultra-minimalist, centered focus.",
        "imagery_style": "Cinematic lighting, hyper-realistic 3D renders, dramatic spotlighting."
    },
    "liquid_glass": {
        "aliases": ["liquid glass", "glassmorphism", "毛玻璃", "液态玻璃", "bento", "便当盒"],
        "description": "Premium Liquid Glass / Glassmorphism style with Bento Grid layouts. High-end tech aesthetic. Semi-transparent frosted glass cards with ultra-thin borders and subtle drop shadows over an ethereal, soft-focus background.",
        "palette": ["#F2F2F7", "#FFFFFF", "#8E8E93", "#007AFF", "#34C759"],
        "fonts": ["Inter", "Helvetica Neue"],
        "shape_language": "Rounded rectangles (Bento grids), asymmetrical grid layouts, frosted glass panels.",
        "imagery_style": "Soft caustics, ethereal light leaks, abstract fluid background, macro textures."
    },
    "magazine_editorial": {
        "aliases": ["magazine", "editorial", "时尚杂志", "杂志风", "vogue", "kinfolk"],
        "description": "High-end Fashion Magazine Editorial style. Elegant, spacious, and cinematic. Combines dramatic full-bleed photography with extreme negative space and sophisticated typography mixing large elegant serifs with clean sans-serif body text.",
        "palette": ["#FAF9F6", "#1A1A1A", "#8B0000", "#D3D3D3", "#4A4A4A"],
        "fonts": ["Playfair Display", "Didot", "Montserrat"],
        "shape_language": "Extreme negative space, clean thin divider lines, asymmetrical but perfectly balanced.",
        "imagery_style": "Cinematic fashion photography, high-end editorial, soft grain, dramatic lighting."
    },
    "soft_3d_clay": {
        "aliases": ["soft 3d", "clay", "3d clay", "3d粘土", "粘土风", "马卡龙", "macaron", "cute"],
        "description": "Soft 3D Clay / Inflated style. Cute, friendly, and approachable. Uses soft pastel macaron colors and 3D rendered elements that look like inflated balloons or smooth matte clay.",
        "palette": ["#FFB6C1", "#87CEFA", "#98FB98", "#FFE4B5", "#2F4F4F"],
        "fonts": ["Quicksand", "Nunito"],
        "shape_language": "Puffy, inflated, extremely rounded, pill shapes, soft and bouncy.",
        "imagery_style": "3D clay renders, matte surfaces, soft ambient occlusion lighting, pastel colors."
    },
    "dark_luxury": {
        "aliases": ["dark luxury", "luxury", "黑金", "奢华", "黑金奢华", "premium"],
        "description": "Dark Luxury aesthetic. Premium, exclusive, and elegant. Deep charcoal or black backgrounds paired with rich gold, brass, or copper metallic accents. Conveys high net worth, exclusivity, and premium quality.",
        "palette": ["#0D0D0D", "#1A1A1A", "#D4AF37", "#C5B358", "#F5F5F5"],
        "fonts": ["Cinzel", "Optima", "Lato"],
        "shape_language": "Symmetrical, sharp geometric accents, thin gold lines, elegant framing.",
        "imagery_style": "Low-key lighting, metallic reflections, high contrast chiaroscuro, luxurious textures."
    },
    "traditional_chinese": {
        "aliases": ["traditional chinese", "chinese", "国风", "新中式", "国潮"],
        "description": "Modern Traditional Chinese (Neo-Chinese) aesthetic. Poetic, cultural, and serene. Incorporates elements of traditional ink wash painting with modern minimalist layout. Uses traditional vermilion red, jade green, and ink black on rice-paper-like backgrounds.",
        "palette": ["#F5F4F1", "#222222", "#C83C23", "#4B5CC4", "#817E7B"],
        "fonts": ["Noto Serif SC", "FZShuTi"],
        "shape_language": "Circular windows (moon gates), vertical text elements, fluid ink strokes, negative space (留白).",
        "imagery_style": "Ink wash (水墨), soft mountain silhouettes, traditional textures, serene and atmospheric."
    },
    "holographic_chrome": {
        "aliases": ["holographic", "chrome", "镭射", "全息", "全息渐变", "y2k"],
        "description": "Holographic Chrome style. Futuristic, high-tech, and edgy Y2K vibe. Features polished chrome metallic surfaces reflecting rainbow holographic gradients (blue, purple, pink) against very dark or very light backgrounds.",
        "palette": ["#121212", "#E0E0E0", "#4169E1", "#FF00FF", "#00FFFF"],
        "fonts": ["Syne", "Space Mono"],
        "shape_language": "Fluid metallic blobs, sharp chrome typography, liquid metal distortion.",
        "imagery_style": "Mirror chrome reflections, iridescent film interference, 3D fluid metals, prismatic light."
    },
    "cyberpunk": {
        "aliases": ["cyberpunk", "赛博朋克", "赛博朋克风格", "tech neon"],
        "description": "Cyberpunk high-tech style. Dark, dystopian but vibrant. Deep navy/black backgrounds with neon cyan, magenta, and electric yellow accents. Features glitch effects, grid lines, and glowing UI elements.",
        "palette": ["#0B0C10", "#45A29E", "#66FCF1", "#FF007F", "#F3E600"],
        "fonts": ["JetBrains Mono", "Orbitron"],
        "shape_language": "Geometric, angled cuts, wireframe grids, glowing neon borders.",
        "imagery_style": "Neon lighting, glitch art, high-tech HUD overlays, dark alleyway moods."
    },
    "academic_paper": {
        "aliases": ["academic paper", "学术风", "学术报告", "research", "nature", "science"],
        "description": "Academic Research style inspired by Nature/Science papers. Clean, authoritative, and data-dense. White background, classic serif typography for elegance, and precise layout for charts and data.",
        "palette": ["#FFFFFF", "#111111", "#004B87", "#A32638"],
        "fonts": ["Times New Roman", "Arial"],
        "shape_language": "Strict columns, thin elegant divider lines, formal grid structure.",
        "imagery_style": "Scientific diagrams, crisp data visualizations, formal and objective."
    }
}

def get_curated_style(user_preference: str) -> dict:
    """
    Check if the user preference matches any curated style aliases.
    Returns the style dict if found, else None.
    """
    if not user_preference:
        return None
        
    pref_lower = user_preference.lower().strip()
    
    for style_key, style_data in STYLE_LIBRARY.items():
        for alias in style_data.get("aliases", []):
            if alias.lower() in pref_lower or pref_lower in alias.lower():
                return style_data
                
    return None
