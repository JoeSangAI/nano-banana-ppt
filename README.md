# 🍌 Nano Banana PPT

**基于大模型的高级全自动 PPT 生成引擎（专为 Cursor/AI Agent 设计的 Skill）**

这是一个致力于“消除丑陋幻灯片”的开源工具。它不仅仅是将文本塞进模板里，而是通过多智能体（Multi-Agent）协作，**像一个真正的人类策划与视觉设计师一样**，帮你把长篇文档转化为逻辑严密、极具美感的高级 PPT。

无论你是通过 Cursor 这样的 AI IDE 对它下达自然语言指令，还是作为开发者在服务器上部署，它都能为你交付媲美专业发布会的演示文稿。

---

## 🌟 核心亮点与优势 (Why Nano Banana PPT?)

### 1. 🧠 精心打磨的叙事逻辑 (Narrative First)
*   **深度内容重构**：市面上的工具往往只是把文章按段落切碎，而我们内置了 `NarrativeAgent`。它会像专业咨询顾问一样分析你的长文，梳理出 SCQA（情境-冲突-问题-解答）或“英雄之旅”等骨架，确保 PPT 逻辑严密、富有说服力。
*   **双阶段审阅（白盒生成）**：拒绝黑盒式的“一键开盲盒”。它会先生成一份人类可读的 `plan_for_review.md` 大纲。你可以提前预览每页的标题、金句、甚至是配图思路，确认这正是你想表达的内容后，再让 AI 真正开始耗费算力去渲染图片。
*   **自带“演讲者备注”**：它会自动把详细的业务论述藏在 PPT 的“演讲者备注（Speaker Notes）”里，而让屏幕上的文字保持极其精简的“金句”状态，彻底告别“字满为患”。

### 2. 🎨 极致的风格与模板系统 (Aesthetic Excellence)
*   **自带 12+ 高级内置风格**：系统原生内置了极高品质的设计流派。无论是苹果发布会风（`apple_keynote`）、温润知性的 Claude 风（`claude_minimalist`），还是新粗野主义（`neo_brutalism`）、科技液态玻璃（`liquid_glass`）、甚至新中式国潮，只需一句口令即可调用。
*   **智能模板克隆 (Style Cloning)**：如果你公司有现成的 PDF/PPTX 模板，扔给它！`TemplateAgent` 会自动提取其中的色彩规范（Palette）、字体组合和版式基调，克隆出一个完美适配的 PPT。
*   **AI 无限铸模 (AI Minting)**：既没有模板也不想用内置？只要描述你想要的 Vibe（比如“赛博朋克霓虹灯的商业计划书”），AI 会实时为你铸造一套全新的色彩与视觉系统。
*   **附赠“真·可编辑模板页”**：在生成完毕的 PPT 最后，系统会智能追加两张带有原生 UI 边框、排版标签、占位图片框的**「空白可编辑模板页」**。并且自带智能亮度对比度检测，确保客户拿去直接输入文字时，配色与排版完全一致且清晰。

### 3. 👁️ 多模态视觉黑科技 (VLM Semantic Layout)
*   **大模型排版“长眼了”**：当你在 PPT 中插入自己的数据图表或配图时，传统的工具经常会挡住背景里的关键文字。本工具会调用 Gemini 的视觉能力（VLM）去**“看”**一眼刚刚生成的底图，精准找到留白安全区，完美嵌入你的原生图片（拒绝变形与遮挡）。

### 4. 🌍 极强的工作流集成与兼容性 (Ecosystem Ready)
*   **企业品牌植入**：原生支持传入公司 Logo 文件，系统会根据页面构图智能将其安放在最合适的角落（支持透明度处理）。
*   **全场景本地与网络图片支持**：不论是本地图片、还是网络链接（http/https），甚至是各种网页里抓下来的 `WebP` 格式，都会自动下载转换并完美嵌入到 PPTX 中，作为图文混排的绝佳素材。
*   **高度适配 Cursor 与 Claude Code**：核心依赖极少，不依赖重量级的本地浏览器环境或复杂的沙盒。非常容易作为 Skill 配置给 Cursor 的 Agent 或终端里的 Claude Code 引擎使用，轻松实现“对话式生 PPT”。

---

## 🚀 如何安装与使用 (For 普通用户 & Cursor / Claude Code 玩家)

如果你不想配置复杂的开发环境，仅仅是想在 Cursor 或 Claude Code 这样的 AI 编程助手里使用它，这是最简单的玩法。

