# Changelog

All notable changes to this project will be documented in this file.

## [v3.1.4] - 2026-03-15

📖 **Skill 文档与 Agent 工作流更新 (Skill & Workflow Documentation)**

本次更新同步了 Cursor/Agent 侧 Skill 文档与工作流说明，确保开源仓库与推荐用法一致。

### 📖 文档与工作流 (Documentation & Workflow)

*   **双阶段确认流程 (Two-Phase Review)**：Skill 明确拆分为 `plan-content`（内容大纲）与 `plan-visual`（视觉方向 + 配图描述），每阶段均需用户确认后再进入下一阶段，禁止连续自动执行。
*   **打样与全量生成 (Prototype vs Execute)**：在 `master_plan.md` 确认后，Agent 必须主动提供「先出原型打样」或「直接生成完整 PPT」的选项；`prototype` 可从四大版式家族各抽一张打样。
*   **plan.json 复用与 `--regenerate`**：若用户修改过 `master_plan.md` 中的配图/画面描述，执行 `execute` 或 `prototype` 时需加 `--regenerate`，否则沿用已有 `plan.json`（零 token 消耗）。
*   **NotebookLM 协同提醒**：生成 `content_plan.md` 后，Agent 应主动询问用户是否同时查看 NotebookLM 原生叙事，并提醒配置与耗时。
*   **visual_prompt 零 LLM 消耗**：从 master_plan.md 模板拼接生成 visual_prompt，无额外 LLM 调用；中文 visual_suggestion 直接嵌入英文 prompt，Gemini 多语言理解。
*   **风格库仅口头展示**：内置风格库仅在「视觉总监咨询」步骤口头列举，不写入 `master_plan.md`，避免干扰审阅文件。

## [v3.1.3] - 2026-03-12

🔥 **视觉多样性与具象隐喻增强 (Visual Diversity & Figurative Metaphor Enhancement)**

本次更新重点解决了 Art Director 在处理抽象话题时过于保守、导致全篇生成单一抽象几何体（如全篇都是石头/玻璃）的单调问题。通过在代码层面放开对生成模型的过度限制，赋予其更强的创造力和视觉丰富度。

### ✨ 核心特性 (Core Features)

*   **新增视觉多样性策略 (Visual Diversity Strategy)**：
    *   在 `review_plan.py` 的设计提案阶段，强制要求 Art Director 为整份 PPT 规划 4-6 种**不同类别**的视觉主体（visual motifs）。
    *   确立了关键排版原则：**同一类视觉主体不应连续出现超过 2 页**。
    *   这些策略会被持久化到 `_content_state.json`，并贯穿整个生成生命周期。
*   **鼓励具象视觉隐喻 (Encouraging Figurative Imagery)**：
    *   明确引导系统在面对抽象概念（如哲学话题、商业理念）时，寻找**具体的视觉锚点**（如用"冰川融化"隐喻"改变"，用"灯塔"隐喻"使命"）。
    *   推荐使用人物剪影、建筑场景、自然景观、物件特写、空间透视等，取代过去默认的纯色石块、立方体、玻璃面板等抽象几何体。

### 🛠 重构与优化 (Refactoring & Improvements)

*   **放松 Cliche Avoidance 执行力度**：
    *   修改了 `visual.py` 中的 Manifesto 约束逻辑。明确指出“陈词滥调排除名单”仅针对特定的劣质元素（如发光大脑、3D漏斗），而**绝不禁止**人物、建筑、自然或真实世界物体。
    *   赋予模型 FULL creative freedom，强烈鼓励其使用多样的具象视觉隐喻。
*   **缩小 Anti-hallucination 约束范围**：
    *   将原本一刀切的 `DO NOT INVENT EXTRA OBJECTS` (甚至包括 people) 放宽为 `DO NOT INVENT IRRELEVANT COMMERCIAL OBJECTS`。
    *   仅禁止生成无关的商业产品、杂志、手表等，明确允许并鼓励生成符合语境的场景元素以丰富画面。
