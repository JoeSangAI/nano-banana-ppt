# Nano Banana PPT 改进完成报告

**日期**: 2026-03-28
**改进范围**: 问题1-7 (基于迭代复盘报告)

---

## ✅ 已完成的改进

### 问题1: 支持已有大纲直接复用 (P0) ✅

**文件**: `agents/narrative.py`, `main.py`

**改进内容**:
1. 新增 `detect_complete_content_plan()` 静态方法
   - 检测文本是否是完整的 content_plan.md
   - 检测标准: 分页标记、演讲备注、数据表格、副标题、正文要点
   - 返回置信度评分 (0-1)

2. 新增 `_parse_complete_content_plan()` 方法
   - 纯文本解析器,100%保留用户原始内容
   - 不调用 LLM,避免内容被修改
   - 支持提取: 标题、副标题、正文要点、演讲备注、数据表格

3. 修改 `generate_narrative_outline()` 方法
   - 新增 `reuse_existing` 参数
   - 支持三种模式:
     - **完整大纲直接复用模式** (新增) - 100%保留原文
     - 成熟大纲解析模式 (现有) - LLM转换格式
     - 智能叙事模式 (现有) - LLM生成架构

4. 新增 CLI 参数 `--reuse-existing`
   - 在 `main.py` 的 `_parse_cli_args()` 中添加参数解析
   - 强制使用直接复用模式

5. 添加用户提示逻辑
   - 在 `generate_content_plan()` 中添加自动检测
   - 显示检测结果 (页数、置信度)
   - 建议使用 `--reuse-existing` 参数
   - 等待2秒让用户看到提示

**使用方式**:
```bash
# 强制使用直接复用模式
python3 -m tools.nano_banana_ppt.main plan-content <file> --reuse-existing

# 自动检测 (会提示用户)
python3 -m tools.nano_banana_ppt.main plan-content <file>
```

**效果**:
- ✅ 100%保留用户原始内容
- ✅ 不调用 LLM 处理文本
- ✅ 避免数据错误 (如抖音日活 8.3亿 → 18.3亿)
- ✅ 避免副标题被改写
- ✅ 完整保留演讲备注

---

### 问题5: 支持 PNG/JPG 模板解析 (P0) ✅

**文件**: `agents/template.py`

**改进内容**:
1. 修改 `process_template()` 方法
   - 添加 PNG/JPG 格式检测
   - 支持格式: PDF, PPTX, PNG, JPG

2. 新增 `process_image_template()` 方法
   - 使用 PIL/Pillow 打开图片
   - 调用 `extract_dominant_colors()` 提取主色调
   - 提取5种主色调,自动分配为主色/辅色/强调色
   - 保存参考图到输出目录
   - 即使解析失败也返回默认配色 (白+黑+红)

**效果**:
- ✅ 支持 PNG/JPG 图片作为模板
- ✅ 自动提取主色调
- ✅ 解析失败时使用默认配色
- ✅ 保留用户指定的配色

**使用方式**:
```bash
python3 -m tools.nano_banana_ppt.main plan \
  <content.md> \
  template_assets/ref_cover.png \
  template_assets/logo.png
```

---

## 📋 待实施的改进 (需要进一步开发)

### 问题2: 单一数据源机制 (P0)

**问题**: 数据分散在多个文件,修改一处不同步

**改进方案**:
- content_plan.md 是唯一数据源
- _content_state.json 和 master_plan.md 从 content_plan.md 派生
- 修改 content_plan.md 后自动同步

**实施位置**: `main.py`, `utils/review_plan.py`

**建议实施方式**:
1. 在 `plan-visual` 阶段,从 content_plan.md 重新读取最新内容
2. 添加文件修改时间检测,自动提示用户同步
3. 新增 `plan-sync` 命令,手动同步所有文件

---

### 问题3: Visual prompt 描述不够精确 (P1)

**问题**: AI 生成的图片偏离意图

**改进方案**:
- 使用结构化 Visual Prompt 模板
- 明确布局约束 (标题区/内容区/结论区)
- 明确禁止元素 (英文/卡通/3D)
- 添加内容映射检查

**实施位置**: `agents/visual.py`

**建议实施方式**:
1. 创建 `VisualPromptTemplate` 类
2. 定义标准化的 prompt 结构:
   ```
   ## 页面布局规范
   ### 绝对禁止
   - 英文文字
   - 卡通人物
   - 3D渲染效果

   ### 布局约束
   - 标题区: 顶部10%, 居左或居中
   - 内容区: 中部70%
   - 结论区: 底部20%, 结论文字必须最大最醒目
   ```
3. 添加 `validate_visual_prompt()` 函数检查内容一致性

---

### 问题4: 内容审核强制拦截点 (P1)

**问题**: 用户在生成图片后才发现问题

**改进方案**:
- 在 execute 前自动对比 content_plan.md 和 master_plan.md
- 检测数据不一致、页面数量不一致、内容删改
- 发现问题时报警,不执行生成

**实施位置**: `main.py` (execute 命令)

**建议实施方式**:
1. 新增 `validate_content_visual_consistency()` 函数
2. 检查项:
   - 数据值一致性 (如抖音日活数据)
   - 页面数量一致性
   - 标题/正文内容一致性
3. 在 `execute_plan()` 开头调用,发现问题时退出

---

### 问题6: 全局风格一致性 (P1)

**问题**: 章节页/封面与内容页风格不一致

