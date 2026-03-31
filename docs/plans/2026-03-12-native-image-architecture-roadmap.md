# 原生图片架构升级路线图

> 创建时间：2026-03-12
> 状态：Phase 1 已完成，Phase 2/3 待排期

---

## 背景

nano-banana-ppt 的原生图片管线存在两个严重问题：

1. **图片选了但未进入 PPT**：`generator.py` 的 `reference_images[:1]` 截断导致 blend 图片从未被发送给 Gemini API；同时 PPTX 渲染阶段 blend 图片被 `continue` 跳过。
2. **AI 自动选图质量差**：选图 prompt 门槛过低，缺乏全局去重，导致同一张泛用风景图被反复选中。

---

## Phase 1：修复 Blend 通路 + 提高选图门槛 ✅ 已完成

### 1.1 修复 `[:1]` 截断 bug
- 文件：`core/generator.py`
- 改动：`reference_images[:1]` → `reference_images[:MAX_REFERENCE_IMAGES]`（MAX=4，Gemini API 上限）
- 效果：模板风格图 + 原生融合图现在都能被发送给 Gemini

### 1.2 大幅收紧选图 prompt
- 文件：`core/image_selector.py` → `select_images_for_page()`
- 改动：
  - 默认心态从"尽量选一张"变为"默认不选"
  - 明确拒绝：通用风景/天空/氛围图、装饰性图标、章节编号图
  - 只接受：图表、数据可视化、产品实拍、人物肖像、技术图纸等不可替代的信息载体
  - 标记 `[ALREADY USED]` 的图片硬性拒绝

### 1.3 全局去重机制
- 文件：`agents/narrative.py` → `_enrich_outline_with_visual_decisions()`
- 改动：维护 `globally_selected_paths` 列表，传入选图器，避免同一张图出现在多页

### 1.4 置信度门槛提升
- 从 55 提升到 80
- 低于 80 分的自动选图结果直接丢弃

### 1.5 来源标记
- 自动选图结果标记 `source: "auto"`
- 为后续区分用户指定 vs AI 自动选图做准备

---

## Phase 2：Programmatic Compositing（程序化合成）🔜 待排期

### 动机
- Blend 模式依赖模型"重绘"参考图，在多图排版、逻辑顺序、数据精度方面不可靠
- 旧 Overlay（`add_picture`）视觉效果差（硬贴纸感）
- 需要一种"精确 + 好看"的中间方案

### 方案
1. **背景生成**：Gemini 正常生成背景，prompt 提示预留干净空间
2. **图片后处理（PIL）**：
   - 边缘羽化（Gaussian feathering）
   - 色调匹配（Color grading，使图片色温与背景协调）
   - 微妙投影（Soft drop shadow）
   - 可选圆角（Rounded corners）
3. **精确合成**：PIL 将处理后的图片合成到背景图的精确坐标位置
4. **复用 VLM 安全区**：`_calculate_dynamic_layout()` 已有的 VLM 布局计算逻辑

### 优势
- 像素级精确（原图不改）
- 多图排版无压力（每张独立合成）
- 顺序完全可控
- 100% 确定性（无模型随机性）
- 视觉质量高于 raw overlay

### 预估工作量
中等偏高（2-3 天开发 + 调参测试），主要复杂度在色调匹配算法。

---

## Phase 3：三级体系 + 用户指定图片 🔮 远期

### 最终架构

| 模式 | 触发条件 | 适用场景 |
|------|---------|---------|
| **Blend** | 单张 + 肖像/氛围 + 用户标注 `[融合]` | 人物肖像融入背景、艺术感插画 |
| **Composite** | 默认模式 | 图表、截图、产品图、多图排版 |
| **不配图** | AI 自动选图未过门槛 | 源文章杂图、装饰性图标 |

### 用户指定 vs AI 自动
- `source: "user"` → 用户在 content_plan 中手动添加的图片，置信度视为 100%，直接进入管线
- `source: "auto"` → AI 从文章中自动提取并选择的图片，必须过 80 分门槛

### 数据结构
```json
{
  "path": "/path/to/image.jpg",
  "semantic_role": "产品主界面截图",
  "integration_mode": "overlay|blend|composite",
  "source": "user|auto",
  "bounding_box": {"left": 0.55, "top": 0.15, "width": 0.4, "height": 0.7}
}
```

### content_plan 用户标记语法（待设计）
- `[融合]` → blend 模式
- `[贴图]` → composite/overlay 模式
- 默认（无标记）→ composite 模式

---

## Blend 模式能力边界（评估记录）

| 维度 | 能力评估 | 说明 |
|------|---------|------|
| 单图融合（肖像/产品） | 70-80% | 适合，五官/外形保持较好 |
| 多图精确排版（2-3张） | 30-40% | 不可靠，模型无法精确定位 |
| 逻辑顺序（步骤1/2/3） | 20-30% | 极不可靠，顺序会被打乱 |
| 图表数据保真 | 20-30% | 数字几乎一定会被改 |
| 截图文字保真 | 15-25% | 文字会模糊/乱码 |
| Logo 保真 | 40-50% | 可能变形 |

**结论**：Blend 适合单张艺术融合，不适合需要精度和多图控制的场景。Phase 2 的 Compositing 方案是解决这些限制的关键。
