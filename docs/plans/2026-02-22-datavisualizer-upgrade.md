# DataVisualizer Upgrade Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development to implement this plan task-by-task.

**Goal:** Upgrade `DataVisualizer` to support background integration and modern aesthetics for tables and charts.

**Architecture:** 
-   Update `render_table_image` and `render_chart_image` to accept optional `background_image`.
-   Implement logic to resize/crop background and overlay a semi-transparent "card" for data readability.
-   Refactor Matplotlib styling for professional look (no vertical lines, custom fonts, clean charts).
-   Update `executor.py` to pass the master slide background.

**Tech Stack:** Python, Matplotlib, PIL.

---

### Task 1: Create Test Harness

**Files:**
-   Create: `tools/nano_banana_ppt/tests/test_visualizer_manual.py`

**Step 1: Create a manual test script**

Create a script that:
1.  Generates a dummy `background_image` (e.g., a gradient or noise).
2.  Defines sample `table_data` and `style_config`.
3.  Calls `render_table_image` and `render_chart_image` (old signature first, then updated).
4.  Saves output to `output/test_vis/`.

```python
import os
import sys
from PIL import Image, ImageDraw

# Ensure we can import from tools
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../..')))

from tools.nano_banana_ppt.core.data_visualizer import render_table_image, render_chart_image

def create_dummy_bg(size=(1920, 1080)):
    img = Image.new('RGB', size, (50, 50, 100))
    draw = ImageDraw.Draw(img)
    draw.line((0, 0) + size, fill=(200, 100, 100), width=10)
    return img

def test_rendering():
    os.makedirs("output/test_vis", exist_ok=True)
    
    table_data = {
        "headers": ["Metric", "Q1", "Q2", "Q3"],
        "rows": [
            ["Revenue", "100", "120", "140"],
            ["Cost", "80", "85", "90"],
            ["Profit", "20", "35", "50"]
        ]
    }
    style_config = {"palette": ["#ffffff", "#333333", "#007bff", "#28a745", "#dc3545"]}
    
    bg = create_dummy_bg()
    
    # Test Table (New Signature will be needed)
    # For now, this will fail if we pass bg, but we'll update the function in next task.
    # This step just sets up the test.
    print("Test harness created.")

if __name__ == "__main__":
    test_rendering()
```

**Step 2: Run verification**
`python3 tools/nano_banana_ppt/tests/test_visualizer_manual.py`

---

### Task 2: Upgrade `render_table_image`

**Files:**
-   Modify: `tools/nano_banana_ppt/core/data_visualizer.py`

**Step 1: Update signature and imports**

-   Import `ImageOps` from PIL.
-   Update `render_table_image` to accept `background_image: Optional[Image.Image] = None`.

**Step 2: Implement Background Processing**

-   Resize `background_image` to cover `output_size` (using `ImageOps.fit` or manual resizing logic).
-   Create a base image.

**Step 3: Implement Modern Table Styling**

-   Use `ax.table`.
-   Style headers with `palette[2]`, white text, bold.
-   Style rows with alternating colors (white / #f9f9f9).
-   Remove vertical cell borders.
-   Set font size to 18 (body) / 24 (header).
-   Use `bbox` or padding to center table.

**Step 4: Update Test Script**

-   Update `test_visualizer_manual.py` to pass `background_image` and verify output visually (check if file exists and dimensions are correct).

---

### Task 3: Upgrade `render_chart_image`

**Files:**
-   Modify: `tools/nano_banana_ppt/core/data_visualizer.py`

**Step 1: Update signature**

-   Update `render_chart_image` to accept `background_image`.

**Step 2: Implement Chart Styling**

-   Remove top/right spines.
-   Add horizontal grid.
-   Use semi-transparent background for axes (the "card").
-   Style legend.

**Step 3: Update Test Script**

-   Add chart rendering test with background.

---

### Task 4: Update Executor

**Files:**
-   Modify: `tools/nano_banana_ppt/core/executor.py`

**Step 1: Pass master slide**

-   In `_generate_single_slide`, pass `master_slide_image` to render functions.

**Step 2: Verify**

-   Run the test script again to ensure everything works together.
