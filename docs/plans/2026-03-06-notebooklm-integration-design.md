# Nano Banana PPT & NotebookLM Integration Design

## 概述 (Overview)

为了满足高定制化（原生 Nano Banana 引擎）与高效内容提炼（NotebookLM 引擎）的双重需求，设计了两套协同又独立的 Skill：
1. **Nano Banana PPT 升级版 (集成方案一)**：在原生流程的 `plan` 阶段，作为“后置扩展（Optional Co-pilot）”引入 NotebookLM 大纲。
2. **独立的 NotebookLM 自动化 Skill**：一个全能型的“全家桶”工具，专门用于满足用户“快速生成播客/信息图/原生 NotebookLM PPT/测验”等轻量级、低定制化需求。

---

## 核心设计 1：升级 `nano-banana-ppt` Skill (集成方案一)

### 目标 (Goal)
保持现有的高品质生图与排版流程（Phase 2 `execute`）不变，但在 Phase 1 `plan` 之后，给予客户更多选择，利用 NotebookLM 提供备选的叙事大纲。完全剥离播客/思维导图等附加功能，保持 `nano-banana-ppt` 专注。

### 交互流程 (Interactive Workflow)
1. **Style Consultation**: 询问用户风格意向（保持不变）。
2. **Phase 1: Plan**: 运行原生 `plan` 命令生成原生的大纲（`plan_for_review.md`）。
3. **The "Co-pilot" Question (新增)**:
   - Agent 主动询问：*“原生叙事大纲已为您生成。您是否需要我同时调用 NotebookLM 看看它原生的叙事大纲会怎么做？”*
   - 同时附上温馨提示：
     - *(a) 若您选择需要，需确保已配置 NotebookLM 相关后台接口。*
     - *(b) 若未配置过，首次配置可能需耗时 3-5 分钟。*
     - *(c) 若已配置好，请直接确认。*
4. **NotebookLM 预演 (如果用户同意)**:
   - 告知用户：“好的，请稍等，正在通过 NotebookLM 消化资料并生成备选大纲...”
   - 后台操作：
     - `notebooklm create "PPT Backup Outline"`
     - `notebooklm source add <用户的输入文件/URL>`
     - 等待源文件就绪 (`source wait`)
     - 使用 `notebooklm generate report --format briefing-doc` (或类似指令) 让 NotebookLM 产出大纲内容。
   - 呈现双轨结果：将原生的 `plan_for_review.md` 与 NotebookLM 生成的备选大纲（需保存为独立的物理文件，例如 `notebooklm_outline.md` 或在终端打印对比）并排呈现给用户。
5. **Human Review & Fusion (人类审核与融合)**:
   - 核心：用户必须与模型交互，说明最终大纲怎么修改（选A，选B，或者结合）。
   - **关键约束 (Critical Constraint)**：无论用户怎么选，Agent 必须将最终确认的内容固化为符合原生格式的 `plan_for_review.md`。
6. **Phase 2: Execute**:
   - **绝对禁止** 在这里调用 NotebookLM 的生图或 PPT 生成功能。
   - 用户确认最终 `plan_for_review.md` 后，严格调用原生 `execute` 走高质量生图（Gemini）和拼装环节。

---

## 核心设计 2：新增 `notebooklm-automation` Skill (独立工具)

### 目标 (Goal)
提供一个封装好 `notebooklm-py` 命令行能力的全能助手。**所有的衍生功能（播客、信息图、原生 PPT 等）全部收敛到这个独立的 Skill 中。**

### 支持的意图与触发场景 (Supported Intents)
- “帮我把这些资料做成一期播客 (Audio Overview)”
- “帮我从这个文档生成一份思维导图 (Mind Map) 和复习卡片 (Flashcards)”
- “我不在乎排版，用这个 PDF 给我也弄个原生的 NotebookLM PPT (Slide Deck)”
- “帮我对这个主题做个 Deep Research”

### 自动化工作流 (Automated Pipelines)
该 Skill 将指导 Agent 使用子代理（Subagents）或并行工具调用来处理耗时任务：
1. **鉴权检查**: 执行任何任务前，检查 `notebooklm status`。
2. **资料入库**: 自动创建 Notebook，添加多个源文件/链接。
3. **异步等待**: 对于耗时操作（如 `source wait`, `artifact wait`，尤其是播客/视频生成可能需要十几分钟），教导 Agent 如何派生一个后台 Subagent（`general-purpose`）去守候任务并自动下载，而不阻塞主对话。
4. **批量下载**: 等待完成后，自动调用 `download` 将 `.mp3` / `.json` / `.pptx` 等文件保存到本地特定目录供用户直接取用。

### 优劣势与定位
- **定位**：效率工具，用于快速知识摄取、音频转换、快速出稿。
- **限制说明**：该 Skill 中生成的 PPT 是 NotebookLM 原生的，带水印且不可深度定制视觉。如果用户提出修改样式的要求，Agent 应建议用户转用 `nano-banana-ppt` Skill。

---

## 下一步行动计划 (Implementation Plan)

1. **修改现有的 `SKILL.md` (nano-banana-ppt)**：
   - 在 Workflow 中插入“The Co-pilot Question”分支。
   - 增加对“双版本融合”并最终统一到 `plan_for_review.md` 格式的强制约束。
   - 强化 `execute` 阶段只能使用原生命令的说明。

2. **创建新的 `SKILL.md` (notebooklm-automation)**：
   - 在 `~/.cursor/skills/notebooklm-automation/SKILL.md` (或指定目录) 建立新文件。
   - 吸收 `notebooklm-py` 的 README 核心精华，编写适用于 Agent 的自主调度指南（尤其是利用 Subagent 处理长耗时任务的 SOP）。