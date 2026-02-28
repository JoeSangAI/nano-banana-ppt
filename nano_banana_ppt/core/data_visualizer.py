"""
Data Visualizer - 从 table_data 程序化渲染表格与图表
保证数据忠实展示，不依赖 AI 生图
"""
import io
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm
from typing import Dict, List, Optional, Tuple
from PIL import Image, ImageOps, ImageDraw
import platform

# ── Font Configuration ──
def _configure_fonts():
    """Try to configure CJK fonts to avoid missing glyphs warnings."""
    system = platform.system()
    font_candidates = []
    
    if system == 'Darwin':  # macOS
        font_candidates = ['PingFang SC', 'Heiti SC', 'STHeiti', 'Hiragino Sans GB', 'AppleGothic', 'Arial Unicode MS']
    elif system == 'Windows':
        font_candidates = ['Microsoft YaHei', 'SimHei', 'SimSun', 'Malgun Gothic', 'Meiryo']
    else:  # Linux
        font_candidates = ['Noto Sans CJK SC', 'WenQuanYi Zen Hei', 'WenQuanYi Micro Hei', 'Droid Sans Fallback']
        
    # Add generic fallbacks
    font_candidates.extend(['sans-serif'])

    # Find first available font
    available_fonts = set(f.name for f in fm.fontManager.ttflist)
    selected_font = None
    
    for font in font_candidates:
        if font in available_fonts:
            selected_font = font
            break
            
    if not selected_font:
        # Check by filename if name match fails
        # This is expensive, so maybe just trust matplotlib's fallback or try setting family
        pass

    if selected_font:
        plt.rcParams['font.sans-serif'] = [selected_font] + plt.rcParams['font.sans-serif']
    
    plt.rcParams['axes.unicode_minus'] = False # Fix minus sign

_configure_fonts()

def _detect_theme(style_config: Dict) -> str:
    """Detect theme from style config description."""
    desc = style_config.get('description', '').lower()
    if any(k in desc for k in ["tech", "cyber", "future", "dark"]):
        return "tech"
    if any(k in desc for k in ["minimal", "clean", "swiss", "flat"]):
        return "minimal"
    return "modern_card"


def _hex_luminance(hex_color: str) -> float:
    """相对亮度 0–1，用于对比度判断。>0.5 视为浅色。"""
    h = str(hex_color).lstrip("#")
    if len(h) < 6:
        return 0.5
    r, g, b = int(h[0:2], 16) / 255, int(h[2:4], 16) / 255, int(h[4:6], 16) / 255
    return 0.299 * r + 0.587 * g + 0.114 * b


def _get_chart_params(style_config: Dict, theme: str) -> Dict:
    """
    从 style_config 和 theme 推导图表样式，保证投影可读。
    安全下限：刻度 >= 12pt，图例 >= 14pt，避免「完全看不清」。
    """
    palette = style_config.get("palette", [])
    desc = (style_config.get("description") or "").lower()

    # 1. 字号：按风格微调，但不低于安全下限
    base_tick, base_legend = 13, 15
    if theme == "minimal":
        base_tick, base_legend = 12, 14
    elif theme == "tech":
        base_tick, base_legend = 14, 16
    if any(k in desc for k in ["bold", "large", "presentation"]):
        base_tick, base_legend = max(base_tick, 14), max(base_legend, 16)

    tick_fontsize = max(12, style_config.get("chart_tick_font", base_tick))
    legend_fontsize = max(14, style_config.get("chart_legend_font", base_legend))
    pie_label_fontsize = max(12, min(tick_fontsize + 1, 16))

    # 2. DPI：高分辨率风格略提，但不超出合理范围
    base_dpi = 120 if theme == "minimal" else 130
    dpi = max(100, min(150, style_config.get("chart_dpi", base_dpi)))

    # 3. 线宽 / 柱子：tech 更粗，minimal 稍细
    line_width = 3 if theme == "tech" else (2.5 if theme == "minimal" else 3)
    markersize = 11 if theme == "tech" else (9 if theme == "minimal" else 10)
    bar_edge_width = 1.5 if theme == "tech" else 1.0

    # 4. 柱边颜色：深色背景用亮边，浅色用白边，保证可见
    is_dark = theme == "tech" or (
        palette and len(palette) > 0 and _hex_luminance(palette[0]) < 0.4
    )
    bar_edge_color = "rgba(255,255,255,0.65)" if is_dark else "white"

    return {
        "tick_fontsize": tick_fontsize,
        "legend_fontsize": legend_fontsize,
        "pie_label_fontsize": pie_label_fontsize,
        "dpi": dpi,
        "line_width": line_width,
        "markersize": markersize,
        "bar_edge_width": bar_edge_width,
        "bar_edge_color": bar_edge_color,
    }

