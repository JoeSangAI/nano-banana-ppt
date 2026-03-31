# Nano Banana PPT Fixes: Visual Plan Renaming & Missing Content Fix

## Context & Problem Statement
During the recent usage of the `nano-banana-ppt` skill, two main issues were identified:
1. **Workflow & Naming Inconsistency**: When the user requested a style change, the AI skipped the `prototype` confirmation step and directly executed the full generation. Furthermore, the intermediate markdown files were inconsistently named (`content_plan.md` vs `plan_for_review.md`).
2. **Missing Body Text in Non-'content' Pages**: Several slides (e.g., pages 3-7, 10, 11) generated only headers and subheaders, entirely omitting the body text (bullet points/paragraphs) that was clearly present in the markdown outline.

## Root Cause Analysis
1. **Workflow**: The agent failed to follow the strict two-step confirmation protocol defined in the `SKILL.md`. The hardcoded filename `plan_for_review.md` created a mental disconnect from `content_plan.md`.
2. **Missing Text**: In `tools/nano_banana_ppt/agents/visual.py`, the `render_text_block` construction had a flawed conditional:
   ```python
   if page_type == 'content' and text_content.get('body'):
   ```
   This meant that any page mapped to a different layout type (`comparison`, `framework`, `flowchart`, `infographic`, etc.) would silently drop all its body text before sending the prompt to the image generation model.

## Implemented Solutions

### 1. Rename `plan_for_review.md` to `visual_plan.md`
- Updated `tools/nano_banana_ppt/utils/review_plan.py` to change `REVIEW_MD_FILENAME` to `visual_plan.md`.
- Updated references in `main.py` CLI instructions and terminal outputs.
- Updated `SKILL.md` to enforce the new naming convention and emphasize the necessity of stopping for user confirmation after `visual_plan.md` generation or modification.

### 2. Fix the Body Text Rendering Bug
- Modified `tools/nano_banana_ppt/agents/visual.py` to remove the restrictive `page_type == 'content'` condition.
- **New Logic**:
  ```python
  if text_content.get('body'):
      render_text_block += "Body Points (render EXACTLY the text inside quotes):\n"
      for i, item in enumerate(text_content['body']):
          item_clean = item.lstrip('-•* ').strip()
          render_text_block += f'Text {i+1}: "{item_clean}"\n'
  ```
- This ensures that *any* page with a `body` array will have its content passed to the image generator, regardless of its abstract layout type.

## Next Steps / Execution
1. Trigger a targeted re-generation of the affected slides (3, 4, 5, 6, 7, 10, 11) using the `execute` command with the `--slides` flag to verify that the body text is now properly rendered onto the slides.