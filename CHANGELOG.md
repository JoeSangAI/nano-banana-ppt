# Changelog

All notable changes to this project will be documented in this file.

## [v2.5.1] - 2026-03-06

### ✨ 新特性 (New Features)

*   **开源贡献与版权支持**: 增加了 `MIT License` 和完整的 `Contributing` 指南，欢迎社区共同参与建设。

### 🛠 重构与优化 (Refactoring & Improvements)

*   **完全移除原生表格生成**: 为了强化全局视觉一致性，废弃了基于 `python-pptx` 的原生表格生成方案 (`data_visualizer.py`)，统一采用高质量图片渲染或大模型排版处理。
*   **独立高清放大命令 (Upscale CLI)**: 新增独立的 `upscale` 命令行模式，支持通过 `--resolution 2K/4K` 和 `--slides 1,2,3` 指定特定幻灯片调用 Gemini 重新生成高清版本并组装。

## [v2.5.0] - 2026-03-05

### ✨ 新特性 (New Features)

*   **预设风格库 (Curated Style Library)**: 引入了系统级高质量视觉风格预设。不仅提升了生图的一致性，还大幅优化了具体风格的美学表现。目前原生支持：
    *   **`Claude 风格` (claude_minimalist)**：温润、极简、知性。奶白色背景，优雅衬线体与无衬线体混排。
    *   **`新粗野主义` (neo_brutalism)**：原始、大胆、高对比。亮色背景，黑色粗边框，生硬阴影，怪诞无衬线体。
    *   **`日式美学` (japanese_aesthetic)**：禅意、侘寂。大地色系，极致留白，非对称排版。
    *   **`苹果发布会风格` (apple_keynote)**：极致高级。深邃纯黑背景，巨大白色无衬线字体，发光渐变。
    *   **`赛博朋克` (cyberpunk)**：科技、故障艺术。深蓝/纯黑底色，荧光青、品红、电光黄点缀。
    *   **`学术风` (academic_paper)**：严谨、专业。纯白背景，经典衬线体，正式的网格排版。
    *   **`液态玻璃` (liquid_glass)**：高级科技。半透明毛玻璃卡片，超细边框，Bento 网格排版。
    *   **`时尚杂志` (magazine_editorial)**：电影级留白。优雅衬线体，不对称排版，适合品牌/人物。
    *   **`3D粘土风` (soft_3d_clay)**：可爱、膨胀。马卡龙色系，哑光软材质，适合活泼场景。
    *   **`黑金奢华` (dark_luxury)**：高级定制。深邃背景搭配暗金线条，适合高端商务。
    *   **`新中式` (traditional_chinese)**：水墨意蕴。留白、朱红点缀、圆窗构图，适合文化/政务。
    *   **`全息镭射` (holographic_chrome)**：Y2K 前卫艺术。液态金属，彩虹光泽。
    系统将通过别名自动匹配最高质量的视觉生成指令，无需完全依赖 LLM 临场发挥。

*   **交互式风格推荐**: 在 Phase 1 生成的 `plan_for_review.md` 中，新增了「AI 风格灵感库」区域，直观展示可选的高级风格，用户可直接复制风格代码填入配置表，极大地降低了审美决策成本。

## [v2.4.1] - 2026-03-04

### 🛠 重构与优化 (Refactoring & Improvements)

*   **消除 temp_slide 重复文件**：`create_advanced_pptx` 此前为满足 `add_picture()` 需文件路径而在磁盘上另存 `temp_slide_XX.png`，且未清理，导致输出目录同时存在 `slide_XX.png` 与 `temp_slide_XX.png` 两套文件。现已改为优先直接使用 executor 已写入的 `slide_XX.png`，不再产生 temp 副本。

## [v2.4.0] - 2026-03-02

### 🐛 修复 (Bug Fixes)

*   **风格一致性修复 (Style Consistency — Core Fix)**：识别并修复了导致字体、配色、版式在幻灯片间不统一的根本原因：
    *   `derive_technical_plan()` 中的 `design_system` 从单行简化描述升级为结构化的「严格设计系统」指令，新增跨页一致性强制约束：*"ALL slides MUST use the exact same fonts, colors, shape language, and decorative elements."*
    *   `parse_review_md()` 新增对 `| 字体 |` 字段的正确解析，修复了字体信息在 `plan_for_review.md` 往返中永久丢失的 bug。
    *   `_generate_visual_prompt_for_page()` 新增 `outline_summary` 参数，每张幻灯片的 visual prompt 现在能看到整套 PPT 的全局大纲，帮助 AI 维持跨页视觉一致性。

