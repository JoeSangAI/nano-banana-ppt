# 移除原生表格功能，全面转向视觉图文混排 (Remove Native Tables for Visual Consistency)

## Overview

Current PowerPoint generation occasionally inserts native PPT tables. This breaks visual consistency because the clean, generated background image clashes with the default, rigid formatting of a standard PowerPoint table. Furthermore, the narrative agent sometimes forces tabular formats on content that would be better served by structural diagrams or simple bullet points.

The goal is to **completely remove native table insertion logic**, converting tabular data into either:
1. Native charts (bar/line/pie) via the existing Matplotlib renderer.
2. Beautiful text-based layouts (bento, comparison, frameworks) rendered seamlessly into the background image by the vision model.
3. For overly complex tables (e.g., pricing sheets, massive data dumps), the system will output standard text and rely on the user to manually paste the table/screenshot into the final deck if they deem it necessary.

## Design Decisions

### 1. Narrative Agent Rules (`agents/narrative.py`)
- We will strictly ban the `table` value in the `type` or `visualization` fields.
- For purely numeric data: Retain the rule to use `data` type with `bar/line/pie` visualization.
- For text-heavy tables: We will instruct the LLM to reconstruct the content into `comparison` (for two columns), `framework`, or `bullets`.
- If a table is massive and undeniable: The LLM will be instructed to summarize the key takeaway on the slide, and add a note in `speaker_notes` that "A complex table existed here in the source; please insert it manually if needed."

### 2. Review Plan Parser (`utils/review_plan.py`)
- Remove the hacky workaround that tries to convert table strings into `auto` visualization blocks.
- Stop trying to reconstruct `table_str_list`. If the narrative agent follows instructions, it will simply output text `body` items instead of `table_data` (unless it's for a chart).
- Strip out `table` from `type_map` and layout mappings.

### 3. Visual Agent (`agents/visual.py`)
- Remove the `table_dominant` layout style entirely.
- Ensure that if `table_data` exists, it MUST be paired with `chart_from_table` (meaning it's a bar/line/pie chart). Any other table data will be ignored or logged as an error since the Narrative agent shouldn't produce it.

### 4. Data Visualizer & Executor (`core/executor.py` & `core/data_visualizer.py`)
- Remove `render_table_image` function from `data_visualizer.py`.
- In `executor.py`, simplify the check: if it's `bar`, `line`, or `pie`, use the chart renderer. Remove `table` from the visualization tuple check.

### 5. PPTX Generator (`core/generator.py`)
- **Delete `_add_native_table` function completely.**
- Remove the logic that checks for `is_native_table` and inserts PPT shapes.
- The slide will simply receive the beautiful background image (or chart image).

## Implementation Steps

1. Modify `agents/narrative.py` prompts to forbid native tables and guide towards text layouts or charts.
2. Update `utils/review_plan.py` to remove table layout translation and string concatenation hacks.
3. Clean up `agents/visual.py` to remove `table_dominant`.
4. Remove `render_table_image` from `core/data_visualizer.py`.
5. Remove `_add_native_table` from `core/generator.py` and references in `core/executor.py`.

## Success Criteria
- Running the pipeline on a document containing a Markdown table produces either a chart (if numeric) or beautiful text points (if text-based), but NEVER a native PowerPoint table.
- Codebase is cleaner with no vestigial native table functions.
- Visual consistency is maintained 100% of the time across all generated slides.