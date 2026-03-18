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