*   **AI Minting 模式加入多样性引导**：
    *   在生成提示词中注入 `VISUAL RICHNESS` 指令，要求视觉主体必须直接服务于幻灯片的特定信息。
*   **增强 SEMANTIC ADAPTATION RULE**：
    *   新增 `VISUAL DIVERSITY RULE` 模块，硬性规定：抽象几何形态（石碑、立方体、球体等）在整份 PPT 中的出现比例**不得超过 20%**。

## [v3.1.2] - 2026-03-12

🔥 **原生图片架构升级 (Native Image Architecture Upgrade Phase 1)**

本次更新重点修复了原生图片（用户指定的图片或 AI 从源文章中提取的图片）无法进入最终 PPT 的核心 Bug，并大幅重构了 AI 自动选图的质量控制逻辑，确保最终呈现的 PPT 既精美又精准。

### 🐛 修复 (Bug Fixes)

*   **修复 Blend 图片静默丢失 Bug**：
    *   修复了 `generator.py` 中由于严格的 `[:1]` 截断导致原图从未被发给 Gemini API 的致命 Bug。
    *   现在，最多支持将 4 张（Gemini API 上限）原生融合图连同模板参考图一起发送给大模型进行自然重绘与融合。

### 🛠 重构与优化 (Refactoring & Improvements)

*   **大幅提高 AI 自动选图门槛 (Strict Image Selection Quality Control)**：
    *   重写了 `image_selector.py` 的选图提示词，将 AI 的默认心态从“尽量选一张”改为“默认不选”。
    *   明确拒绝：通用风景、天空、氛围图、装饰性图标、章节编号图等（AI 生成的背景比这些网图更好看）。
    *   只接受：图表、数据可视化、产品实拍、人物肖像、技术图纸等包含**不可替代信息**的图片。
*   **引入全局去重机制 (Global Image Deduplication)**：
    *   在 `narrative.py` 中新增 `globally_selected_paths` 状态追踪。
    *   当同一张图片在前序页面被选中后，系统会给选图器打上 `[ALREADY USED]` 标记并进行硬性拦截，彻底解决了同一张图在不同幻灯片被反复使用 7、8 次的尴尬情况。
*   **提升选图置信度门槛 (Confidence Threshold Bump)**：
    *   将自动选图的采纳置信度阈值从 55 提升至 80，宁缺毋滥，确保只有极度匹配的图片才会进入排版计划。
*   **新增图片来源标记 (Source Tracking)**：
    *   自动选图结果现在会带有 `source: "auto"` 标记，为后续 Phase 2（区分用户强制指定 vs AI 自动推荐）的 Programmatic Compositing 架构升级打下数据基础。

## [v3.1.1] - 2026-03-11

🔥 **全局视觉一致性增强与核心逻辑深度优化**

本次更新重点解决了模板页与 AI 生图页之间的色彩断层问题，并进一步完善了页面类型的「家族分类」逻辑，确保整套 PPT 从封面到内页再到封底的绝对风格统一。

### ✨ 核心特性 (Core Features)

*   **四大版式家族 (Four Master Families)**：
    *   新增 `BOOKEND_FAMILY`（首尾页家族）。封面与封底现在独立作为一个家族，共享极简、高视觉冲击的母版参考，确保开场与结尾的视觉强呼应。
    *   彻底解决了以往封面与内页风格偶发割裂的问题。
*   **全景 Prototype (360° Prototype Preview)**：
    *   `prototype` 命令大升级！现在如果不指定具体的页码，系统会自动从 `hero`（金句/核心）、`content`（内容）、`section`（章节）、`bookend`（首尾页）四个家族中各抽取一张最具代表性的“种子页”进行生成。
    *   实现“一次打样，全貌尽收眼底”，零盲区验证视觉宪法。

### 🛠 重构与优化 (Refactoring & Improvements)

*   **真·模板页色彩同化 (Template Page Color Assimilation)**：
    *   重新设计了原生模板页的色彩继承逻辑。废弃了原本死板的“最高对比度”算法。
    *   模板页现在完美继承并应用 AI 生成的**4级色彩层级 (4-Level Color Hierarchy)**：L1主标题、L2副标题、L3正文、L4强调色（项目符号），实现与 AI 配图页的无缝衔接。
