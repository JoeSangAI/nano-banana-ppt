# Native Image Layout Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Allow users to insert original, unaltered images into generated PPTs at predefined layout positions while instructing the AI background generator to leave those areas blank/clean.

**Architecture:** We will extend the slide JSON plan to support a `native_image` object. `PPTGenerator.generate_image` will dynamically append whitespace instructions to the prompt based on the layout. `create_advanced_pptx` will calculate coordinates based on the layout and use `python-pptx` to insert the unaltered image on top of the background.

**Tech Stack:** Python, `python-pptx`, `PIL` (Pillow)

---

### Task 1: Update Prompt Injection for Smart Whitespace (Generator)

**Files:**
- Modify: `tools/nano_banana_ppt/core/generator.py`

**Step 1: Modify `PPTGenerator.generate_image` to accept layout hints**

Add a `native_layout` parameter (default `None`) to `generate_image`. Based on this parameter, append specific instructions to `full_prompt`.

```python
    def generate_image(self, description: str, aspect_ratio: str = "16:9", reference_images: List[Image.Image] = None, is_background_only: bool = False, resolution: str = "1K", native_layout: str = None) -> Image.Image:
        # ... existing code ...
        
        tech_suffix = f"\n\nTechnical: aspect ratio {aspect_ratio}, {resolution} resolution, sharp text rendering. CRITICAL: No black blocks, no solid black rectangles, seamless full-bleed composition."
        
        # Inject smart whitespace instructions based on native_layout
        if native_layout:
            layout_prompts = {
                "right_half": "CRITICAL: The right half of the image MUST be left extremely clean, empty, or plain solid color to accommodate an overlaid photo.",
                "left_half": "CRITICAL: The left half of the image MUST be left extremely clean, empty, or plain solid color to accommodate an overlaid photo.",
                "center": "CRITICAL: The center area of the image MUST be left extremely clean, empty, or plain solid color to accommodate an overlaid photo.",
                "bottom_right": "CRITICAL: The bottom right corner of the image MUST be left extremely clean, empty, or plain solid color to accommodate an overlaid photo."
            }
            if native_layout in layout_prompts:
                tech_suffix += f" {layout_prompts[native_layout]}"

        full_prompt = description + tech_suffix
        # ... existing code ...
```

**Step 2: Commit changes**
```bash
git add tools/nano_banana_ppt/core/generator.py
git commit -m "feat: add smart whitespace prompt injection based on native layout"
```

---

### Task 2: Pass Layout to Generator from Executor

**Files:**
- Modify: `tools/nano_banana_ppt/core/executor.py`

**Step 1: Update `_generate_single_slide` to read and pass `native_layout`**

Read `native_image.layout` from the slide plan and pass it to `generate_image`.

```python
def _generate_single_slide(slide, visual_plan, slides_dir, generator, resolution, masters, clean_background_image=None):
    # ... existing code ...
    
    native_image_config = slide.get('native_image', {})
    native_layout = native_image_config.get('layout')
    
    # ... inside the try block for image generation ...
    image = generator.generate_image(
        prompt, aspect_ratio="16:9",
        reference_images=reference_images,
        is_background_only=is_background_only,
        resolution=resolution,
        native_layout=native_layout
    )
    # ... existing code ...
```

**Step 2: Commit changes**
```bash
git add tools/nano_banana_ppt/core/executor.py
git commit -m "feat: pass native_layout hint from executor to generator"
```

---

### Task 3: Implement Native Image Insertion in PPTX Export

**Files:**
- Modify: `tools/nano_banana_ppt/core/generator.py`

**Step 1: Add layout calculation logic to `create_advanced_pptx`**

In `create_advanced_pptx`, process the `native_image` block. Calculate coordinates based on the layout and insert the image using `slide.shapes.add_picture`. Make sure to handle aspect ratio scaling (fit within bounds).

