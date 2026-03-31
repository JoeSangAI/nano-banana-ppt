# Nano Banana PPT Visual Tuning Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Remove strict layout boxing (bento grids, bullet counting) to allow Nano Banana 2 to dynamically adapt the page structure to the semantic meaning of the text, while strictly preserving brand colors and fonts.

**Architecture:** We will modify `tools/nano_banana_ppt/agents/visual.py`. First, we'll rewrite `_assign_layout` to stop hijacking layout decisions based on text bullet counts. Second, we'll soften `_get_page_type_specific_instruction` to remove rigid grid mandates. Finally, we'll rewrite the `STYLE ADAPTATION RULE` in the final prompt to explicitly tell the model to use the global *color/texture* but allow the layout to form *organically* around the text's metaphor.

**Tech Stack:** Python string manipulation and AI prompt engineering.

---

### Task 1: Remove "Bullet Counting" from Layout Assignment

**Files:**
- Modify: `tools/nano_banana_ppt/agents/visual.py:165-188`

**Step 1: Write the minimal implementation**
We will delete the `elif len(body)` checks and rely purely on the semantic `page_type` that the Narrative Agent so carefully decided.

Find `def _assign_layout` and rewrite it:

```python
    def _assign_layout(page_type: str, text_content: dict, prev_layout: str = None, page: dict = None) -> tuple:
        """Pick a layout based on semantic page type."""
        # Check for table/chart data
        if page:
            table_data = page.get('text_content', {}).get('table_data') or page.get('table_data')
            visualization = page.get('visualization', '')
            if table_data:
                if visualization in ('bar', 'line', 'pie'):
                    return 'chart_from_table', "Data visualization chart (bar/line/pie) derived from table data."
                return 'content', VisualAgent.LAYOUT_LIBRARY.get('content', '')

        # Map semantic page types to basic layout hints (without forcing rigid boxes)
        layout_map = {
            'cover': ('full_screen_immersive', VisualAgent.LAYOUT_LIBRARY.get('full_screen_immersive', '')),
            'back': ('centered_headline', VisualAgent.LAYOUT_LIBRARY.get('centered_headline', '')),
            'ending': ('centered_headline', VisualAgent.LAYOUT_LIBRARY.get('centered_headline', '')),
            'section': ('minimalist_hero', VisualAgent.LAYOUT_LIBRARY.get('minimalist_hero', '')),
            'hero': ('minimalist_hero', VisualAgent.LAYOUT_LIBRARY.get('minimalist_hero', '')),
            'quote': ('wide_quote_card', VisualAgent.LAYOUT_LIBRARY.get('wide_quote_card', '')),
            'infographic': ('dense_infographic', VisualAgent.LAYOUT_LIBRARY.get('dense_infographic', '')),
            'toc': ('three_column_grid', VisualAgent.LAYOUT_LIBRARY.get('three_column_grid', '')),
            'data': ('big_number_data', VisualAgent.LAYOUT_LIBRARY.get('big_number_data', '')),
            'flowchart': ('process_flow', VisualAgent.LAYOUT_LIBRARY.get('process_flow', '')),
            'comparison': ('split_screen_contrast', VisualAgent.LAYOUT_LIBRARY.get('split_screen_contrast', ''))
        }
        
        return layout_map.get(page_type, ('content', VisualAgent.LAYOUT_LIBRARY.get('content', '')))
```

### Task 2: Soften Page-Specific Instructions

**Files:**
- Modify: `tools/nano_banana_ppt/agents/visual.py:190-205`

**Step 1: Write the minimal implementation**
Rewrite `_get_page_type_specific_instruction` to remove rigid mandates (like "Use Bento grids").

```python
    def _get_page_type_specific_instruction(self, page_type: str) -> str:
        """根据页面类型生成特定的设计指令，更侧重语义而非死板构图"""
        instructions = {
            "cover": "【COVER DESIGN】Max visual impact. Title must be MASSIVE and clearly legible. Use a symbolic, high-end visual anchor.",
            "section": "【SECTION TRANSITION】Minimalist and bold. The Section Title should be the absolute focus. Create a sense of 'pause'.",
            "hero": "【HERO / GOLDEN SENTENCE】Impact over detail. Use massive typography for the core message. The background visual should organically support the metaphor of the text.",
            "quote": "【QUOTE CARD】High impact quotation. The quote text must be large and prominent, elegantly balanced with the visual context.",
            "toc": "【TABLE OF CONTENTS】Structured and clean. Organize chapters clearly with high legibility.",
            "content": "【CONTENT SLIDE】Organize the text logically. Let the text structure dictate the layout naturally, balancing it with a relevant visual element without forcing it into rigid boxes.",
            "data": "【DATA VISUALIZATION】Focus on the key metric. Integrate the data visualization seamlessly into the scene's aesthetic.",
            "infographic": "【INFOGRAPHIC】Organize complex information clearly. Use logical grouping and visual hierarchy to manage high density, allowing the specific semantic structure (like a cycle, pyramid, or web) to form naturally.",
            "flowchart": "【PROCESS / FLOW】Visually connect the steps. Draw a clear directional flow that matches the text, blending the nodes organically into the environment.",
            "comparison": "【COMPARISON】Create a visual duality. Contrast the two concepts clearly using layout, lighting, or composition.",
            "ending": "【ENDING】Simple and memorable. Clean background, elegant text placement."
        }
        return instructions.get(page_type, instructions['content'])
```

### Task 3: Rewrite the Prompt's Style Override Rule

**Files:**
- Modify: `tools/nano_banana_ppt/agents/visual.py:328-340`

**Step 1: Write the minimal implementation**
Find the `STYLE ADAPTATION RULE` block in the prompt and rewrite it to explicitly grant layout freedom.

```python
            user_prompt = f"""Generate a high-fidelity image generation prompt for a PPT slide.

{design_system}

{prompt_mode}
- **Reference Image**: Using '{os.path.basename(reference_image_path) if reference_image_path else "None"}' as style anchor.

【Global Context (For Consistency)】
{outline_summary}

【CURRENT PAGE TARGET】
- Section: {page.get('section_title', 'General')}
- Page Type: {page_type.upper()}
- Initial Visual Suggestion: {visual_suggestion}

【STYLE & SEMANTIC ADAPTATION RULE (CRITICAL)】
1. You MUST apply the Global Style (especially the exact Color Palette, lighting, and textures) to the scene.
2. HOWEVER, the layout and structural metaphor MUST adapt organically to the specific text content and Initial Visual Suggestion.
3. If the page is a "flowchart", "comparison", or describes a specific metaphor (like a flywheel or pyramid), you must draw that specific semantic structure. 
4. DO NOT force text into rigid, generic boxes or bento grids unless specifically requested. Allow the visual elements to form dynamically around the text's meaning while strictly wearing the "skin" of the Global Style.
{native_image_constraint}

【Instruction】
1. **{type_instruction}**
2. Describe the visual scene in detail.
3. Plan text placement organically based on the meaning of the content.

{render_text_block}

{neg_constraints}

【Output】
Directly output the final image-generation Prompt string. No explanation."""
```

### Task 4: Commit

**Step 1: Commit the changes**
```bash
git add tools/nano_banana_ppt/agents/visual.py
git commit -m "feat: loosen rigid layout constraints to allow dynamic semantic composition"
```