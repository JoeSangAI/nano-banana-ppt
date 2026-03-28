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
5.  **Charts, Infographics, and Editable Finishers**: Numeric data uses rendered charts (`bar` / `line` / `pie`), high-density structure can use `infographic`, and the final deck appends one pure-background helper slide plus two blank editable template slides for manual finishing when needed.

## 叙事与版面设计原则 (Narrative & Layout)

- **副标题按需**：金句页、封面可省略副标题；仅当能补充关键信息或承上启下时使用。
- **正文形态多样化**：`paragraph`（成段）、`bullets`（要点）、`data`（数据块）、`quote`（引用）、`mixed`（混合）。避免所有页面僵化为 bullet 列表。
- **呼吸页 (breathing)**：适当穿插轻页面——一个问句、一个数字或半屏留白+过渡语，给听众 3–5 秒消化时间。
- **密度交替**：信息页 ↔ 金句页 ↔ 数据页 ↔ 图/流程页，形成节奏。结合演讲内容自然交替，不为了节奏而节奏。
- **抬机率设计**：穿插可拍照页（金句、翔实数据、框架图、公式、行动指引）。结尾优先放一句可拍照金句。
- **数据表达策略**：趋势/比例优先用图表；高密度结构优先用 `infographic`；如果必须保留原始表格，建议最终贴入系统附赠的空白模板页中手工整理。

## Data, Infographics, and Tables

| 类型 | 实现方式 | 特点 |
|------|----------|------|
| **图表** (visualization: bar/line/pie) | 图片渲染 | 由 Matplotlib 生成柱状/折线/饼图，风格与 style_config 一致 |
| **信息图** (`infographic`) | AI 结构化排版 | 适合高密度信息、全景图、模块化框架 |
| **表格** (table_data) | AI 图片渲染 | 支持完整还原多行多列表格数据，通过 prompt 约束确保所有行列被完整呈现 |

**表格渲染支持格式：**
- `{headers: [...], rows: [[...], [...]}` — 标准格式（推荐）
- `[{...}, {...}]` — list of dicts
- `[[...], [...]]` — list of lists (第一行为表头)

**表格渲染约束：** 在 visual prompt 中添加了 `TABLE RENDERING (CRITICAL)` 约束，要求模型完整渲染所有行列，不得省略或摘要。

## 原生图片排版 (Native Images Semantic Layout)

通过 `visual_plan.md` 中的 `- **📥 原生图片**：` 配置，支持在 AI 生成的背景上精准贴合原图。

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

## Workflow (Dual-Director Pipeline)

The pipeline is split into phases to allow human review before image generation (the expensive step).

### Pre-defined Style Library (内置风格库 · 31风格 · 8分类)
You can directly use these high-quality curated styles by passing their names to the `--style` argument or `style_preference` input. Styles are organized by content scenario categories:

**内容讲解型**
- **`blackboard`** (黑板风): 粉笔感、培训教学、课堂推导
- **`whiteboard`** (白板风): 马克笔、内部分享、头脑风暴
- **`sketch_note`** (手绘笔记风): 手绘图标、会议纪要、工作坊

**结构与技术型**
- **`blueprint`** (蓝图风): 深蓝底白线稿、架构图、工程制图
- **`exploded_view`** (爆炸图): 产品拆解、模块关系
- **`minimal_data`** (极简数据风): 扁平图表、统计汇报
- **`terminal_tech`** (终端技术风): 黑底等宽、网络安全、极客感
- **`swiss_design`** (瑞士设计风): 网格系统、严谨商务
- **`academic_paper`** (学术风): Nature/Science风格、学术报告

**商务与高端型**
- **`claude_minimalist`**: 温暖知识风、思考型内容
- **`apple_keynote`**: 电影感、深黑背景、发布会
- **`liquid_glass`**: 毛玻璃、Bento Grid、金融科技
- **`dark_luxury`**: 黑金奢华、高端品牌
- **`executive_dashboard`** (高管仪表盘): KPI、财务、指挥中心
- **`strategic_infographic`** (战略信息图): 路线图、高层战略
- **`sharp_minimalism`** (极致简约): 刚性网格、高端克制

**人物与亲和型**
- **`soft_3d_clay`**: 粘土风、马卡龙、软萌可爱
- **`corporate_memphis`** (企业协作插画风): 扁平人物、HR、团队文化
- **`paper_craft`** (纸艺手作风): 层叠纸张、创意提案、教育

**编辑、杂志与潮流型**
- **`magazine_editorial`**: 时尚杂志、大片摄影、编辑力度
- **`yellow_black_editorial`** (黄黑编辑风): 黄底黑字、年轻品牌、强冲击
- **`modern_newspaper`** (商业媒体风): 大标题、编辑感、思想领导力
- **`black_orange_creative`** (黑橙创意公司风): 创意机构、广告

