# Remove Native Tables Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Completely remove native PowerPoint table insertion, forcing the pipeline to use visual/text layouts or native charts instead, ensuring 100% aesthetic consistency.

**Architecture:** We are modifying the prompt logic in `agents/narrative.py`, cleaning up legacy layout matching in `agents/visual.py` and `utils/review_plan.py`, and stripping out all table-rendering code from `core/executor.py`, `core/data_visualizer.py`, and `core/generator.py`.

**Tech Stack:** Python, PPTX, Prompts

---

### Task 1: Update Narrative Agent Prompt

**Files:**
- Modify: `tools/nano_banana_ppt/agents/narrative.py`

**Step 1: Modify the instruction prompt**
Update `_get_system_prompt` inside `agents/narrative.py` to strictly ban native tables and explain how to reconstruct them.

```python
# Replace the current rule:
# - **严禁使用原生表格排版文字 (NO TABLES)**：极度丑陋！遇到原文中的文字或对比表格时，必须将其重塑为 `comparison` (双列对比)、`framework` (逻辑结构) 或 `bullets` (极简要点)。将核心内容提炼后放入 `body` 数组中，交给文字引擎进行优美的图文混排。
# - **纯数值数据图表化**：如果原文表格全是硬核数值（趋势/比例/份额），请提取为一页 `data` 类型，并在 `text_content` 中增加 `table_data` 字段，同时 `visualization` 必须指定为 `bar`、`line` 或 `pie`。**绝对禁止指定 visualization 为 table 或 auto！**

# With:
   - **全面弃用原生表格 (NO NATIVE TABLES)**：本系统不再支持原生PPT表格。遇到原文中的表格时：
     1. **纯数值表格**：若全是硬核数值（趋势/比例/份额），请提取为一页 `data` 类型，在 `text_content` 中增加 `table_data` 字段，且 `visualization` 必须指定为 `bar`、`line` 或 `pie`。
     2. **文字型表格/对比**：必须重构为普通的文字排版（如 `comparison` 双列对比、`framework` 逻辑结构 或 `bullets` 极简要点），将核心内容提炼放入 `body` 数组中。
     3. **极度复杂的巨型表格（如报价单）**：如果表格过于复杂无法简化，将其处理为一页包含总结性文字的 `content` 页面，并在 `speaker_notes` 中明确提示：“【重要】原文此处包含复杂表格，建议演讲者后续截图手动粘贴至本页”。
     **绝对禁止使用 type 为 table 或 visualization 为 table/auto！**
```

Update JSON format definitions in the prompt:
```python
# Remove table from type definition
    "type": "cover|section|content|hero|breathing|data|flowchart|framework|comparison|ending", 

# Update visualization definition
    "visualization": "bar/line/pie (仅在纯数值图表时填写，严禁使用table或auto)",
```

**Step 2: Remove Markdown table extraction method**
Remove `extract_markdown_tables` function from `NarrativeAgent` class.
Also remove `table` from the `type` check in `_print_plan_preview` around line 436: `elif page.get('type') in ['content', 'data'] and text_content.get('body'):`

**Step 3: Commit**
```bash
git add tools/nano_banana_ppt/agents/narrative.py
git commit -m "refactor(narrative): ban native tables in prompts and remove table extraction"
```

---

### Task 2: Clean up Visual Agent and Review Plan

**Files:**
- Modify: `tools/nano_banana_ppt/agents/visual.py`
- Modify: `tools/nano_banana_ppt/utils/review_plan.py`

**Step 1: Clean up `visual.py`**
Remove `table_dominant` from `LAYOUT_LIBRARY`.
In `_assign_layout`:
```python
            if table_data:
                if visualization in ('bar', 'line', 'pie'):
                    return 'chart_from_table', "Data visualization chart (bar/line/pie) derived from table data."
                # If they still send something else, fallback to content
                return 'content', VisualAgent.LAYOUT_LIBRARY['content']
```
Remove `table_dominant` checks in `Task 3: Handle table/chart pages`:
```python
            if layout_name in ('chart_from_table',):
```
And remove the `else: plan_item['table_only'] = True` block.

**Step 2: Clean up `review_plan.py`**
Remove `"table": "表格"` from type mappings everywhere.
Remove the hacky table string building logic in `derive_technical_plan`:
```python
            if vis in ("bar", "line", "pie"):
                slide["visualization"] = vis
                slide["visual_prompt"] = "DATA_VISUALIZATION_PLACEHOLDER"
                slide["use_data_visualizer"] = True
            # DELETE THE ENTIRE `else:` BLOCK BELOW IT THAT FORCES "auto" AND BUILDS table_str_list
```
Remove `in_table` parsing logic from `parse_review_md`.

**Step 3: Commit**
```bash
git add tools/nano_banana_ppt/agents/visual.py tools/nano_banana_ppt/utils/review_plan.py
git commit -m "refactor(visual): remove table_dominant layout and string building hacks"
```

---

### Task 3: Remove execution and visualization code

**Files:**
- Modify: `tools/nano_banana_ppt/core/executor.py`
- Modify: `tools/nano_banana_ppt/core/data_visualizer.py`

**Step 1: Clean `executor.py`**
Change `if table_data and visualization in ('bar', 'line', 'pie', 'table'):` to `if table_data and visualization in ('bar', 'line', 'pie'):`
Remove the `if visualization == 'table':` block that tries to create a transparent background.
Change `missing = [s['page_num'] for s in visual_plan if s['page_num'] not in images_dict and not (s.get('table_data') or s.get('text_content', {}).get('table_data'))]` to just `missing = [s['page_num'] for s in visual_plan if s['page_num'] not in images_dict]` since we no longer skip background generation for native tables.

**Step 2: Clean `data_visualizer.py`**
Delete the `render_table_image` function entirely.

**Step 3: Commit**
```bash
git add tools/nano_banana_ppt/core/executor.py tools/nano_banana_ppt/core/data_visualizer.py
git commit -m "refactor(executor): remove table rendering hooks"
```

---

### Task 4: Remove native table generation from PPTX

**Files:**
- Modify: `tools/nano_banana_ppt/core/generator.py`

**Step 1: Delete `_add_native_table` function**
Find and delete `def _add_native_table(self, slide, table_data: Dict, style_config: Dict, prs) -> None:` and all its contents (approx lines 256-324).

**Step 2: Remove references in `add_slide`**
Remove the `is_native_table` detection:
```python
            # Remove:
            is_native_table = table_data and visualization in ('table',)
```
Change `if slide_img_path and not is_native_table:` to just `if slide_img_path:`
Remove the final table insertion block at the bottom of the function:
```python
            # Remove:
            if is_native_table:
                logger.info(f"Slide {page_num}: Inserting native PPT table...")
                self._add_native_table(slide, table_data, style_config, prs)
```

**Step 3: Commit**
```bash
git add tools/nano_banana_ppt/core/generator.py
git commit -m "refactor(generator): completely remove native table shape generation"
```