def _draw_theme_background(base_image: Image.Image, output_size: Tuple[int, int], theme: str, style_config: Dict) -> Image.Image:
    """
    Draw theme-specific background overlay (Card, Tech container, etc.).
    Returns the image with the theme background drawn.
    """
    from PIL import ImageDraw
    
    w, h = output_size
    # Container dimensions: 90% width, 75% height, centered
    card_w = int(w * 0.9)
    card_h = int(h * 0.75) 
    x = (w - card_w) // 2
    y = int(h * 0.15) # Start lower to leave room for headline
    
    # Create overlay for transparency
    overlay = Image.new('RGBA', output_size, (0,0,0,0))
    draw = ImageDraw.Draw(overlay)
    
    if theme == "tech":
        # Tech: Darker overlay, cut corners (chamfered), tech border
        cut = 40
        # Check if we have enough space for the cut
        if cut > card_w // 2 or cut > card_h // 2:
            cut = min(card_w // 4, card_h // 4)

        points = [
            (x + cut, y), (x + card_w - cut, y),
            (x + card_w, y + cut), (x + card_w, y + card_h - cut),
            (x + card_w - cut, y + card_h), (x + cut, y + card_h),
            (x, y + card_h - cut), (x, y + cut)
        ]
        
        # Dark tech overlay
        draw.polygon(points, fill=(20, 30, 40, 230))
        
        # Tech border
        palette = style_config.get("palette", [])
        # Try to find a bright color in palette or default to cyan
        border_color = "#00ffff"
        if len(palette) > 1:
            border_color = palette[1]
        
        draw.polygon(points, outline=border_color, width=3)
        
    elif theme == "minimal":
        # Minimal: No heavy overlay.
        # Just drawing nothing to keep it clean, or maybe a very subtle separator?
        # Prompt says: "Draw nothing (transparent) OR very subtle divider lines"
        # We'll leave it transparent to let the base background show through.
        pass
        
    else:
        # modern_card (Default)
        # White with 90% opacity (230)
        draw.rounded_rectangle([x, y, x+card_w, y+card_h], radius=20, fill=(255, 255, 255, 230))
    
    # Composite
    base_image = base_image.convert("RGBA")
    out = Image.alpha_composite(base_image, overlay)
    return out.convert("RGB")

def _ensure_readable_colors(
    text_color: str, grid_color: str, theme: str, style_config: Dict
) -> Tuple[str, str]:
    """
    对比度安全：深色背景下强制浅色文字，避免「看不清」。
    """
    palette = style_config.get("palette", [])
    bg_lum = _hex_luminance(palette[0]) if palette else 0.9
    # tech 主题的卡片是深色，minimal 可能透明透出底层
    effective_dark = theme == "tech" or (theme == "minimal" and bg_lum < 0.4)
    if effective_dark:
        return "#e8e8e8", "#444444"
    if bg_lum < 0.35:
        return "#e8e8e8", "#444444"
    return text_color, grid_color


def _prepare_background(output_size: Tuple[int, int], 
                       style_config: Dict, 
                       background_image: Optional[Image.Image] = None) -> Image.Image:
    """Prepare the background image (resized/cropped or solid color)."""
    palette = style_config.get("palette", ["#ffffff", "#000000"])
    bg_color = palette[0] if len(palette) > 0 else "#ffffff"

    if background_image:
        # Resize and crop to fill output_size
        bg = ImageOps.fit(background_image, output_size, method=Image.LANCZOS)
        return bg.convert("RGB")
    else:
        return Image.new('RGB', output_size, bg_color)

def render_table_image(table_data: Dict, style_config: Dict, 
                       output_size: Tuple[int, int] = (1920, 1080),
                       background_image: Optional[Image.Image] = None) -> Image.Image:
    """
    Render table from table_data as PNG with modern aesthetics and background integration.
    table_data: {"headers": [...], "rows": [[...], ...]}
    """
    dpi = 100
    figsize = (output_size[0] / dpi, output_size[1] / dpi)
    
    # Create figure with transparent background
    fig, ax = plt.subplots(figsize=figsize, dpi=dpi)
    fig.patch.set_alpha(0.0)
    ax.patch.set_alpha(0.0)
    ax.axis('off')
    
    # Extract data
    headers = table_data.get("headers", [])
    rows = table_data.get("rows", [])
    
    theme = _detect_theme(style_config)
    
    # Prepare background image with Theme
    base_bg = _prepare_background(output_size, style_config, background_image)
    final_bg = _draw_theme_background(base_bg, output_size, theme, style_config)
    
    if not rows:
        plt.close(fig)
        return final_bg

    # Create table
    # Just render the table centered in the figure
    
    # Calculate colors based on theme
    palette = style_config.get("palette", ["#ffffff", "#000000", "#4e79a7"])
    
    if theme == "tech":
        header_bg = "#000000"
        header_text = palette[1] if len(palette) > 1 else "#00ff00" # Use highlight color
        row_bg_odd = "#111111"
        row_bg_even = "#222222"
        text_color = "#e0e0e0"
        border_color = "#444444"
    elif theme == "minimal":
        header_bg = "none" # Transparent headers
        header_text = "#000000"
        row_bg_odd = "#ffffff"
        row_bg_even = "#ffffff" # White rows
        text_color = "#000000"
        border_color = "#000000" # Strong lines
    else:
        # Modern Card
        header_bg = palette[2] if len(palette) > 2 else "#333333"
        header_text = "#ffffff"
        row_bg_odd = "#ffffff"
        row_bg_even = "#f8f9fa" # Very light grey
        text_color = "#333333"
        border_color = "#e0e0e0"

    table = ax.table(cellText=rows, colLabels=headers, loc='center', cellLoc='center',
                     edges='horizontal') 
    
    # Style table
    table.auto_set_font_size(False)
    table.set_fontsize(18) # Larger font
    
    # Iterate cells to style
    for (row, col), cell in table.get_celld().items():
        cell.set_height(0.1) # Increase row height/padding
        
        cell.set_edgecolor(border_color)
        cell.set_linewidth(1)
        
        if theme == "minimal":
             # Stronger lines for minimal
            cell.set_linewidth(2)
        
        if row == 0:  # Header
            if theme == "minimal":
                 cell.set_text_props(weight='bold', color=header_text, size=24)
                 cell.set_facecolor("none")
                 # Minimal headers might need a bottom border
                 cell.set_linewidth(3)
            else:
                cell.set_facecolor(header_bg)
                cell.set_text_props(weight='bold', color=header_text, size=24)
        else:
            # Body
            bg = row_bg_odd if row % 2 != 0 else row_bg_even
            
            if theme == "minimal":
                 cell.set_facecolor("none") # Let background show or white
            else:
                 cell.set_facecolor(bg)
                 
            cell.set_text_props(color=text_color)
            
    # Render to buffer
    buf = io.BytesIO()
    plt.savefig(buf, format='png', bbox_inches='tight', pad_inches=0.1, transparent=True, dpi=dpi)
    plt.close(fig)
    buf.seek(0)
    
    table_img = Image.open(buf)
    
    # Paste table onto card area
    w, h = table_img.size
    
    # Resize if too big for card
    card_w = int(output_size[0] * 0.9)
    card_h = int(output_size[1] * 0.75)
    
    if w > card_w * 0.9 or h > card_h * 0.9: 
        # Add some padding inside card (0.9 factor)
        table_img.thumbnail((int(card_w * 0.9), int(card_h * 0.9)), Image.LANCZOS)
        w, h = table_img.size
    
    # Center on card
    card_center_x = output_size[0] // 2
    card_center_y = int(output_size[1] * (0.15 + 0.75/2))
    
    x = card_center_x - w // 2
    y = card_center_y - h // 2
    
    final_bg.paste(table_img, (x, y), mask=table_img)
    
    return final_bg

def render_chart_image(table_data: Dict, chart_type: str, style_config: Dict, 
                       output_size: Tuple[int, int] = (1920, 1080),
                       background_image: Optional[Image.Image] = None) -> Image.Image:
    """
    Render chart from table_data as PNG with modern aesthetics and background integration.
    chart_type: "bar" | "line" | "pie"
    样式由 style_config + theme 推导，保证对比度可读。
    """
    theme = _detect_theme(style_config)
    params = _get_chart_params(style_config, theme)
    dpi = params["dpi"]
    figsize = (output_size[0] / dpi, output_size[1] / dpi)

    # Create figure with transparent background
    fig, ax = plt.subplots(figsize=figsize, dpi=dpi)
    fig.patch.set_alpha(0.0)
    ax.patch.set_alpha(0.0)
    
    # Prepare background image with Theme
    base_bg = _prepare_background(output_size, style_config, background_image)
    final_bg = _draw_theme_background(base_bg, output_size, theme, style_config)
    
    # Extract data
    headers = table_data.get("headers", [])
    rows = table_data.get("rows", [])
    
    if not rows:
        plt.close(fig)
        return final_bg

    # Assume first column is label (X-axis or Pie labels)
    labels = [str(row[0]) for row in rows] # Ensure strings
    
    # Try to convert other columns to numbers
    values_list = []
    
    for col_idx in range(1, len(rows[0])):
        try:
            col_values = [float(row[col_idx]) for row in rows]
            values_list.append(col_values)
        except ValueError:
            values_list.append([0.0] * len(rows))
            
    palette = style_config.get("palette", ["#ffffff", "#000000"])
    data_colors = palette[2:] if len(palette) > 2 else ["#4e79a7", "#f28e2c", "#e15759", "#76b7b2", "#59a14f"]
    
    # Theme specific text color，再经对比度安全校验
    if theme == "tech":
        text_color, grid_color = "#e0e0e0", "#333333"
    elif theme == "minimal":
        text_color, grid_color = "#000000", "#cccccc"
    else:
        text_color, grid_color = "#333333", "#333333"
    text_color, grid_color = _ensure_readable_colors(text_color, grid_color, theme, style_config)

    tick_fontsize = params["tick_fontsize"]
    legend_fontsize = params["legend_fontsize"]
    pie_label_fontsize = params["pie_label_fontsize"]

    # Remove the "Card" effect from Matplotlib since we drew it with PIL
    # Just style the axes to be clean and transparent
    
    # Remove spines
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    ax.spines['left'].set_color(text_color)
    ax.spines['bottom'].set_color(text_color)
    ax.set_facecolor('none') # Transparent
    
    # Grid
    if theme == "minimal":
        # Minimal: No grid or very subtle
        ax.grid(False)
    else:
        ax.grid(True, axis='y', linestyle='--', alpha=0.35, color=grid_color)

    ax.tick_params(axis='both', colors=text_color, labelsize=tick_fontsize)
    ax.xaxis.label.set_color(text_color)
    ax.yaxis.label.set_color(text_color)
    if ax.get_title():
        ax.title.set_color(text_color)

    if chart_type == "bar":
        x = range(len(labels))
        width = min(0.65, 0.75 / max(len(values_list), 1))
        
        for i, values in enumerate(values_list):
            color = data_colors[i % len(data_colors)]
            offset = (i - len(values_list)/2) * width + width/2 if len(values_list) > 1 else 0
            
            bar_x = [pos + offset for pos in x] if len(values_list) > 1 else x
            
            label_text = headers[i+1] if i+1 < len(headers) else f"Series {i+1}"
            ax.bar(bar_x, values, width=width, label=label_text, color=color, alpha=0.92,
                   edgecolor=params["bar_edge_color"], linewidth=params["bar_edge_width"])
        
        ax.set_xticks(x)
        ax.set_xticklabels(labels, rotation=40, ha='right', fontsize=tick_fontsize)
        
        if headers and len(headers) > 1 and len(values_list) > 1:
            legend = ax.legend(frameon=False, loc='upper center', bbox_to_anchor=(0.5, 1.12), ncol=len(values_list),
                               fontsize=legend_fontsize)
            for text in legend.get_texts():
                text.set_color(text_color)
            
    elif chart_type == "line":
        for i, values in enumerate(values_list):
            color = data_colors[i % len(data_colors)]
            label_text = headers[i+1] if i+1 < len(headers) else f"Series {i+1}"
            ax.plot(labels, values, marker='o', label=label_text, color=color,
                    linewidth=params["line_width"], markersize=params["markersize"])
        
        plt.xticks(rotation=40, ha='right')
        ax.tick_params(axis='x', labelsize=tick_fontsize)
        
        if headers and len(headers) > 1 and len(values_list) > 1:
            legend = ax.legend(frameon=False, loc='upper center', bbox_to_anchor=(0.5, 1.12), ncol=len(values_list),
                               fontsize=legend_fontsize)
            for text in legend.get_texts():
                text.set_color(text_color)
            
    elif chart_type == "pie":
        # Pie usually takes one series.
        if values_list:
            values = values_list[0]
            colors = [data_colors[i % len(data_colors)] for i in range(len(values))]
            
            wedges, texts, autotexts = ax.pie(values, labels=labels, autopct='%1.1f%%', 
                                              startangle=90, colors=colors,
                                              textprops={'color': text_color, 'fontsize': pie_label_fontsize})
            
            for autotext in autotexts:
                autotext.set_color("white")
                autotext.set_weight('bold')
                autotext.set_fontsize(max(11, pie_label_fontsize - 1))
            for t in texts:
                t.set_fontsize(pie_label_fontsize)
                
            ax.axis('equal')
            
    # Save and Process
    plt.tight_layout(pad=1.2)
    buf = io.BytesIO()
    plt.savefig(buf, format='png', bbox_inches='tight', pad_inches=0.15, transparent=True, dpi=dpi)
    plt.close(fig)
    buf.seek(0)
    
    chart_img = Image.open(buf)
    
    # Resize logic to fit centered in CARD
    w, h = chart_img.size
    
    # Resize if chart is too big for card area
    card_w = int(output_size[0] * 0.9)
    card_h = int(output_size[1] * 0.75)
    
    if w > card_w * 0.9 or h > card_h * 0.9:
        chart_img.thumbnail((int(card_w * 0.9), int(card_h * 0.9)), Image.LANCZOS)
        w, h = chart_img.size
        
    # Center on CARD
    card_center_x = output_size[0] // 2
    card_center_y = int(output_size[1] * (0.15 + 0.75/2))
    
    x = card_center_x - w // 2
    y = card_center_y - h // 2
    
    final_bg.paste(chart_img, (x, y), mask=chart_img)
    
    return final_bg