### 第 1 步：配置你的大模型 API 密钥
本工具底层使用 Google 的极速且强大的 Gemini 模型。你需要在电脑的终端或项目根目录的 `.env` 文件中配置以下环境变量（建议使用 OpenAI 兼容格式的转发 API，性价比极高）：
```bash
export OPENAI_API_KEY="sk-你的API密钥"
export OPENAI_API_BASE="https://你的API代理地址/v1"
```

### 第 2 步：安装 Cursor Skill
1. 将本项目 clone 到本地，或者直接把 `nano_banana_ppt` 文件夹放进你的工作区。
2. 在 Cursor 中，把本项目的 `.cursor/skills/nano-banana-ppt/SKILL.md` 内容复制到你自己的 Agent 记忆库或 Cursor Rules 中。
3. 确保你的 Python 环境装了这几个包：`pip install openai python-pptx pillow pymupdf requests`

### 第 3 步：直接对 AI 说话！
你现在可以直接在 Cursor 的聊天框里对 AI 这样下达指令：

> 🗣️ *"使用 nano-banana-ppt 技能，帮我把这份 `商业计划书.md` 转换成一份 PPT。风格我想要 'liquid_glass'（液态玻璃），并且在右上角加上我的公司 `logo.png`。"*

**AI 的工作流将会是这样的：**
1. **生成大纲**：AI 会先阅读文档，并在你的文件夹里生成一个 `plan_for_review.md`。
2. **人类确认**：AI 会停下来问你：“大纲和分页规划好了，你看这个叙事逻辑满意吗？”
3. **一键生成**：当你回复“没问题，开始生成”后，它就会开始跑图并最终输出一个精美的 `.pptx` 文件给你。

---

## 💻 开发者与命令行指南 (For Developers)

如果你想在服务器上跑批处理，或者想二次开发，请看这里。

### 核心目录结构
```text
nano_banana_ppt/
  agents/           # AI 代理群 (NarrativeAgent, VisualAgent, TemplateAgent 等)
  core/             # 核心逻辑 (PPTX 生成器、执行器)
  utils/            # 实用脚本 (高清重绘、修补等)
  main.py           # 统一 CLI 入口
```

### CLI 命令行调用

**阶段一：生成审阅计划 (Phase 1)**
```bash
python3 -m nano_banana_ppt.main plan "content.md" [template.pdf] [logo.png] [output_name] --style claude_minimalist
```
*这会生成一个 `plan_for_review.md`。你可以手动打开这个 Markdown 修改每页的标题或决定某页应该用什么图表。*

**阶段二：执行生成与组装 (Phase 2)**
```bash
python3 -m nano_banana_ppt.main execute output/ppt/your_project_dir --resolution 1K
```

**独立生图与高清放大 (Upscale)**
如果你对 PPT 里某几张图的清晰度不满意，或者想用于印刷：
```bash
python3 -m nano_banana_ppt.main upscale output/ppt/your_project_dir --resolution 4K --slides 1 3 5
```

---

## 📜 更新日志 (Changelog摘要)

详细更新请查看 [CHANGELOG.md](./CHANGELOG.md) 

### [v2.5.2] - 2026-03-06
*   ✨ **真·PPT模板页生成**: 每次生成 PPT 会在末尾追加两张（单栏/双栏图文）带有真实原生边框、标签与可编辑文本框的「空白模板页」。
*   🐛 **对比度智能保护**: 修复浅色背景下浅色占位文本“隐形”的 Bug，引入文字与背景亮度实时校验（Luminance Contrast）算法。

### [v2.5.0] - 2026-03-05
*   ✨ **预设风格库 (Curated Style Library)**: 引入了 `Claude 风格`、`新粗野主义`、`赛博朋克` 等 12 种系统级高质量视觉风格预设。

### [v2.3.0] - 2026-03-01
*   🚀 **原生图片语义排版 (VLM Semantic Layout)**: 让大模型“睁眼”寻找完美的留白安全区，完美嵌入原生图片。

---

## 🤝 参与贡献 (Contributing)

欢迎提交 PR 让这个工具变得更好！
1. Fork 本仓库并 `git clone` 到本地
2. 创建特性分支：`git checkout -b feature/amazing-feature`
3. 提交修改：`git commit -m "feat: add amazing feature"`
4. 推送并提交 Pull Request

## ⚖️ 版权与开源协议 (License)

本项目采用 [MIT License](./LICENSE) 开源协议。
你可以自由地使用、修改和商业化分发，但请保留原作者的版权声明。

Copyright (c) 2026 桑卓豪 Joe
