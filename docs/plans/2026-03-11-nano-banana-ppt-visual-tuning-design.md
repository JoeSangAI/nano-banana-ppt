# Nano Banana PPT 视觉统筹与双阶确认工作流重构设计 (Design Doc)

## 1. 背景与痛点 (Context & Problem Statement)

当前 `nano-banana-ppt` 的生成流程存在以下痛点：
1. **AI 塑料感与审美疲劳**：由于缺乏全局的“懂设计”的统筹机制，底层模型在生成图片时会滥用具象且老套的 AI 元素（如发光连线、漏斗、赛博大脑、数据中枢），导致画面花里胡哨、意义不明，缺乏现代 B2B 或高级路演所需的极简与克制。
2. **决策维度耦合**：当前的 `plan_for_review.md` 将“文案大纲”与“视觉提示词”混合在一起让用户一次性确认。这导致用户难以专注审阅文案，且对纯文字的“视觉风格描述”缺乏直观感知。
3. **有模板时的视觉冲突**：在用户提供模板时，如果 AI 仍按原有逻辑生成大量具象图形，会破坏模板的干净版式。同时，原生贴图（Native Images）与 AI 辅助图形的融合（Blend）逻辑不够精细。

## 2. 核心架构重构 (Core Architectural Shifts)

为了彻底解决上述问题，我们将现有的 Pipeline 重构为**“双总监机制 (Dual-Director System)”**与**“双阶确认流程 (Two-Stage Review Process)”**。

### 2.1 内容确认阶段（文案总监 / Copywriter Director）
**目标**：专注敲定“屏幕上写什么”以及“演讲者说什么”。
- **动作**：
  1. 用户输入源文档（Markdown/文本）或通过多轮对话定下大纲。
  2. Narrative Agent（内容总监）分析并提取出纯文字维度的 PPT 结构（标题、正文结构、演讲备注）。
  3. **人类确认点 1**：生成并呈现一份纯粹的 `content_plan.md`，仅包含逻辑框架和文字（包括原生贴图的预留位置）。
- **价值**：用户在这个阶段不需要思考“长什么样”，只需确认“逻辑对不对、字准不准”。

### 2.2 视觉确认阶段（视觉总监 / Visual Art Director）
**目标**：统筹全局视觉审美，剔除低劣 AI 陈词滥调，根据具体语境（如历史、科技、消费）寻找最贴切的视觉意象（Visual Motif），并通过“打样”建立直观预期。
- **动作**：
  1. 内容确认后，Visual Art Director Agent 登场。它会根据大纲内容和受众，向用户提供 2-3 个专业的视觉风格建议（不局限于极简，而是寻找最契合主题的高级审美，如 `Cinematic Roman Marble & Sand`, `Liquid Glass Minimalist` 等）。
  2. **设定视觉宪法 (Design System Manifesto)**：视觉总监会输出一套全局强约束规范，包含：
     - `visual_motif`（核心视觉意象）：确立整套幻灯片的意境（如“史诗般的古代遗迹质感”或“深色霓虹光晕”）。
     - `composition_rules`（构图与留白法则）：强制留白比例与排版分布，确保文字阅读的清晰度。
     - `color_treatment`（色彩处理）：背景色、强调色、材质光影等。
     - `cliche_avoidance`（陈词滥调排除名单 / The "No-Plastic-AI" Ban List）：**核心去塑料感机制。视觉总监会敏锐地将与当前主题相关的“懒惰隐喻”列入黑名单（Negative Prompts）。**例如，禁止发光大脑、数字雨、3D漏斗、机器人握手、卡通小人等廉价感元素，强制要求电影级、高质感的真实隐喻。
  3. **打样预览 (Optional Look & Feel Prototyping)**：
     - 视觉总监向用户提供选择：“*为了确保风格符合您的预期，您可以选择让我先为您生成 1-2 页的样图（如封面页和极具代表性的内页）。如果您觉得没必要，我们也可以直接生成全案。*”
     - **人类确认点 2**：这是非强制性的（降低选择负担）。如果用户选择直接生成，系统挂载当前这套视觉规范直接跑全流程；如果用户选择打样，系统渲染样图反馈给用户，用户可微调风格提示词直到满意。
  4. **全量生成**：视觉确认通过后，系统挂载这套经过验证的“视觉宪法”，进入无人值守的全量生成与组装阶段。

### 2.3 模板与原生元素的融合策略 (Template & Asset Blending)

当用户提供了 `template_file`（有模板模式）或内容中包含 `native_images`（原生贴图）时，视觉总监将采取智能同化与融合策略，而**不再是简单地将 AI 降级为抽象底纹**：
- **受控的模板共舞 (Controlled Thematic Styling within Templates)**：即使有公司标准模板，AI 依然可以生成具象且宏大的插图（如角斗士、汽车模型、行业场景）。但视觉总监会强制要求：
  - **色彩与质感同化**：生成的插图必须服从模板的主色调（例如，将古罗马斗兽场渲染出带有企业蓝色调的高质感）。
  - **安全的构图让位 (Safe Zones)**：根据模板的版式（如左侧有固定文字区），强制插图在对应的位置使用纯色或干净的渐变（模板底色）过渡，确保主体插画不会干扰模板原有的排版规范。
- **原生贴图的智能 Blend**：对于需要保留的原生贴图（如应用截图、复杂数据表原图），视觉总监在生成提示词时，会强制规划出**硬性留白区 (Hard Negative Space)**。并使用诸如“纯色底”、“柔和边缘过渡”的指令，使得后续 Python-pptx 贴入原生图时，能与 AI 背景无缝融合，拒绝粗暴的“贴膏药”效果。

## 3. 流程图变迁 (Workflow Diagram)

### 变更前 (Legacy Pipeline)
```text
[Input] -> (Narrative & Visual Prompting) -> [plan_for_review.md] -> (User Reviews ALL at once) -> [Execute Generation] -> Output
```

### 变更后 (New Dual-Director Pipeline)
```text
[Input] 
  |
  v
[1. Copywriter Director] -> Extracts pure text & logic
  |
  v
[📝 Human Review 1: Content Plan] -> User approves logic & text
  |
  v
[2. Visual Art Director] -> Proposes styles + Creates Design Manifesto (Cliche Ban)
  |
  v
[🖼️ Optional Prototyping] -> User chooses whether to see 1-2 sample slides or proceed directly
  |
  v
[👀 Human Review 2: Visual Style] -> User approves the Look & Feel
  |
  v
[Execute Generation] -> Applies global manifesto to all slides -> Output
```

## 4. 后续实现计划 (Next Steps)

此设计将拆解为具体的代码实现计划：
1. **解耦 Plan 逻辑**：拆分原有的 `plan` 命令，将其改写为两阶段交互或输出两个分离的审查文件（`content_plan.md` 与 `style_manifesto.json`）。
2. **实现 Art Director Agent**：编写全新的 LLM Prompt 链，专门用于生成并强校验全局视觉约束（特别是黑名单机制）。
3. **增加打样 (Prototype) 命令**：在 CLI 中增加快速渲染指定页码的功能，支持预览循环。
4. **重构底图生成 Prompt**：在生成最终 `visual_prompt` 时，强制注入 Art Director 的 Manifesto，并在有模板时自动切换为底纹模式。