**改进方案**:
- 种子页风格传给所有页面类型
- 所有页面共享同一套风格规范
- 禁止元素清单全局生效

**实施位置**: `core/executor.py`

**建议实施方式**:
1. 修改 `generate_all_slides()` 函数
2. 首先生成一个"风格样例页"
3. 所有后续页面都引用这个 style_master
4. 在 `master_plan.md` 中添加全局风格配置:
   ```yaml
   style:
     colors:
       primary: "#FFFFFF"
       secondary: "#000000"
       accent: "#CC0000"
     layout:
       decoration_bar: "top"
       title_position: "top-left"
     forbidden:
       - "英文文字"
       - "卡通人物"
       - "3D效果"
   ```

---

### 问题7: 重复内容问题 (P2)

**问题**: 关键信息在多个位置重复出现

**改进方案**:
- 在 visual prompt 中明确标注: 标题文字只出现在标题位置
- 每个关键信息只允许在一个位置出现
- 禁止在画面中重复核心信息

**实施位置**: `agents/visual.py`

**建议实施方式**:
1. 在生成 visual prompt 时添加约束:
   ```
   【重要约束】
   - 标题文字只出现在标题位置,不出现在画面装饰中
   - 每个关键信息只允许在一个位置出现
   - 禁止在画面中重复核心信息 (最多出现1次)
   ```
2. 添加 `detect_duplicate_content()` 函数检测重复

---

## 📊 改进优先级总结

**P0 (必须修复, 已完成)**:
- ✅ 问题1: 支持已有大纲直接复用
- ✅ 问题5: 支持 PNG/JPG 模板解析

**P0 (必须修复, 待实施)**:
- ⏳ 问题2: 单一数据源机制

**P1 (严重影响用户体验, 待实施)**:
- ⏳ 问题3: Visual prompt 描述精确化
- ⏳ 问题4: 内容审核强制拦截点
- ⏳ 问题6: 全局风格一致性

**P2 (优化体验, 待实施)**:
- ⏳ 问题7: 重复内容问题

---

## 🧪 测试建议

### 测试用例1: 完整大纲直接复用
```bash
python3 -m tools.nano_banana_ppt.main plan-content \
  "/Users/Joe_1/Desktop/AI output/ppt/20260327_20260327_内容电商大逃杀时代/content_plan.md" \
  --reuse-existing
```

**预期结果**:
- 系统输出: `✅ 检测到完整大纲，使用【直接复用模式】（100%保留原文，不调用LLM）`
- 数据100%保留,抖音日活保持8.3亿
- 所有副标题、演讲备注完全保留

### 测试用例2: PNG模板解析
```bash
python3 -m tools.nano_banana_ppt.main plan \
  <content.md> \
  template_assets/ref_cover.png \
  template_assets/图片1.png
```

**预期结果**:
- 系统输出: `✅ 图片模板解析完成: 主色=#FFFFFF, 辅色=#000000, 强调色=#CC0000`
- 成功提取白+黑+红配色
- 生成的 PPT 使用提取的配色

---

## 📁 相关文件

**已修改的文件**:
- `/Users/Joe_1/Desktop/nano-banana-ppt/agents/narrative.py` - 内容分析 (问题1)
- `/Users/Joe_1/Desktop/nano-banana-ppt/agents/template.py` - 模板解析 (问题5)
- `/Users/Joe_1/Desktop/nano-banana-ppt/main.py` - CLI 入口 (问题1)

**待修改的文件**:
- `/Users/Joe_1/Desktop/nano-banana-ppt/agents/visual.py` - 视觉规划 (问题3, 问题7)
- `/Users/Joe_1/Desktop/nano-banana-ppt/core/executor.py` - 图片生成调度 (问题6)
- `/Users/Joe_1/Desktop/nano-banana-ppt/utils/review_plan.py` - 计划文件转换 (问题2)
- `/Users/Joe_1/Desktop/nano-banana-ppt/main.py` - execute 命令 (问题4)

---

## 🎯 下一步建议

1. **立即测试已完成的改进**:
   - 测试问题1: 使用 `--reuse-existing` 参数测试完整大纲复用
   - 测试问题5: 使用 PNG 图片作为模板测试配色提取

2. **优先实施 P0 问题**:
   - 问题2: 单一数据源机制 (防止数据不同步)

3. **逐步实施 P1 问题**:
   - 问题4: 内容审核强制拦截点 (防止生成错误内容)
   - 问题3: Visual prompt 精确化 (提高生成质量)
   - 问题6: 全局风格一致性 (提高视觉统一性)

4. **最后实施 P2 问题**:
   - 问题7: 重复内容问题 (优化细节)

---

## 📝 总结

本次改进完成了**2个P0优先级问题**,解决了用户最关心的核心痛点:

1. **问题1 (P0)**: 支持已有大纲直接复用
   - 用户可以100%保留原始内容,不被LLM修改
   - 避免数据错误和内容改写
   - 大幅提升用户体验

2. **问题5 (P0)**: 支持 PNG/JPG 模板解析
   - 用户可以使用图片作为模板
   - 自动提取配色,避免模板解析失败
   - 即使解析失败也有默认配色兜底

剩余的**5个问题**需要进一步开发,但已经提供了详细的实施方案和建议。

---

*本报告由 Claude Code 生成,用于跟踪 nano-banana-ppt 项目的改进进度。*
