# Nano Banana PPT 交互重构与视觉纠偏实施计划 (Implementation Plan)

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 将 Plan 阶段真正拆分为 `plan-content` 和 `plan-visual` 双指令流；确保输出文件为通俗易懂的中文大白话；将 Logo 颜色决策交还给 LLM 的“设计审美”；打通排版类型的有机传递。

**Architecture:** 
1. 拆分 `main.py` 中的 CLI 入口，分为 `plan-content` 和 `plan-visual`。
2. 在 `review_plan.py` 中新增 `build_content_review_md`（极简纯文字版）和修改 `generate_design_manifesto`（输出大白话中文设计提案）。
3. 在 `agents/visual.py` 中，调整风格生成 Prompt，让 LLM 智能判断 Logo 颜色是否与目标风格兼容。
4. 确保排版关键字（如 `flowchart`, `infographic`）能够正确传递并在图片生成中生效。

**Tech Stack:** Python, OpenAI API (Gemini)

---

### Task 1: 真正拆分命令流为 `plan-content` 和 `plan-visual`

**Files:**
- Modify: `tools/nano_banana_ppt/main.py`

**Step 1: 重构 CLI 解析**
更新 `_parse_cli_args` 和 `__main__`，支持 `plan-content` 和 `plan-visual`，为了向后兼容，原有的 `plan` 命令可以直接映射为执行 `plan-content` 然后立刻提示用户执行下一步。

**Step 2: 拆分功能函数**
将庞大的 `generate_plan` 拆分为 `generate_content_plan` 和 `generate_visual_plan`：
- `generate_content_plan`: 只提取 `NarrativeAgent.analyze_content` 和 `generate_narrative_outline`。将结果存入 `content_plan.md`。
- `generate_visual_plan`: 读取 `content_plan.md`，执行 Logo 提取、`VisualAgent.define_style` 和 `generate_design_manifesto`。生成一份中文大白话视觉提案，追加到文件头部，并将文件另存为 `plan_for_review.md`。

**Step 3: Commit**
```bash
git add tools/nano_banana_ppt/main.py
git commit -m "feat: split plan into plan-content and plan-visual commands"
```

---

### Task 2: 重构内容与视觉的 Markdown 呈现 (大白话与去杂质)

**Files:**
- Modify: `tools/nano_banana_ppt/utils/review_plan.py`

**Step 1: 编写极简 `build_content_review_md`**
剔除所有关于配色、风格、选图理由、布局类型的系统字段。
对于原生图片，格式简化为大白话：
`- **原生插图**：这是一张 [图片语义]，它将被 [融合/叠加] 到本页中（预览：[图片路径]）`

**Step 2: 修改 `generate_design_manifesto` 的 Prompt**
要求大模型输出**中文大白话的设计提案**。
Prompt 必须强调：不要生成机械的 JSON 或键值对，用两三段话与人类沟通。必须包含：建议的主题意象、核心色调、以及针对“AI 塑料感”的明确禁令（如：不使用发光大脑等）。
*注：代码层面的生图逻辑仍需要硬性的英文负向提示词，所以除了中文大白话，依然需要返回一个隐式的英文 `cliche_ban_list` 供后端使用，或者让 VisualAgent 自己去理解这段中文提案。这里最优雅的做法是让 LLM 返回 JSON，包含 `chinese_proposal` 和 `english_cliche_bans`。*

**Step 3: Commit**
```bash
git add tools/nano_banana_ppt/utils/review_plan.py
git commit -m "feat: use plain chinese for content review and visual manifesto"
```

---

### Task 3: 优化视觉总监的色彩智能融合与版式连结

**Files:**
- Modify: `tools/nano_banana_ppt/agents/visual.py`
- Modify: `tools/nano_banana_ppt/agents/visual_flash.py`

**Step 1: 智能评估 Logo 色彩**
在 `VisualAgent.define_style` 中，当存在 `brand_colors` 和预设风格时：
修改 LLM prompt：`The user provided a logo with dominant colors: {brand_colors}. The requested visual style is: {user_preference}. As an expert Art Director, judge if these colors naturally fit the requested style. If yes, incorporate them as primary or accent colors. If they severely clash (e.g. neon green logo on a dark luxury theme), prioritize the requested style's aesthetics and ignore the logo colors for the background generation.`
（注：如果是强制命中系统预设 `curated_style`，则通过字符串拼接，将这段逻辑注入到后续生成每页 `visual_prompt` 的 `design_system` 中去，由生图大模型去把握平衡）。

**Step 2: 修复版式断层**
确保 Narrative Agent 生成的特殊页面类型（如 `flowchart`, `data`, `comparison`）在 `VisualAgent._assign_layout` 或 `_get_page_type_specific_instruction` 中得到强有力的英文生图 Prompt 支撑。
确保不要让 `content` 页面一股脑全变成 `left_text_right_visual`。

**Step 3: Commit**
```bash
git add tools/nano_banana_ppt/agents/visual.py tools/nano_banana_ppt/agents/visual_flash.py
git commit -m "fix: intelligent logo color blending and organic layout mapping"
```