**流行、娱乐与高冲击型**
- **`neo_brutalism`**: 新粗野主义、高对比、粗黑边框
- **`holographic_chrome`**: 全息铬金属、Y2K、彩虹渐变
- **`cyberpunk`**: 霓虹赛博朋克、高科技、视觉冲击
- **`manga_narrative`** (漫画叙事风): 分镜、故事化、onboarding
- **`sports_energy`** (运动热血风): 速度感、激励、战役传播
- **`digital_neo_pop`** (数码拼贴风): 像素、builder文化、年轻创业
- **`pink_street_style`** (粉色街头风): 街潮、网红、活泼发布

**Artistic & Avant-garde**
- **`japanese_aesthetic`** (日式美学): 侘寂、禅意、水墨
- **`traditional_chinese`** (新中式): 国潮、红金、水墨
- **`royal_blue_red_watercolor`** (水彩风): 绘画感、愿景叙事
- **`deformed_flat_persona`** (变形扁平人物风): 艺术插画、身份认同
- **`studio_mockup_premium`** (高端产品摄影风): 产品展示、SaaS
- **`classic_pop_sculpture_vaporwave`** (古典波普风): 雕塑+蒸汽波、实验性
- **`tech_art_neon`** (科技艺术风): AI艺术、前沿视觉
- **`mincho_handwritten_mix`** (明朝手写混搭风): 文学感、人文反思

### Phase 1: Plan (Copywriter Director & Art Director)

```bash
python3 -m nano_banana_ppt.main plan <content_file> [template_file] [logo_file] [output_name] [--pages N]
```
- **Copywriter Director** analyzes content, parses template, and generates narrative outline.
- **Art Director** generates a Design System Manifesto (defining shape, composition, color, and explicitly banning cliché AI elements).
- Saves **visual_plan.md** (human-readable Markdown: 包含 Art Director 的 Manifesto（视觉设计系统与避坑指南），以及 Copywriter 的各页类型/标题/内容/**演讲备注**/配图描述).
- Stores all project assets under `output/ppt/<date>_<project_name>/`.
- NarrativeAgent 会：精细拆解章节、将详实论述放入演讲备注、用 hero 页突出金句。支持多种正文形态（paragraph/bullets/data/quote/mixed）、呼吸页、副标题按需、抬机率设计。
- Does NOT generate plan.json or visual prompts at this stage.
- **Agent MUST present the outline and manifesto (from terminal output or plan_for_review.md) to the user for confirmation before proceeding.**

### Phase 1.5: Prototype (Optional but Recommended)

```bash
python3 -m nano_banana_ppt.main prototype <project_dir_or_plan_md> [output_name] [--slides 1 2]
```
- Rapidly generates 1-2 slides to confirm the visual style and template integration before generating the entire deck.
- Helps validate that the Art Director's Cliche Avoidance and Theme rules are working effectively.

### Phase 2: Execute (Derives technical plan, generates images + assembles PPTX)

```bash
python3 -m nano_banana_ppt.main execute <project_dir_or_plan_md> [output_name] [--resolution 1K|2K|4K] [--slides 3 5 7]
```
- Accepts: project directory (e.g. `output/设定集`), `visual_plan.md`, or `plan.json`.
- If given visual_plan.md: parses MD → derives plan.json (LLM generates visual_prompts using the Design System Manifesto) → saves plan.json → generates images.
- Generates images via Gemini, assembles `.pptx`.

### Agent Workflow (CRITICAL — follow this exact sequence):

#### ── GATE 1: Content Plan ──
1. Run `plan-content` with the user's content file (no style argument yet).
2. **The Co-pilot Question (NotebookLM Integration):**
   - After `plan-content` completes, you SHOULD proactively ask the user: *"您现在生成了一版是我们这个 Skill 为您提供的叙事，那么您要不要同时也看一看 NotebookLM 原生的叙事会帮您怎么做？"*
   - Simultaneously, you MUST append this reminder for the user:
     - *(a) 如果您需要的话，可能需要重新去配置 NotebookLM 相关的后台接口。*
     - *(b) 如果您没有配置过，可能还需要花 3 到 5 分钟左右时间。*
     - *(c) 如果您已经配置过，请直接确认。*
   - If user agrees:
     - Use the `notebooklm-automation` skill (or raw `notebooklm` CLI if installed) to create a notebook, add the source file, and generate an outline (e.g., `generate report --format briefing-doc`).
     - **DO NOT offer or generate podcasts, mind maps, or native PPTs here.** Those features belong ONLY in the standalone `notebooklm-automation` skill.
     - Present both the native `content_plan.md` and the NotebookLM alternative outline (which MUST be saved into the same PPT project directory as a separate file, e.g., `output/ppt/<date>_<project_name>/notebooklm_outline.md`).
     - Have the user interact and specify how to modify/fuse the outline. **CRITICAL:** Whatever the user decides, you must write the final chosen structure back into the native `content_plan.md` format before proceeding.
   - If user declines: Proceed to next step.
3. **Present `content_plan.md` to the user.** Show the slide-by-slide outline (page number, type, headline, body summary).
4. **⛔ STOP — GATE 1.** Do NOT run `plan-visual` yet. Wait for the user to explicitly confirm the content outline (e.g., "内容没问题" / "确认" / "可以"). The user may edit `content_plan.md` before confirming.