```python
    def create_advanced_pptx(self, visual_plan: List[Dict], images: Dict[int, Image.Image], output_path: str, template_path: str = None) -> str:
        # ... existing code inside the loop ...
            
            # Add Logo ... (existing code)

            # --- NEW: Add Native Image ---
            native_image_config = slide_plan.get('native_image')
            if native_image_config:
                img_path = native_image_config.get('path')
                layout = native_image_config.get('layout', 'center')
                
                if img_path and os.path.exists(img_path):
                    try:
                        from PIL import Image as PILImage
                        native_img = PILImage.open(img_path)
                        img_w, img_h = native_img.size
                        aspect = img_w / img_h
                        
                        sw = prs.slide_width
                        sh = prs.slide_height
                        
                        margin = Inches(0.5)
                        
                        # Define target bounding box (left, top, max_width, max_height)
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
                        
                        # Calculate fitted dimensions preserving aspect ratio
                        target_aspect = max_w / max_h
                        if aspect > target_aspect:
                            # Image is wider than target box
                            final_w = max_w
                            final_h = max_w / aspect
                        else:
                            # Image is taller than target box
                            final_h = max_h
                            final_w = max_h * aspect
                            
                        # Center within the target box
                        final_l = target_l + (max_w - final_w) / 2
                        final_t = target_t + (max_h - final_h) / 2
                        
                        slide.shapes.add_picture(img_path, final_l, final_t, final_w, final_h)
                        logger.info(f"  Inserted native image at {layout} layout")
                    except Exception as e:
                        logger.warning(f"Failed to insert native image {img_path}: {e}")

            # 添加演讲者备注 (Speaker Notes) ... (existing code)
```

**Step 2: Commit changes**
```bash
git add tools/nano_banana_ppt/core/generator.py
git commit -m "feat: implement precise native image layout and insertion in PPTX"
```

---

### Task 4: Integration Test with the Corgi Image

**Files:**
- Create: `tools/nano_banana_ppt/test_native_image.py`

**Step 1: Write a test script**

Create a script that generates a 2-slide PPT. Slide 1 uses `right_half` layout with the Corgi image. Slide 2 uses `center` layout with the Corgi image.

```python
import os
import json
from pathlib import Path
from tools.nano_banana_ppt.core.executor import execute_plan

def test_native_image():
    corgi_path = os.path.abspath("output/images/20260214_corgi_in_landscape.png")
    
    plan = {
        "meta": {
            "title": "Corgi Native Image Test",
            "project_dir": "output/ppt/test_corgi"
        },
        "slides": [
            {
                "page_num": 1,
                "type": "content",
                "visual_prompt": "A beautiful traditional Chinese painting of a mountain landscape with misty peaks and a small temple. Wide angle, serene atmosphere.",
                "native_image": {
                    "path": corgi_path,
                    "layout": "right_half"
                }
            },
            {
                "page_num": 2,
                "type": "content",
                "visual_prompt": "A minimal zen garden background, soft lighting, lots of empty space.",
                "native_image": {
                    "path": corgi_path,
                    "layout": "center"
                }
            }
        ]
    }
    
    os.makedirs("output/ppt/test_corgi", exist_ok=True)
    plan_file = "output/ppt/test_corgi/plan.json"
    with open(plan_file, "w") as f:
        json.dump(plan, f, indent=2)
        
    print(f"Executing plan: {plan_file}")
    execute_plan(plan_file, output_name="Corgi_Test", project_dir="output/ppt/test_corgi")

if __name__ == "__main__":
    test_native_image()
```

**Step 2: Run the test**
```bash
python tools/nano_banana_ppt/test_native_image.py
```
Check the generated `.pptx` file to ensure the Corgi image is inserted correctly and the background is generated appropriately.

**Step 3: Commit test script**
```bash
git add tools/nano_banana_ppt/test_native_image.py
git commit -m "test: add integration test for native image layout feature"
```
