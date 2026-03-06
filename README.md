# Nano Banana PPT

基于 Nano Banana 2 的全自动 PPT 生成工具。

## 目录结构

```
nano_banana_ppt/
  agents/           # AI 代理 (叙事、视觉、模版)
  core/             # 核心逻辑 (生成器、执行器)
  utils/            # 工具脚本 (修复、分析)
  main.py           # 统一入口
```

## 使用方法

### 预设风格库 (Curated Style Library)
我们在 `v2.5.0` 引入了系统级预设风格库，您可以直接在 `--style` 中使用以下名称（或其中文别名）来获取极高品质的排版与配色方案：
- **`claude_minimalist`** (Claude 风格): 温润、极简、知性。奶白色背景，优雅衬线体与无衬线体混排。
- **`neo_brutalism`** (新粗野主义): 原始、大胆、高对比。亮色背景，黑色粗边框，生硬阴影，怪诞无衬线体。
- **`japanese_aesthetic`** (日式美学 / Wabi-sabi): 禅意、侘寂。大地色系，极致留白，非对称排版。
- **`apple_keynote`** (苹果发布会风格): 极致高级。深邃纯黑背景，巨大白色无衬线字体，发光渐变。
- **`cyberpunk`** (赛博朋克): 科技、故障艺术。深蓝/纯黑底色，荧光青、品红、电光黄点缀。
- **`academic_paper`** (学术风): 严谨、专业。纯白背景，经典衬线体，正式的网格排版。
- **`liquid_glass`** (液态玻璃 / Bento): 高级科技风。半透明毛玻璃卡片，超细边框，Bento 网格排版。
- **`magazine_editorial`** (时尚杂志风): 电影级留白，优雅衬线体，不对称排版，适合品牌/人物。
- **`soft_3d_clay`** (3D 粘土风): 可爱、膨胀。马卡龙色系，哑光软材质，适合活泼轻松的场景。
- **`dark_luxury`** (黑金奢华): 高级定制。深邃背景搭配暗金线条，适合高端商务/奢侈品。
- **`traditional_chinese`** (新中式 / 国潮): 水墨意蕴。留白、朱红点缀、圆窗构图，适合文化/政务。
- **`holographic_chrome`** (全息镭射 / Y2K): 液态金属，彩虹光泽，前卫艺术。

### 1. 环境准备

确保已安装依赖：
```bash
pip install openai python-pptx pillow pymupdf requests
```

设置 API Key：
```bash
export OPENAI_API_KEY="your-key"
export OPENAI_API_BASE="https://generativelanguage.googleapis.com/v1beta/openai"
```

### 2. 一键生成 (Auto Pipeline)

这是推荐的使用方式，自动完成从文档解析到 PPT 生成的全过程。

```bash
# 仅提供内容，AI 自动设计风格
python -m nano_banana_ppt.main "your_content.md"

# 提供内容和模版 (PDF)
python -m nano_banana_ppt.main "your_content.md" "template.pdf" "output_filename"
```

### 3. 独立工具

**独立生图工具 (原 gen_image.py):**
```bash
python nano_banana_ppt/utils/image_gen.py "A futuristic city"
```

**PPT 修复工具:**
```bash
python -m nano_banana_ppt.utils.regenerate "output.pptx" "ppt_generation_plan.json"
```

## 开发指南

- **NarrativeAgent**: 负责将长文档转化为结构化的 JSON 大纲。
- **VisualAgent**: 负责将大纲转化为生图 Prompt (包含 Style Injection)。
- **TemplateAgent**: 负责解析 PDF 模版，提取 Logo 和参考图。
- **Executor**: 读取视觉计划，调用 Nano Banana 2 生成图片并组装 PPTX。

## 📜 更新日志 (Changelog)

请查看 [CHANGELOG.md](./CHANGELOG.md) 以获取完整的历史更新记录。

### [v2.5.0] - 2026-03-05
*   ✨ **预设风格库 (Curated Style Library)**: 引入了系统级高质量视觉风格预设。不仅提升了生图的一致性，还大幅优化了具体风格的美学表现。目前原生支持：
    *   `Claude 风格` (claude_minimalist)：温润、极简、知性。
    *   `新粗野主义` (neo_brutalism)：原始、大胆、高对比。
    *   `日式美学` (japanese_aesthetic)：禅意、侘寂。
    *   `苹果发布会风格` (apple_keynote)：极致高级、深邃。
    *   `赛博朋克` (cyberpunk)：科技、故障艺术。
    *   `学术风` (academic_paper)：严谨、专业。
    *   `液态玻璃` (liquid_glass)：Bento 网格、毛玻璃。
    *   `时尚杂志` (magazine_editorial)：电影级留白、优雅。
    *   `3D粘土风` (soft_3d_clay)：可爱、膨胀软材质。
    *   `黑金奢华` (dark_luxury)：高端定制、暗金。
    *   `新中式` (traditional_chinese)：水墨、国潮。
    *   `全息镭射` (holographic_chrome)：Y2K、液态金属。
    系统将通过别名（如 "claude", "新粗野主义", "wabi-sabi"）自动匹配最高质量的视觉生成指令。
