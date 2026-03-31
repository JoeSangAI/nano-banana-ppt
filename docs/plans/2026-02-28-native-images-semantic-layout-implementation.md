# Native Images Semantic Layout Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Upgrade the existing single `native_image` layout logic to support a `native_images` list with semantic coordinate-based bounding boxes (`bounding_box` with `left`, `top`, `width`, `height` as floats 0.0-1.0).

**Architecture:** 
1. `generate_image` will parse the `native_images` array (and translate legacy `native_image`) and construct specific whitespace prompts based on relative coordinates.
2. `executor.py` will pass `native_images` to the generator instead of `native_layout`.
3. `create_advanced_pptx` will iterate over `native_images` to calculate physical absolute coordinates and insert multiple unaltered images per slide.

**Tech Stack:** Python, `python-pptx`, `PIL` (Pillow)

---

### Task 1: Refactor Prompt Injection for Multi-Region Smart Whitespace (Generator)

**Files:**
- Modify: `tools/nano_banana_ppt/core/generator.py`

**Step 1: Modify `PPTGenerator.generate_image` signature and logic**

Replace `native_layout: str = None` with `native_images: List[Dict] = None`. Iterate over the images to dynamically construct the whitespace constraints.

```python
    def generate_image(self, description: str, aspect_ratio: str = "16:9", reference_images: List[Image.Image] = None, is_background_only: bool = False, resolution: str = "1K", native_images: List[Dict] = None) -> Image.Image:
        # ... existing code ...
        
        tech_suffix = f"\n\nTechnical: aspect ratio {aspect_ratio}, {resolution} resolution, sharp text rendering. CRITICAL: No black blocks, no solid black rectangles, seamless full-bleed composition."
        
        # Inject smart whitespace instructions based on native_images array
        if native_images and len(native_images) > 0:
            areas = []
            for idx, img_conf in enumerate(native_images):
                layout = img_conf.get('layout')
                bbox = img_conf.get('bounding_box')
                
                if bbox:
                    # Translate bounding box to natural language roughly
                    left_pct = int(bbox.get('left', 0) * 100)
                    top_pct = int(bbox.get('top', 0) * 100)
                    w_pct = int(bbox.get('width', 0) * 100)
                    h_pct = int(bbox.get('height', 0) * 100)
                    areas.append(f"Area {idx+1}: starting at {left_pct}% from left and {top_pct}% from top, covering {w_pct}% width and {h_pct}% height")
                elif layout:
                    # Legacy fallback
                    layout_prompts = {
                        "right_half": "The right half of the image",
                        "left_half": "The left half of the image",
                        "center": "The center area of the image",
                        "bottom_right": "The bottom right corner of the image"
                    }
                    if layout in layout_prompts:
                        areas.append(layout_prompts[layout])
            
            if areas:
                areas_str = ", ".join(areas)
                tech_suffix += f" CRITICAL: The following areas MUST be left extremely clean, empty, or plain solid color to accommodate overlaid photos: {areas_str}."

        full_prompt = description + tech_suffix
        # ... existing code ...
```

**Step 2: Commit changes**
```bash
git add tools/nano_banana_ppt/core/generator.py
git commit -m "feat: upgrade prompt injection to support multi-region bounding boxes for smart whitespace"
```

---

### Task 2: Pass Array to Generator from Executor

**Files:**
- Modify: `tools/nano_banana_ppt/core/executor.py`

**Step 1: Update `_generate_single_slide` to read and pass `native_images`**

Read `native_images` list, or fallback to wrapping the legacy `native_image` object into a list.

```python
def _generate_single_slide(slide, visual_plan, slides_dir, generator, resolution, masters, clean_background_image=None):
    # ... existing code ...
    
    native_images = slide.get('native_images', [])
    # Legacy fallback mapping
    if not native_images and slide.get('native_image'):
        native_images = [slide.get('native_image')]
    
    image = generator.generate_image(
        prompt, aspect_ratio="16:9",
        reference_images=reference_images,
        is_background_only=is_background_only,
        resolution=resolution,
        native_images=native_images
    )
    # ... existing code ...
```

**Step 2: Commit changes**
```bash
git add tools/nano_banana_ppt/core/executor.py
git commit -m "feat: pass native_images array from executor to generator for multi-image layout"
```

---

### Task 3: Implement Multi-Image Bounding Box Insertion in PPTX Export

**Files:**
- Modify: `tools/nano_banana_ppt/core/generator.py`

**Step 1: Update layout calculation logic in `create_advanced_pptx`**

Iterate over the `native_images` array. Support both legacy `layout` enum and the new `bounding_box` relative coordinates.

