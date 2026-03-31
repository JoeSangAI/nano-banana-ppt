# Visual Auto-Director Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 为 `nano-banana-ppt` 增加“自动视觉导演”能力，让用户主要只在 `plan` 阶段确认叙事，执行阶段自动完成选图、模式判断、摆位与降级处理。

**Architecture:** 在现有 `plan -> execute` 双阶段结构上，新增执行阶段的视觉决策链：候选图理解、页面级选图、模式决策、模板内摆位、生成后复核。保留 `overlay` 与 `blend` 双模式，但通过更强的模板约束和低置信度回退提升稳定性。

**Tech Stack:** Python, Gemini/OpenAI-compatible multimodal calls, `tools.nano_banana_ppt` 现有 `NarrativeAgent` / `executor` / `generator` / `review_plan` 模块。

---

### Task 1: 固化页面视觉意图字段

**Files:**
- Modify: `tools/nano_banana_ppt/agents/narrative.py`
- Modify: `tools/nano_banana_ppt/utils/review_plan.py`
- Test: `临时/测试PPT/plan.json`

**Step 1: Write the failing test**

手工准备一个最小页面 JSON，确认执行阶段需要独立使用的字段完整存在：
- 页面用途
- 推荐视觉类型
- 推荐布局模板

**Step 2: Run test to verify it fails**

Run: 手工检查现有 `plan` 输出  
Expected: 页面只有 `visual_suggestion`，缺少可机器使用的明确视觉意图字段

**Step 3: Write minimal implementation**

在 `NarrativeAgent` 的 JSON 输出规范中增加字段，例如：
- `visual_intent`
- `recommended_layout_family`
- `image_need_level`

同时让 `review_plan` 能往返读写这些字段。

**Step 4: Run test to verify it passes**

Run: 重新生成一个单页测试 plan  
Expected: 新字段出现在 plan 中，并能被 `review_plan` 正常解析

**Step 5: Commit**

暂不提交，等待用户明确要求。

---

### Task 2: 实现候选图理解器

**Files:**
- Create: `tools/nano_banana_ppt/core/image_selector.py`
- Modify: `tools/nano_banana_ppt/core/executor.py`
- Test: `临时/测试PPT/plan_overlay.json`

**Step 1: Write the failing test**

准备一个候选图列表，要求输出统一的结构化理解结果：
- `semantic_summary`
- `image_type`
- `text_density`
- `person_present`
- `overlay_score`
- `blend_score`

**Step 2: Run test to verify it fails**

Run: 直接调用尚不存在的理解器  
Expected: ImportError 或函数不存在

**Step 3: Write minimal implementation**

新增 `image_selector.py`，实现：
- 图片读取与基础元数据采集
- 调用视觉模型对每张候选图做结构化分析
- 输出标准化候选图描述对象

**Step 4: Run test to verify it passes**

Run: 对 1-2 张测试图跑理解器  
Expected: 成功输出结构化候选图理解结果

**Step 5: Commit**

暂不提交，等待用户明确要求。

---

### Task 3: 实现页面级自动选图

**Files:**
- Modify: `tools/nano_banana_ppt/core/image_selector.py`
- Modify: `tools/nano_banana_ppt/core/executor.py`
- Test: `临时/测试PPT/plan_mixed.json`

**Step 1: Write the failing test**

构造一个页面描述 + 多张候选图，要求系统输出：
- 最佳主图
- 推荐 `integration_mode`
- 选择理由
- 置信度

**Step 2: Run test to verify it fails**

Run: 页面级选图流程  
Expected: 当前系统只能用 plan 里已写死的图，无法自动排序和挑选

**Step 3: Write minimal implementation**

新增页面级排序逻辑：
- 依据 `core_message`、`visual_intent`、`narrative_role`
- 结合候选图的 `overlay_score` / `blend_score`
- 输出页面的最终选图决策

**Step 4: Run test to verify it passes**

Run: 针对单页测试  
Expected: 正确返回最优候选图与推荐模式

**Step 5: Commit**

暂不提交，等待用户明确要求。

---

### Task 4: 将自由摆位改为模板内摆位

**Files:**
- Modify: `tools/nano_banana_ppt/core/generator.py`
- Modify: `tools/nano_banana_ppt/core/executor.py`
- Test: `临时/测试PPT/plan_overlay.json`

**Step 1: Write the failing test**

复用现有稳定性测试，观察 VLM 摆位结果是否出现跨区漂移。

**Step 2: Run test to verify it fails**

Run: 连续执行 overlay / mixed 测试  
Expected: 出现左右漂移或跨语义区域摆放