*   **设计宪法松绑 (Manifesto Unchained)**：
    *   修复了视觉提示词中部分指令“过度限制 AI 创造力”的问题。
    *   将《设计宪法》分为正向的“色彩与情绪氛围”和负向的“陈词滥调排除名单 (Bans)”，在禁止廉价塑料感的同时，释放大模型在隐喻、排版和构图上的自由创造力。
*   **清理历史包袱 (Legacy Code Cleanup)**：
    *   彻底删除了已废弃的 `visual_flash.py` 相关代码及冗余的条件分支，架构更加轻盈强健。

## [v3.1.0] - 2026-03-11

🔥 **重大架构升级：引入「双总监确认机制」与「反 AI 塑料感」视觉宪法**

本次更新重构了 `plan` 到 `execute` 的决策流，彻底剥离了“文案逻辑”与“视觉风格”的强耦合，引入了虚拟的“视觉艺术总监”角色，从根本上解决 AI 生成 PPT 时常见的“花里胡哨”、“堆砌廉价素材”（如发光大脑、3D漏斗、赛博连接线）等审美疲劳问题。

### ✨ 核心特性 (Core Features)

*   **双阶总监确认机制 (Dual-Director Review Workflow)**：
    *   **Copywriter Director (内容总监)**：专注于从长文本中提取精准的逻辑大纲与演讲备注，不再强制在同一轮次中决定视觉表现。
    *   **Visual Art Director (视觉艺术总监)**：接管视觉风格设定。它会根据大纲语境（如历史、科技、消费）寻找最贴切的“视觉意象 (Visual Motif)”，并输出一套严格的「设计宪法 (Design System Manifesto)」。
*   **强力反 AI 塑料感 (Anti-Plastic-AI Ban List)**：
    *   引入了强制性的 `cliche_avoidance` 排除名单机制。视觉总监会敏锐地将低劣、偷懒的 AI 隐喻（如：两个西装机器人握手、发光的数据节点、数字雨等）列入生图黑名单。
    *   鼓励模型采用电影级材质（如大理石、金属）或极简几何构造（Bento Grid），大幅提升产出图的质感和专业度。
*   **新增 Prototype 快速打样命令 (Visual Prototyping)**：
    *   在生成完整的 20 页 PPT 之前，系统支持调用 `prototype` 命令（如 `python -m tools.nano_banana_ppt.main prototype <project_dir> --slides 1 2`）。
    *   快速渲染封面和典型内页供用户验证“视觉宪法”的效果。确认无误后再运行 `execute` 进行全量生成，免去盲盒式漫长等待和算力浪费。
*   **智能模板共舞 (Template-Aware Subdued Blending)**：
    *   当用户提供企业模板时，生图模型不再被粗暴地降级为“只能画底纹”。
    *   视觉总监会开启受控模式：允许 AI 生成宏大、具象的插画（如角斗士、汽车模型），但会强制其**色彩同化**至模板主色调，并严格划定**排版安全区**（要求插画边缘用纯色平滑过渡），确保与原有模板版式的完美融合。

### 🛠 重构与优化 (Refactoring & Improvements)

*   **完全解耦的 Markdown 解析与派生逻辑**：重构了 `review_plan.py`。`plan_for_review.md` 现已支持直接在顶部显示并编辑 Art Director 的 Design Manifesto，并无缝贯穿至 Phase 2 的所有 Agent。
*   **Flash Agent 静默丢图修复**：彻底修复了 `VisualAgentFlash` 在遭遇并发限流或幻觉导致批量结果长度不匹配时，使用 `zip()` 导致页面静默丢失的严重 Bug。现已加入严格的长度校验与异常回退。

## [v3.0.0] - 2026-03-08

🔥 **史诗级架构更新：Visual Auto-Director (视觉自动导演) 上线**

