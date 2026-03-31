# Nano Banana PPT Bugfixes Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Fix the workflow confirmation bypass issue (rename to visual_plan.md and enforce prototype/approval) and fix the missing body text generation issue on non-content pages.

**Architecture:** We will modify `main.py` to use `visual_plan.md` as the source of truth for Phase 1.2 output and prompt users effectively. We will modify `visual.py` to unconditionally append the `body` items into the `render_text_block` for any layout type.

**Tech Stack:** Python, file I/O, string formatting.

---

### Task 1: Fix Visual Plan Renaming

**Files:**
- Modify: `tools/nano_banana_ppt/utils/review_plan.py`
- Modify: `tools/nano_banana_ppt/main.py`
- Modify: `tools/nano_banana_ppt/SKILL.md`

**Step 1: Write the minimal implementation in `review_plan.py`**

Update the filename constant:
```python
REVIEW_MD_FILENAME = "visual_plan.md"
```

**Step 2: Write the minimal implementation in `main.py`**

Ensure `main.py` CLI instructions refer to `visual_plan.md` and check for the correct `REVIEW_MD_FILENAME`.

```python
# Phase 1.2: 视觉规划（生成 visual_plan.md 包含风格和视觉主张）
```

**Step 3: Write the minimal implementation in `SKILL.md`**

Update documentation to state:
```markdown
- Saves **visual_plan.md**
```
And replace all occurrences of `plan_for_review.md` with `visual_plan.md`.

**Step 4: Commit**

```bash
git add tools/nano_banana_ppt/utils/review_plan.py tools/nano_banana_ppt/main.py tools/nano_banana_ppt/SKILL.md
git commit -m "fix: rename plan_for_review to visual_plan.md"
```

### Task 2: Fix Missing Body Text

**Files:**
- Modify: `tools/nano_banana_ppt/agents/visual.py`

**Step 1: Write the minimal implementation**

Change the `render_text_block` conditional from checking `if page_type == 'content'` to just checking if `body` exists.

```python
            # 3. Text rendering block
            render_text_block = "**TEXT CONTENT TO DISPLAY (render ONLY these, nothing else):**\n\n"
            if text_content.get('headline'):
                render_text_block += f'Headline: "{text_content["headline"]}"\n'
            if text_content.get('subhead'):
                render_text_block += f'Subtitle: "{text_content["subhead"]}"\n'
            if text_content.get('body'):
                render_text_block += "Body Points (render EXACTLY the text inside quotes):\n"
                for i, item in enumerate(text_content['body']):
                    item_clean = item.lstrip('-•* ').strip()
                    render_text_block += f'Text {i+1}: "{item_clean}"\n'
```

**Step 2: Commit**

```bash
git add tools/nano_banana_ppt/agents/visual.py
git commit -m "fix: unconditionally render body text for all layout types"
```

### Task 3: Verify the Fix

**Step 1: Run the `execute` command on targeted slides**

```bash
PYTHONPATH=tools python3 -m nano_banana_ppt.main execute "output/ppt/20260311_非凡产研PPT" --slides 3 4 5 6 7 10 11
```

**Step 2: Review PPT output visually to confirm text generation**

(Since this is visual, we will ask the user to verify the generated PPTX or look at the slides directory.)