**Step 3: Write minimal implementation**

增加布局模板层：
- 左文右图
- 右文左图
- 半屏融合
- 全屏弱融合

VLM 只能在模板给定的安全区内微调，不能跨模板边界。

**Step 4: Run test to verify it passes**

Run: 连续执行 overlay / mixed 稳定性测试  
Expected: 图片位置波动缩小，不再跨区

**Step 5: Commit**

暂不提交，等待用户明确要求。

---

### Task 5: 锁定混合模式区域

**Files:**
- Modify: `tools/nano_banana_ppt/core/generator.py`
- Modify: `tools/nano_banana_ppt/core/executor.py`
- Test: `临时/测试PPT/plan_mixed.json`

**Step 1: Write the failing test**

针对同页 `blend + overlay` 的 case，检查：
- `blend` 是否仍被后贴图
- `overlay` 是否跑入 `blend` 主视觉区

**Step 2: Run test to verify it fails**

Run: mixed 模式连续执行  
Expected: 至少一轮中出现 overlay 漂移或区域冲突

**Step 3: Write minimal implementation**

为混合模式增加：
- `blend_reserved_region`
- `overlay_allowed_region`
- 区域冲突时的优先级规则

**Step 4: Run test to verify it passes**

Run: mixed 模式连续执行至少 5 次  
Expected: `overlay` 不再跨到 `blend` 区域，`blend` 不再被二次贴图

**Step 5: Commit**

暂不提交，等待用户明确要求。

---

### Task 6: 加入低置信度自动降级

**Files:**
- Modify: `tools/nano_banana_ppt/core/image_selector.py`
- Modify: `tools/nano_banana_ppt/core/executor.py`
- Test: `临时/测试PPT/plan.json`

**Step 1: Write the failing test**

构造低相关候选图，要求系统不要硬选错图。

**Step 2: Run test to verify it fails**

Run: 页面级选图  
Expected: 当前逻辑会默认使用已有图，而不是主动回退

**Step 3: Write minimal implementation**

实现自动回退规则：
- 低置信度选图：不用图或改抽象背景
- 低置信度模式：回退到 `overlay`
- 低置信度摆位：回退到模板默认安全区

**Step 4: Run test to verify it passes**

Run: 低相关测试页  
Expected: 系统不再强行选错图

**Step 5: Commit**

暂不提交，等待用户明确要求。

---

### Task 7: 增加生成后视觉复核

**Files:**
- Modify: `tools/nano_banana_ppt/core/generator.py`
- Modify: `tools/nano_banana_ppt/core/executor.py`
- Test: `临时/测试PPT/*.json`

**Step 1: Write the failing test**

准备一页容易压字或错误摆位的测试样例。

**Step 2: Run test to verify it fails**

Run: 当前生成流程  
Expected: 生成完成后没有自动复核与回退机制

**Step 3: Write minimal implementation**

在生成完成后加入轻量视觉检查：
- 是否压字
- 是否偏离目标区域
- 是否主体过小/过大
- 是否与页面语义冲突

失败时自动重试一次或回退到保守布局。

**Step 4: Run test to verify it passes**

Run: 执行测试页  
Expected: 能识别明显问题并执行自动回退

**Step 5: Commit**

暂不提交，等待用户明确要求。

---

### Task 8: 做稳定性回归测试

**Files:**
- Modify: `临时/测试PPT/plan.json`
- Modify: `临时/测试PPT/plan_overlay.json`
- Modify: `临时/测试PPT/plan_mixed.json`
- Test: `临时/测试PPT/*.pptx`

**Step 1: Write the failing test**

定义回归测试矩阵：
- `blend` x 5
- `overlay` x 5
- `mixed` x 5

**Step 2: Run test to verify it fails**

Run: 连续批量执行  
Expected: 旧逻辑中 mixed 模式存在摆位不稳定

**Step 3: Write minimal implementation**

在前述任务完成后，只补充测试脚本或执行命令，不再新增功能。

**Step 4: Run test to verify it passes**

Run: 批量稳定性测试  
Expected: 成功率高，且 mixed 模式不再明显跨区漂移

**Step 5: Commit**

暂不提交，等待用户明确要求。

---

## Execution Handoff

Plan complete and saved to `docs/plans/2026-03-07-visual-autodirector-plan.md`. Two execution options:

**1. Subagent-Driven (this session)** - 我在当前会话里按任务逐个实现并验证

**2. Parallel Session (separate)** - 你开一个新会话，按这份计划并行推进

如果你愿意，我建议直接选 **1**，先从“锁定 mixed 模式里的 overlay 区域”开始，因为它收益最大、风险最小。