#### ── GATE 2: Visual Plan ──
5. **Style Consultation:** Only after GATE 1 is confirmed, ask the user if they have a preferred visual style. Based on the content topic and audience, **proactively recommend 3-4 most fitting styles** from the expanded style library (31 styles, 8 categories).

   **推荐表达方式**：优先用中文风格名 + 英文参考名补充，例如：
   - "偏**高端极简商业风**（接近 sharp-edged minimalism）"
   - "偏**战略信息图风**（适合路线图/高层汇报）"
   - "偏**水墨风**（Neo-Chinese aesthetic）"

   **快速对照**（按内容目标选）：
   - 要讲清楚 → 内容讲解型（黑板风/白板风/手绘笔记风）
   - 要讲结构 → 结构与技术型（蓝图风/拆解风/终端技术风）
   - 要讲战略 → 商务与高端型（战略信息图/高管仪表盘/极致简约）
   - 要讲人和团队 → 人物与亲和型（企业协作插画风/纸艺手作风）
   - 要抓眼球 → 编辑潮流/流行高冲击型（黄黑编辑风/漫画叙事风/赛博朋克）

   - 如果用户已明确说过风格（如"极简商务风"），直接采用，跳过推荐。
   - 如果用户描述了自己的意图但不在预制库中（如"赛博朋克+中国龙元素"），记录为 free-text style，plan-visual 会通过 LLM 理解并映射。
   - **模板复刻**（用户提供 PDF/PPTX）和**自定义 AI Minting**（无模板时 AI 自动定义风格）均全程可用，前者通过 `--template` 参数传入，后者为默认行为。
6. Run `plan-visual <project_dir>` with the selected `--style` (if any).
7. **Present `master_plan.md` to the user.** Show the Art Director's Manifesto (visual style, palette, cliché avoidance rules) and the per-slide visual descriptions. **Do NOT include the full style inspiration list in master_plan.md** — that list was only for agent reference during style consultation.
8. **⛔ STOP — GATE 2.** Do NOT run `execute` or `prototype` yet. Wait for the user to explicitly confirm the visual plan. Remind the user they can edit `master_plan.md` directly to adjust any slide's visual description before proceeding.

#### ── Prototype & Execute ──
9. **Prototype Offer:** Ask the user if they want to run `prototype` to preview 1-2 slides before generating the full deck.
10. **If the user wants to prototype**, run `prototype <project_dir>` and **STOP again**. Wait for the user to review the generated slides.
11. **Only after the user explicitly approves** (e.g., "确认" / "可以" / "开始生成" / "run execute"), run `execute`.

**⛔ FORBIDDEN:** Running `plan-content` and `plan-visual` in the same turn without waiting for GATE 1 confirmation.
**⛔ FORBIDDEN:** Running `plan-visual` and `execute` in the same turn without waiting for GATE 2 confirmation.
**⛔ FORBIDDEN:** Using NotebookLM's native `generate slide-deck` to skip the `execute` phase. The final presentation MUST be generated using the native `nano_banana_ppt` `execute` command for high-quality visuals.

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
- `GOOGLE_API_KEY`: Recommended public configuration.
- `OPENAI_API_KEY` / `OPENAI_API_BASE`: Optional compatibility path for advanced users, but do not present it as the default public setup.

## Common Mistakes & Red Flags

| Mistake | Consequence | Fix |
|---------|-------------|-----|
| **Skipping GATE 1 (content review)** | User gets unwanted content structure | Run `plan-content`, present `content_plan.md`, STOP and wait for confirmation before running `plan-visual` |
| **Skipping GATE 2 (visual review)** | User cannot review visual style before costly image generation | Run `plan-visual`, present `master_plan.md`, STOP and wait for confirmation before running `execute` |
| **Asking style preference before content is confirmed** | Premature style decision before user has seen the outline | Ask style only AFTER GATE 1 is confirmed |
| **Chaining plan-content→plan-visual→execute without stops** | User bypassed on both review gates | Each gate requires explicit user confirmation — never chain all three in one turn |
| **Using .pptx as template** | May need LibreOffice for conversion | Prefer PDF templates, or ensure `soffice` is installed |
| **Missing API Key** | Script failure | Ensure `GOOGLE_API_KEY` is set |
| **Promising native editable tables** | User expects a feature the current pipeline no longer provides | Offer charts, infographic pages, or the final blank template slides for manual table insertion |
| **Manual XML editing** | Corrupt files | Always use the script |
| **Not providing Logo source** | No logo in output | Pass logo file alongside template |
| **Running `execute` without `plan`** | Missing plan file | Always run `plan` first; execute needs visual_plan.md or plan.json |
| **Ignoring gray slides** | API failures resulted in placeholder | Rerun with `--slides N` for failed pages (check terminal output for errors) |

## Stability Notes
- Default max_retries increased to 5 with exponential backoff (up to 48s wait).
- Max concurrent workers set to 2 to prevent API rate limiting.
- If specific slides fail (render as gray placeholders), use `execute ... --slides X Y` to regenerate only those slides.
