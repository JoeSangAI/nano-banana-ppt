# Dynamic Narrative Density Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Modify the NarrativeAgent prompt and SKILL.md to encourage dynamic text density rather than forced bullets.

**Architecture:** Prompt engineering in Python, markdown edits in the skill documentation.

**Tech Stack:** Python, Markdown.

---

### Task 1: Update NarrativeAgent Prompt

**Files:**
- Modify: `tools/nano_banana_ppt/agents/narrative.py`

**Step 1: Write minimal implementation**

Change the `Content Refinement` section in `generate_narrative_outline` prompt to encourage dynamic body formatting. Replace the strict "Slide 上只放提词器" rule with the new dynamic instructions.

Replace lines 275-278 with:
```python
2. **内容提炼法则 (Content Refinement - CRITICAL)**：
   - PPT 不是 Word 的搬运工！**绝对不要把大段原话直接复制到 body 中**。
   - **动态叙事密度与文本形态 (Dynamic Narrative Density - CRITICAL)**：
     - **因地制宜，拒绝机械排版**：有些时候是几点，有些时候是一句很有韵味的话，有些时候可能要讲个故事（用中长段文字），有些时候可能一个词足矣，甚至有些时候一个字都不要，只要放一幅画就可以了。绝对不要机械地全部使用“XXX：XXXX”的短句分点结构！
     - 结构化数据或干货：使用 `bullets`，保留极简要点。
     - 完整论述或故事讲述：使用 `paragraph`，用中长段文字说明，保持连贯性。
     - 情绪渲染或金句：使用 `quote`，只需一两句极具穿透力的话。
     - 纯视觉冲击：无需 body，只需 headline 或完全留白。
   - **把“肉”藏进备注 (Speaker Notes)**：为每页生成详尽的 `speaker_notes` 字段。将原文中那些精彩但冗长的长句、具体的案例细节、讲师需要补充的背景知识，全部放到这里。这样幻灯片才能保持清爽，同时不丢失任何信息深度。
```

**Step 2: Commit**

```bash
git add tools/nano_banana_ppt/agents/narrative.py
git commit -m "feat: relax bullet point constraints and encourage dynamic narrative density"
```

### Task 2: Update SKILL.md

**Files:**
- Modify: `.cursor/skills/nano-banana-ppt/SKILL.md`

**Step 1: Write minimal implementation**

Update the "叙事与版面设计原则 (Narrative & Layout)" section to explicitly mention the "因地制宜" (adapt to circumstances) philosophy.

Insert at the top of the bulleted list under `## 叙事与版面设计原则 (Narrative & Layout)`:

```markdown
- **因地制宜的文本密度 (Dynamic Density)**：拒绝机械的“短句分点”排版。根据内容需要调整：有些时候是几点，有些时候是一句很有韵味的话，有些时候可能要讲个故事（用中长段文字），有些时候可能一个词足矣，甚至有些时候只要放一幅画。
```

**Step 2: Commit**

```bash
git add .cursor/skills/nano-banana-ppt/SKILL.md
git commit -m "docs: add dynamic narrative density principles to SKILL.md"
```
