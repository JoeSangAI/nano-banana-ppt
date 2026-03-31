# Nano Banana PPT Logo Enhancement Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Implement logo-based color extraction for AI Minting and dynamic, unified scaling for logo insertion in PPT slides.

**Architecture:** We will create an image utility to extract dominant colors from the user's logo using Pillow. These colors will be passed as constraints to `VisualAgent.define_style()` when no template is provided. Finally, we will update `generator.py` to calculate a unified scaled size for the logo based on its aspect ratio within a fixed bounding box, ensuring consistent rendering across all slides.

**Tech Stack:** Python, Pillow, `python-pptx`

---

### Task 1: Create Image Utilities

**Files:**
- Create: `tools/nano_banana_ppt/utils/image_utils.py`

**Step 1: Implement `extract_dominant_colors`**

```python
from PIL import Image

def extract_dominant_colors(image_path: str, num_colors: int = 3) -> list:
    """Extract dominant hex colors from an image using Pillow's quantize."""
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
```

**Step 2: Commit**

```bash
git add tools/nano_banana_ppt/utils/image_utils.py
git commit -m "feat: add logo color extraction utility"
```

### Task 2: Inject Logo Colors into AI Minting

**Files:**
- Modify: `tools/nano_banana_ppt/main.py`
- Modify: `tools/nano_banana_ppt/agents/visual.py`

**Step 1: Extract colors in `main.py`**

In `main.py`, around line 176 (where the logo is checked and added to `assets`), add the following:

```python
    # After: elif logo_file: logger.warning(...)
    
    # If we have a logo but no template, extract brand colors
    brand_colors = []
    if assets.get('logo_path') and not template_info:
        from tools.nano_banana_ppt.utils.image_utils import extract_dominant_colors
        print("\n🎨 正在从 Logo 提取品牌色...")
        brand_colors = extract_dominant_colors(assets['logo_path'], num_colors=3)
        if brand_colors:
            print(f"   提取到的品牌色: {', '.join(brand_colors)}")
```

And update the `constraints` dictionary right below it:

```python
    constraints = {
        "target_audience": inferred.get("target_audience", "通用受众"),
        "presentation_type": inferred.get("presentation_type", "商业演示"),
        "duration": inferred.get("duration", "15分钟"),
        "page_count": str(page_count) if page_count else "10",
        "style_preference": style_preference or inferred.get("style_preference", "专业商务"),
        "briefing": briefing,
        "brand_colors": brand_colors, # ADD THIS LINE
    }
```

**Step 2: Update prompt in `visual.py`**

In `tools/nano_banana_ppt/agents/visual.py`, locate `def define_style(self, constraints: Dict, assets: Dict = None, template_info: Dict = None) -> tuple:`

Modify the prompt formulation to include brand colors (around line 87):

```python
        brand_colors = constraints.get('brand_colors', [])
        brand_color_text = f"- Brand Colors (Extracted from Logo): {', '.join(brand_colors)}\nIf Brand Colors are provided, USE THEM as the primary inspiration for the palette, ensuring high contrast for text reading." if brand_colors else ""

        prompt = f"""You are a world-class Art Director. Define a cohesive visual style guide for a presentation.

【Context】
- Topic: {topic}
- Audience: {audience}
- User Preference Vibe: "{user_preference}"
{brand_color_text}

【Task】
If User Preference is vague, default to a **"Modern Professional Business"** style...
```

**Step 3: Commit**

```bash
git add tools/nano_banana_ppt/main.py tools/nano_banana_ppt/agents/visual.py
git commit -m "feat: inject extracted logo colors into visual agent for ai minting"
```

### Task 3: Implement Dynamic Logo Scaling

**Files:**
- Modify: `tools/nano_banana_ppt/core/generator.py`

**Step 1: Update Logo Insertion Logic**

In `tools/nano_banana_ppt/core/generator.py`, around line 812, locate the logo insertion block:

```python
            logo_path = slide_plan.get('logo_path')
            # ...
            if logo_path and os.path.exists(logo_path) and page_type != 'background_only':
                logo_loc = (slide_plan.get('logo_location') or 'Top-Right').lower()
                # OLD: logo_h = Inches(0.45)
```

Replace the sizing and placement logic with a bounding-box approach:

```python
            logo_path = slide_plan.get('logo_path')
            # Only add logo if it exists and it's not a pure background slide
            if logo_path and os.path.exists(logo_path) and page_type != 'background_only':
                logo_loc = (slide_plan.get('logo_location') or 'Top-Right').lower()
                
                # Define bounding box for logo
                max_logo_w = Inches(1.8)
                max_logo_h = Inches(0.65)
                
                try:
                    from PIL import Image as PILImage
                    _logo = PILImage.open(logo_path)
                    logo_aspect = _logo.width / _logo.height
                    
                    # Calculate dimensions preserving aspect ratio within bounding box
                    # First try setting width to max
                    calc_w = max_logo_w
                    calc_h = calc_w / logo_aspect
                    
                    # If height exceeds max_height, scale down based on height instead
                    if calc_h > max_logo_h:
                        calc_h = max_logo_h
                        calc_w = calc_h * logo_aspect
                        
                    logo_w = calc_w
                    logo_h = calc_h
                except Exception as e:
                    logger.warning(f"Failed to read logo for aspect ratio: {e}")
                    logo_w = Inches(1.2)
                    logo_h = Inches(0.45)
                
                # Default margin
                margin_x = Inches(0.5)
                margin_y = Inches(0.4)
                
                # Calculate coordinates
                if 'left' in logo_loc and 'top' in logo_loc:
                    lx, ly = margin_x, margin_y
                elif 'right' in logo_loc and 'bottom' in logo_loc:
                    lx = prs.slide_width - logo_w - margin_x
                    ly = prs.slide_height - logo_h - margin_y
                elif 'left' in logo_loc and 'bottom' in logo_loc:
                    lx, ly = margin_x, prs.slide_height - logo_h - margin_y
                else: # Default Top-Right
                    lx = prs.slide_width - logo_w - margin_x
                    ly = margin_y
                
                slide.shapes.add_picture(logo_path, lx, ly, logo_w, logo_h)
```

**Step 2: Check formatting and import**

Ensure `PILImage` is imported safely inside the block or globally (it looks like `from PIL import Image as PILImage` is already used in `generator.py` locally around that block based on the grep).

**Step 3: Commit**

```bash
git add tools/nano_banana_ppt/core/generator.py
git commit -m "feat: implement dynamic scaling and unified sizing for logos"
```

---