本次更新彻底重构了 PPT 生成过程中的视觉处理与排版架构，从根本上解决了 AI 生成幻灯片时“贴图生硬”、“内容胡乱生成”和“网络不稳定”的三大痛点。

### ✨ 核心特性 (Core Features)

*   **多模态图库安检 (Image Selector)**：
    *   新增 `image_selector.py` 组件。系统现在会像人类编辑一样，在生成前对所有传入的参考图片进行 VLM (视觉语言模型) 语义打分和过滤。
    *   **强力去噪**：自动精准拦截包含二维码 (QR Code)、牛皮癣广告、低质网图等 junk images，保证后续生成的极高纯净度。
*   **全融合重绘架构 (All-Blend Redraw)**：
    *   彻底废弃了以往粗糙的 `overlay` (用 Python 在背景上计算方框硬贴原图) 逻辑。
    *   现在，所有通过安检的非图表类配图，都会被强制设为 `blend` 模式。系统会将原图作为 `reference_image` 投喂给生图大模型，要求其在保持原主体/数据隐喻的基础上，以统一的高级 3D/UI 质感进行**光影级别的自然重绘与融合**，彻底告别“狗皮膏药”。
*   **高压防幻觉约束 (Anti-Hallucination & Anti-Duplication Prompt)**：
    *   在 `VisualAgent` 的生图提示词中注入了极严格的负向约束。
    *   **防加戏**：明确禁止大模型在高端商务/社论风格下随意臆想并生成手表、杂志、不相关的人物或品牌 Logo。
    *   **防复读机**：针对文本排版，明确禁止大模型将同一句话或同一个要点在画面中重复渲染多次（如原本只有 2 个 bullet points，大模型却画了 4 个），强制要求点到为止。
*   **高可用自动退避机制 (LLM Fallback & Retry)**：
    *   重写了底层 `llm_client.py`，新增对 `APIConnectionError`、`Timeout` 等瞬态网络异常的全局捕获。
    *   当遭遇并发限流 (429) 或服务不可用 (503) 时，系统将自动降级切换至备用模型（如 `gemini-2.5-flash` 或备用通道），彻底解决长文生图时跑到 80% 突然崩溃前功尽弃的痛点。

### 🚀 优化 (Optimizations)

*   大幅优化了 `NarrativeAgent` 在生成逐页 JSON 计划（Phase 2）时的长文本截断逻辑（`outline_content_limit` 从 16000 降至 8000），在保证上下文连贯的前提下，极大地减轻了 LLM 输出大段 JSON 时的掉线率。

## [v2.5.2] - 2026-03-06

### ✨ 新特性 (New Features)

*   **真·PPT模板页生成**: 废弃了之前仅生成一张纯色渐变图作为 Bonus 的简陋方案。现在，系统会在每次生成的 PPT 末尾，自动追加**两张带有原生、可编辑结构**的「空白版式模板页」：
    *   **自由编辑页 (单栏)**：带有主题色的高级边框装饰线、操作引导标签，以及预设好当前风格字体、字号、颜色的「大标题文本框」和带有半透明微遮罩效果的「正文文本框」。
    *   **图文分栏页 (双栏)**：左侧为预设好的观点文本框，右侧自带居中对齐的真实占位色块与图像插入提示 (`🖼️ 拖拽图片至此`)，方便用户直接补充内容。

### 🐛 修复 (Bug Fixes)

*   **占位符文本颜色对比度穿透修复**: 修复了当使用浅色背景风格时，系统盲目使用调色板的第 4 顺位颜色（通常也是浅色），导致模板占位文本与背景融为一体“隐形”的 Bug。
    *   新增了**「文字与背景亮度对比度实时校验算法 (Luminance Contrast)」**。
    *   如果算法检测到指定的次要文本色与背景色亮度差值 `< 50`，系统将强制干预，并根据当前背景色的深浅，智能地将文本覆盖为极高对比度的深灰色 (`#666666` / `#222222`) 或亮灰色 (`#CCCCCC` / `#FFFFFF`)，确保所有占位文字绝对清晰可见。

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
