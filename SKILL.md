---
name: nano-banana-ppt
description: Use when creating professional PowerPoint presentations, generating slides from content/topics, or visualizing concepts into a deck with Nano Banana 2. Supports Template Cloning and AI Minting modes.
---

# Nano Banana PPT Generator (Advanced)

## Overview
Automates professional PowerPoint creation using Google's Nano Banana 2 (Gemini 3). This advanced version features a modular "Auto Pipeline" that supports:
1.  **Narrative Architecture**: Deep analysis of content to build logical story flows (using `NarrativeAgent`). Supports multiple narrative frameworks (SCQA, Golden Circle, Hero's Journey, etc.) and **speaker notes** (演讲备注) for detailed presenter guidance—screen text stays concise while rich context lives in notes.
2.  **Visual Prompt Engineering**: Sophisticated image generation prompts with style injection (using `VisualAgent`).
3.  **Template Cloning**: Extract style, logo, and layout from existing PDF/PPTX templates (using `TemplateAgent`).
4.  **AI Minting**: Automatically define and generate a cohesive visual style if no template is provided.
5.  **Tables & Charts (Hybrid)**: Tables use **native PPT table** (editable in PowerPoint); charts (bar/line/pie) use rendered images.

## 叙事与版面设计原则 (Narrative & Layout)

- **副标题按需**：金句页、封面可省略副标题；仅当能补充关键信息或承上启下时使用。
- **正文形态多样化**：`paragraph`（成段）、`bullets`（要点）、`data`（数据块）、`quote`（引用）、`mixed`（混合）。避免所有页面僵化为 bullet 列表。
- **呼吸页 (breathing)**：适当穿插轻页面——一个问句、一个数字或半屏留白+过渡语，给听众 3–5 秒消化时间。
- **密度交替**：信息页 ↔ 金句页 ↔ 数据页 ↔ 图/流程页，形成节奏。结合演讲内容自然交替，不为了节奏而节奏。
- **抬机率设计**：穿插可拍照页（金句、翔实数据、框架图、公式、行动指引）。结尾优先放一句可拍照金句。
- **表格 vs 图表**：精确对比用表格，趋势/比例用图表。避免同页同时塞满表格+图表。

## Tables vs Charts (混合策略)

| 类型 | 实现方式 | 特点 |
|------|----------|------|
| **表格** (visualization: table) | 原生 PPT 表格 | 可在 PPT 中直接编辑文字、调整列宽和样式 |
| **图表** (visualization: bar/line/pie) | 图片渲染 | 由 Matplotlib 生成柱状/折线/饼图，风格与 style_config 一致 |

表格样式由 `style_config` 驱动：主色、背景、字号（标题 18–24pt、正文 14–18pt）、列宽比例、表头底色与加粗、行间留白。

## 原生图片排版 (Native Images Semantic Layout)

通过 `plan_for_review.md` 中的 `- **📥 原生图片**：` 配置，支持在 AI 生成的背景上精准贴合原图。

**排版机制：**
1. **自动提取与智能选择**：`NarrativeAgent` 会自动提取源文档中的本地或网络图片（并下载），根据上下文严格判断相关性。只有强相关（如数据图表、新闻截图）才会保留。
2. **强制背景留白**：在生成背景的 Prompt 中，注入严厉的禁令（`CRITICAL VISUAL CONSTRAINT...`），强迫 AI 在指定区域（如左侧、右侧）留出不含任何文字和复杂图形的纯色安全区。
3. **视觉智能对齐 (VLM Layout)**：在背景生成后，调用 `Gemini 1.5 Pro`（视觉能力）去“看”一眼这页 PPT，根据背景上的留白和文字走势，计算出一个**完美的、带有安全边距的绝对居中坐标**，彻底避免图片压字或紧贴边缘的尴尬，实现真正的人类设计师级排版。
4. **完美比例缩放**：最后在插入 PPTX 时，严格保持原生图片的长宽比（Aspect Ratio），在 VLM 给定的安全框内等比缩放并绝对居中。

## When to Use
- User asks for "PPT", "slides", "deck", or "presentation".
- Converting existing documents/notes into slide format with high visual fidelity.
- **Cloning a style**: "Make it look like this PDF" or "Use this template".
- **Visualizing abstract concepts**: "Create a futuristic pitch deck".

## Workflow (Two-Phase Pipeline)

The pipeline is split into two phases to allow human review before image generation (the expensive step).

### Pre-defined Style Library (内置风格库)
You can directly use these high-quality curated styles by passing their names to the `--style` argument or `style_preference` input:
- **`claude_minimalist`**: Warm, intellectual, approachable. Off-white/cream backgrounds, elegant typography mixing serif and sans-serif.
- **`neo_brutalism`** (新粗野主义): Raw, bold, unapologetic. High contrast, stark backgrounds, bright accents, thick black borders, hard offset shadows.
- **`japanese_aesthetic`** (日式美学): Zen, quiet, balanced. Muted earth tones, extreme negative space, asymmetrical balance.
- **`apple_keynote`**: Premium, cinematic. Deep black backgrounds, massive white typography, glowing gradients.
- **`cyberpunk`**: Dark, dystopian, high-tech. Deep navy/black with neon cyan, magenta, electric yellow.
- **`academic_paper`**: Clean, authoritative. White background, classic serif typography, formal grid structure.

### Phase 1: Plan (generates human-readable review plan, NO images)
```bash
python3 -m nano_banana_ppt.main plan <content_file> [template_file] [logo_file] [output_name] [--pages N]
```
- Analyzes content, parses template, generates narrative outline.
- Saves **plan_for_review.md** (human-readable Markdown: 整体设计、各页类型/标题/内容/**演讲备注**/配图描述).
- NarrativeAgent 会：精细拆解章节、将详实论述放入演讲备注、用 hero 页突出金句。支持多种正文形态（paragraph/bullets/data/quote/mixed）、呼吸页、副标题按需、抬机率设计。
- Does NOT generate plan.json or visual prompts at this stage.
- **Agent MUST present the outline (from terminal output or plan_for_review.md) to the user for confirmation before proceeding.**
- **Do NOT run `execute` until the user confirms.**

### Phase 2: Execute (reads review plan, derives technical plan, generates images + assembles PPTX)
```bash
python3 -m nano_banana_ppt.main execute <项目目录或plan_for_review.md> [output_name] [--resolution 1K|2K|4K] [--slides 3 5 7]
```
- Accepts: project directory (e.g. `output/设定集`), `plan_for_review.md`, or `plan.json`.
- If given plan_for_review.md: parses MD → derives plan.json (LLM generates visual_prompts) → saves plan.json → generates images.
- Generates images via Gemini, assembles `.pptx`.

### Agent Workflow (CRITICAL — follow this exact sequence):
1. **Style Consultation (Interactive):** Before running any commands, ask the user if they have a preferred visual style. **Proactively list 3-4 relevant options** from the *Curated Style Library* (e.g., "Would you like a 'Claude Minimalist', 'Apple Keynote', or 'Liquid Glass' style?").
2. Run `plan` with user's content file AND the selected `--style` (if any).
3. **Present the slide outline to the user** (from terminal output or by reading `plan_for_review.md`).
4. **Style Confirmation:** Remind the user they can still change the style by editing the `plan_for_review.md` file (refer to the "Style Inspirations" block in the file).
5. **STOP. Wait for user confirmation.** Do NOT run `execute` in the same response/turn.
6. **Only after the user explicitly says "确认" / "可以" / "开始生成" / "run execute"**, run `execute`.

**⛔ FORBIDDEN:** Running `plan` and `execute` back-to-back in one go. The human must review plan_for_review.md and confirm before any image generation begins.

### Legacy: One-shot auto mode (interactive terminal only)
```bash
python3 -m nano_banana_ppt.main auto <content_file> [template_file] [logo_file] [output_name]
```

## Dependencies
- `openai` (used for Gemini compatibility)
- `pymupdf` (fitz, for template parsing)
- `python-pptx`
- `Pillow`
- `python-dotenv`
- `requests`

## Configuration
- `OPENAI_API_KEY` or `GOOGLE_API_KEY`: Required.
- `OPENAI_API_BASE`: Optional (defaults to Google's OpenAI-compatible endpoint).

## Common Mistakes & Red Flags

| Mistake | Consequence | Fix |
|---------|-------------|-----|
| **Skipping Phase 1 review** | User gets unwanted content | ALWAYS show plan_for_review.md outline to user and wait for confirmation before execute |
| **Chaining plan→execute without confirmation** | User cannot review/edit plan before costly image generation | NEVER run execute in the same turn as plan. STOP after plan, present outline, wait for "确认" |
| **Using .pptx as template** | May need LibreOffice for conversion | Prefer PDF templates, or ensure `soffice` is installed |
| **Missing API Key** | Script failure | Ensure `GOOGLE_API_KEY` is set |
| **Manual XML editing** | Corrupt files | Always use the script |
| **Not providing Logo source** | No logo in output | Pass logo file alongside template |
| **Running `execute` without `plan`** | Missing plan file | Always run `plan` first; execute needs plan_for_review.md or plan.json |
| **Ignoring gray slides** | API failures resulted in placeholder | Rerun with `--slides N` for failed pages (check terminal output for errors) |

## Stability Notes
- Default max_retries increased to 5 with exponential backoff (up to 48s wait).
- Max concurrent workers set to 2 to prevent API rate limiting.
- If specific slides fail (render as gray placeholders), use `execute ... --slides X Y` to regenerate only those slides.