```python
    def create_advanced_pptx(self, visual_plan: List[Dict], images: Dict[int, Image.Image], output_path: str, template_path: str = None) -> str:
        # ... existing code inside the loop ...
            
            # Add Logo ... (existing code)

            # --- NEW: Add Multiple Native Images ---
            native_images = slide_plan.get('native_images', [])
            if not native_images and slide_plan.get('native_image'):
                native_images = [slide_plan.get('native_image')]

            for img_conf in native_images:
                img_path = img_conf.get('path')
                if not img_path or not os.path.exists(img_path):
                    continue
                    
                layout = img_conf.get('layout', 'center')
                bbox = img_conf.get('bounding_box')
                
                try:
                    from PIL import Image as PILImage
                    native_img = PILImage.open(img_path)
                    img_w, img_h = native_img.size
                    aspect = img_w / img_h
                    
                    sw = prs.slide_width
                    sh = prs.slide_height
                    
                    margin = Inches(0.5)
                    
                    # 1. Resolve target bounding box (left, top, max_width, max_height)
                    if bbox:
                        # Semantic coordinate system (0.0 - 1.0)
                        target_l = sw * bbox.get('left', 0)
                        target_t = sh * bbox.get('top', 0)
                        max_w = sw * bbox.get('width', 1.0)
                        max_h = sh * bbox.get('height', 1.0)
                    else:
                        # Legacy enum system
                        if layout == 'right_half':
                            box = (sw / 2 + margin/2, margin, sw / 2 - margin*1.5, sh - margin*2)
                        elif layout == 'left_half':
                            box = (margin, margin, sw / 2 - margin*1.5, sh - margin*2)
                        elif layout == 'bottom_right':
                            box = (sw * 0.6, sh * 0.5, sw * 0.4 - margin, sh * 0.5 - margin)
                        elif layout == 'fullscreen':
                            box = (0, 0, sw, sh)
                        else: # center
                            box = (margin*2, margin*2, sw - margin*4, sh - margin*4)
                        target_l, target_t, max_w, max_h = box
                        
                    # 2. Calculate fitted dimensions preserving aspect ratio
                    if max_h == 0: max_h = 1 # prevent div by zero
                    target_aspect = max_w / max_h
                    if aspect > target_aspect:
                        # Image is wider than target box
                        final_w = max_w
                        final_h = max_w / aspect
                    else:
                        # Image is taller than target box
                        final_h = max_h
                        final_w = max_h * aspect
                        
                    # 3. Center within the target box
                    final_l = target_l + (max_w - final_w) / 2
                    final_t = target_t + (max_h - final_h) / 2
                    
                    slide.shapes.add_picture(img_path, final_l, final_t, final_w, final_h)
                    logger.info(f"  Inserted native image at {bbox if bbox else layout}")
                except Exception as e:
                    logger.warning(f"Failed to insert native image {img_path}: {e}")

            # 添加演讲者备注 (Speaker Notes) ... (existing code)
```

**Step 2: Commit changes**
```bash
git add tools/nano_banana_ppt/core/generator.py
git commit -m "feat: implement precise multi-image bounding box layout engine in PPTX export"
```

---

### Task 4: Integration Test with Multiple Images

**Files:**
- Modify: `tools/nano_banana_ppt/test_native_image.py`

**Step 1: Rewrite test script for semantic layout**

Generate a 1-slide PPT that uses `bounding_box` to place two pictures side by side (semantic comparison).

```python
import os
import json
from pathlib import Path
from tools.nano_banana_ppt.core.executor import execute_plan

def test_native_image():
    corgi_path = os.path.abspath("output/images/20260214_corgi_in_landscape.png")
    landscape_path = os.path.abspath("output/images/20260214_chinese_landscape_v2.png")
    
    plan = {
        "meta": {
            "title": "Multi-Image Semantic Layout Test",
            "project_dir": "output/ppt/test_semantic_layout"
        },
        "slides": [
            {
                "page_num": 1,
                "type": "content",
                "visual_prompt": "A minimalist tech comparison background. The left area and right area should be clean. A futuristic divider in the middle.",
                "native_images": [
                    {
                        "path": landscape_path,
                        "semantic_role": "Old generation product, shown on the left",
                        "bounding_box": { "left": 0.05, "top": 0.2, "width": 0.4, "height": 0.6 }
                    },
                    {
                        "path": corgi_path,
                        "semantic_role": "New generation product, shown on the right",
                        "bounding_box": { "left": 0.55, "top": 0.2, "width": 0.4, "height": 0.6 }
                    }
                ]
            }
        ]
    }
    
    os.makedirs("output/ppt/test_semantic_layout", exist_ok=True)
    plan_file = "output/ppt/test_semantic_layout/plan.json"
    with open(plan_file, "w") as f:
        json.dump(plan, f, indent=2)
        
    print(f"Executing plan: {plan_file}")
    execute_plan(plan_file, output_name="Semantic_Test", project_dir="output/ppt/test_semantic_layout")

if __name__ == "__main__":
    test_native_image()
```

**Step 2: Run the test**
```bash
export PYTHONPATH=$PWD
python tools/nano_banana_ppt/test_native_image.py
```

**Step 3: Commit test script**
```bash
git add tools/nano_banana_ppt/test_native_image.py
git commit -m "test: upgrade integration test for semantic multi-image layout feature"
```