*   **Content 母版覆盖范围修复 (Master Reference Fix)**：`framework`、`flowchart`、`comparison`、`data`、`toc`、`breathing` 等信息展示类页面此前无法获取 content 母版参考图，导致它们与 content 页面视觉风格分裂。现已将这些类型全部纳入 `CONTENT_FAMILY`，统一使用 content 母版作为生成参考。

*   **503 错误 Fallback 修复 (503 Fallback Fix)**：LLM 调用链 (`llm_client.py`) 此前只处理 `429`（配额耗尽），遇到 `503`（服务临时高峰）时会直接放弃切换，导致整次任务所有后续页面都降级为最简陋的 prompt。修复后：
    *   **503（临时高峰）**：仅跳过本次调用，切换到备用模型，下次请求仍先重试主模型。
    *   **429（配额耗尽）**：维持原有行为，整个任务内永久跳过该模型。

*   **`regenerate.py` 导入路径修复**：修复了 `regenerate.py` 中错误的相对 import 路径（`nano_banana_ppt` → `nano_banana_ppt`），避免在 standalone 模式下因导入失败而崩溃。

## [v2.2.0] - 2026-02-28

### 🚀 新特性 (New Features)

*   **模型底座全面升级 (Model Upgrade)**：
    *   全线业务代理（NarrativeAgent、VisualAgent、TemplateAgent）已从 `gemini-3-pro-preview` 升级至最新一代高智力模型 **`gemini-3.1-pro-preview`**，带来更深度的业务理解和更精准的提示词生成。
    *   底层图像生成模型从 `gemini-3-pro-image-preview` 升级至 **`gemini-3.1-flash-image-preview`**，在保持画质的同时大幅提升渲染速度。
*   **强化叙事提取蓝图 (Deep Narrative Blueprint)**：
    *   NarrativeAgent 中的分析引擎引入了“深度叙事蓝图”层，不再仅仅提取骨架，更规划演讲的节奏、情绪起伏和内容映射，并支持用户直接注入 Briefing (意图)，确保幻灯片核心逻辑服务于讲述者意图。
    *   支持了更多样化的正文形态（如 `bullets`, `data`, `quote` 等），并改善了视觉提示工程以按需有条件地使用纯列表排版。
*   **双阶段自动化流 (Two-Phase Auto Pipeline)**：
    *   **Phase 1 (Plan)**: 引入了基于 Markdown 的审阅机制。首先生成 `plan_for_review.md`，允许用户在生成昂贵的图片前进行确认和修改。
    *   **Phase 2 (Execute)**: 读取确认后的计划文件进行渲染和 PPT 组装。
*   **混合图表渲染系统 (Hybrid Tables & Charts)**：
    *   **原生表格支持**: 表格 (`visualization: table`) 现采用原生 PPT 表格渲染，允许用户直接在 PowerPoint 中修改文本、调整列宽和单元格样式。
    *   **静态图表渲染**: 引入 `data_visualizer.py`，支持将柱状图、折线图、饼图等数据渲染为与主风格一致的高清图片。
*   **演讲备注支持 (Speaker Notes)**：
    *   叙事代理 (`NarrativeAgent`) 升级，支持为每页自动生成详尽的“演讲备注”，从而保持 PPT 页面核心文案的精简，并将丰富的业务背景放入备注中。
*   **局部重新生成 (Partial Regeneration)**：
    *   支持在生成失败（如 API 限流出现灰色占位图）时，通过 `execute ... --slides X Y` 仅重新生成指定的出错页面，无需从头开始。

### 🛠 重构与优化 (Refactoring & Improvements)

*   **长文本超时处理**: 将 `NarrativeAgent` 的请求超时时间放宽至 600 秒，以完美支持 50+ 页超大型演示文档的逻辑推演。
*   **包结构标准化**: 重新组织代码架构为标准的 Python 模块 (`nano_banana_ppt`)，清理了原有分散的脚本，提供更清晰的 `agents`、`core` 和 `utils` 目录划分。
*   **API 稳定性提升**: 将默认重试次数增加至 5 次，并引入指数退避策略 (最高 48 秒)，有效降低由于 API 并发限流导致的生成失败概率。
*   **并发控制**: 设置最高并发线程数（max concurrent workers = 2），以平滑处理图片生成请求并防止触发速率限制。
*   **系统提示词优化 (Prompt Engineering)**：对 `NarrativeAgent` 和 `VisualAgent` 的系统提示词进行了全面升级，增强了各种业务分析模型（如 SCQA、金字塔原理、英雄之旅）的自适应性。

### 🐛 修复 (Bug Fixes)

*   修复了导入路径导致的 `ModuleNotFoundError`。
*   修复了生成全黑或不完整图片的角点问题。
*   优化并修复了纯要点 (bullet points) 排版的过度生成情况。
