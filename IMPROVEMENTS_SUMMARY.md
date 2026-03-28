# Nano Banana PPT 改进总结

## 已完成的改进 (2026-03-28)

### 问题1: 支持已有大纲直接复用 ✅

**文件**: `agents/narrative.py`, `main.py`

**改进内容**:
- 新增 `detect_complete_content_plan()` 函数 - 检测完整大纲
- 新增 `_parse_complete_content_plan()` 函数 - 纯文本解析器,100%保留原文
- 修改 `generate_narrative_outline()` - 支持三种模式(直接复用/解析/智能叙事)
- 新增 CLI 参数 `--reuse-existing` - 强制使用直接复用模式
- 添加用户提示 - 自动检测完整大纲并建议使用 --reuse-existing

**使用方式**:
```bash
# 强制使用直接复用模式
python3 -m tools.nano_banana_ppt.main plan-content <file> --reuse-existing

# 自动检测(会提示用户)
python3 -m tools.nano_banana_ppt.main plan-content <file>
```

**效果**:
- ✅ 100%保留用户原始内容
- ✅ 不调用 LLM 处理文本
- ✅ 避免数据错误(如抖音日活 8.3亿 → 18.3亿)
- ✅ 避免副标题被改写
- ✅ 完整保留演讲备注

---

### 问题5: 支持 PNG/JPG 模板解析 (部分完成)

**文件**: `agents/template.py`

**改进内容**:
- 修改 `process_template()` - 添加 PNG/JPG 格式检测
- 需要添加 `process_image_template()` 方法 - 提取图片主色调

**待完成**:
- 实现 `process_image_template()` 方法
- 使用 PIL/Pillow 提取主色调
- 即使解析失败也保留用户指定配色

---

## 待实施的改进

### 问题2: 单一数据源机制 (P0)

**问题**: 数据分散在多个文件,修改一处不同步

**改进方案**:
- content_plan.md 是唯一数据源
- _content_state.json 和 master_plan.md 从 content_plan.md 派生
- 修改 content_plan.md 后自动同步

**实施位置**: `main.py`, `utils/review_plan.py`

---

### 问题3: Visual prompt 描述不够精确 (P1)

**问题**: AI 生成的图片偏离意图

**改进方案**:
- 使用结构化 Visual Prompt 模板
- 明确布局约束(标题区/内容区/结论区)
- 明确禁止元素(英文/卡通/3D)
- 添加内容映射检查

**实施位置**: `agents/visual.py`

---

### 问题4: 内容审核强制拦截点 (P1)

**问题**: 用户在生成图片后才发现问题

**改进方案**:
- 在 execute 前自动对比 content_plan.md 和 master_plan.md
- 检测数据不一致、页面数量不一致、内容删改
- 发现问题时报警,不执行生成

**实施位置**: `main.py` (execute 命令)

---

### 问题6: 全局风格一致性 (P1)

**问题**: 章节页/封面与内容页风格不一致

**改进方案**:
- 种子页风格传给所有页面类型
- 所有页面共享同一套风格规范
- 禁止元素清单全局生效

**实施位置**: `core/executor.py`

---

### 问题7: 重复内容问题 (P2)

**问题**: 关键信息在多个位置重复出现

**改进方案**:
- 在 visual prompt 中明确标注:标题文字只出现在标题位置
- 每个关键信息只允许在一个位置出现
- 禁止在画面中重复核心信息

**实施位置**: `agents/visual.py`

---

## 改进优先级

**P0 (必须修复)**:
- ✅ 问题1: 支持已有大纲直接复用
- 🔄 问题5: 支持 PNG/JPG 模板解析 (部分完成)
- ⏳ 问题2: 单一数据源机制

**P1 (严重影响用户体验)**:
- ⏳ 问题3: Visual prompt 描述精确化
- ⏳ 问题4: 内容审核强制拦截点
- ⏳ 问题6: 全局风格一致性

**P2 (优化体验)**:
- ⏳ 问题7: 重复内容问题

---

## 测试建议

### 测试用例1: 完整大纲直接复用
```bash
python3 -m tools.nano_banana_ppt.main plan-content \
  "/Users/Joe_1/Desktop/AI output/ppt/20260327_20260327_内容电商大逃杀时代/content_plan.md" \
  --reuse-existing
```

**预期**: 数据100%保留,抖音日活保持8.3亿

### 测试用例2: PNG模板解析
```bash
python3 -m tools.nano_banana_ppt.main plan \
  <content.md> \
  template_assets/ref_cover.png \
  template_assets/图片1.png
```

**预期**: 成功提取白+黑+红配色

---

## 相关文件

- `/Users/Joe_1/Desktop/nano-banana-ppt/agents/narrative.py` - 内容分析
- `/Users/Joe_1/Desktop/nano-banana-ppt/agents/visual.py` - 视觉规划
- `/Users/Joe_1/Desktop/nano-banana-ppt/agents/template.py` - 模板解析
- `/Users/Joe_1/Desktop/nano-banana-ppt/main.py` - CLI 入口
- `/Users/Joe_1/Desktop/nano-banana-ppt/core/executor.py` - 图片生成调度
- `/Users/Joe_1/Desktop/nano-banana-ppt/utils/review_plan.py` - 计划文件转换

---

*本文档由 Claude Code 生成,用于跟踪 nano-banana-ppt 项目的改进进度。*