*   ✨ **宽幅名人金句卡 (Wide Quote Card)**: 新增 `quote` 页面类型与专用排版模式，支持 1/3 肖像 + 2/3 巨大引言文字的经典杂志排版。
*   ✨ **Markdown 审阅灵感库**: 在 `plan_for_review.md` 中新增风格灵感提示区，允许用户在 execute 前直接挑选或修改视觉风格。

### [v2.4.0] - 2026-03-02
*   🐛 **风格一致性根本修复**: 识别并修复了导致字体、配色、版式在幻灯片间不统一的架构级 bug——`design_system` 强化为含跨页一致性强制指令的「严格设计系统」，字体字段从 `plan_for_review.md` 往返中正确保留，每页 visual prompt 新增全局大纲上下文。
*   🐛 **Content 母版覆盖范围修复**: `framework`、`flowchart`、`comparison`、`data`、`toc`、`breathing` 等信息展示类页面现已正确共享 content 母版参考图，视觉风格与内容页统一。
*   🐛 **503 错误 Fallback 修复**: LLM 调用链区分对待 `429`（配额耗尽，任务内永久跳过）与 `503`（临时高峰，仅跳过本次，下次仍重试主模型），避免 API 高峰期整套 PPT 全部降级为最简陋 prompt。
*   🐛 **`regenerate.py` 导入路径修复**: 修复 standalone 模式下因错误 import 路径导致的崩溃。

### [v2.3.0] - 2026-03-01
*   🚀 **原生图片语义排版 (VLM Semantic Layout)**: 引入强悍的多模态排版系统。利用 `gemini-3.1-pro-preview` 的视觉能力，在 AI 生成 PPT 背景后，让大模型“睁眼”寻找完美的留白安全区。
*   🚀 **完美比例与贴边对齐**: 原生图片插入时强制遵循原始长宽比 (`object-fit: contain` 逻辑)，并根据 VLM 计算的留白框自动进行视觉重心对齐（如左贴边、右贴边、完美居中），拒绝强行拉伸和错位。
*   🚀 **自动网络图片兜底**: 解析器新增对 `http/https` 图片链接的自动下载和本地路径映射支持，并自动修复 `WebP` 格式（无损转 PNG）以兼容微软 Office 引擎。
*   🚀 **母版背景储备页增强**: 最终生成的纯净背景页将严格提取并继承整套 PPT 的核心色彩配置 (`palette`) 与材质隐喻，实现无缝的临时加页支持。
*   🛠 **人类可读审核流优化**: 简化 `plan_for_review.md` 的呈现结构，移除冗余的技术元数据，原生图片预览直接采用内联 HTML 小图渲染，提升主讲人审阅体验。

### [v2.2.0] - 2026-02-28
*   🚀 **模型底座全面升级**: 代理与生图全线升级至 `gemini-3.1-pro-preview` 与 `gemini-3.1-flash-image-preview`。
*   🚀 **强化叙事提取蓝图**: 深度规划演讲节奏与情绪，支持 Briefing 意图注入，改善排版分布。
*   🚀 **双阶段自动化流**: 引入 Phase 1 (Plan) Markdown 审阅机制，确认无误后再执行 Phase 2 (Execute)。
*   🚀 **混合图表渲染系统**: 表格采用原生 PPT 渲染（可编辑），静态图表渲染为高清图片。
*   🚀 **演讲备注支持**: 自动为每页生成详尽“演讲备注”，保持屏幕文案精简。
*   🛠 **稳定性大幅提升**: 放宽超时至 600 秒（支持 50+ 页文档），最高 5 次 API 退避重试机制，并发数控制优化。
*   🐛 **修复**: 导入路径异常、不完整图片角点问题、过度生成纯要点 (bullet points) 等。

## 参与贡献 (Contributing)

欢迎提交代码让这个工具变得更好！如果你是第一次在 GitHub 参与开源项目，流程如下：

1. **Fork 本仓库**：点击右上角的 `Fork` 按钮，将代码复制到你的账号下。
2. **克隆代码**：将你账号下的仓库 `git clone` 到本地。
3. **创建分支**：`git checkout -b feature/your-feature-name`
4. **提交修改**：`git commit -m "feat: 增加某个功能"`
5. **推送到你的仓库**：`git push origin feature/your-feature-name`
6. **发起合并请求 (Pull Request)**：回到本仓库页面，点击 `New Pull Request`。

我会收到通知并 Review 你的代码，如果合适就会合并进来！

## 版权与开源协议 (License)

本项目采用 [MIT License](./LICENSE) 开源协议。
你可以自由地使用、修改和分发，但请保留原作者的版权声明。

Copyright (c) 2026 桑卓豪 Joe
