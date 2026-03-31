# Native Image Smart Semantic Layout Design

## 1. 背景与目标

目前，我们实现了基础版的单图 `native_image` 插入功能，依靠预设的枚举值（如 `right_half`）控制原图在幻灯片上的摆放，这是一种“硬编码”规则。
然而，在真实使用场景中：
1. 一页幻灯片里可能需要插入**多张原图**（例如：前后对比图、功能展示图组等）。
2. 每张图片不仅是视觉元素，更代表着**业务语义**。我们需要模型能理解**为何**要放这些图，并根据图片的语义（比如主次、对比关系、分类）来**自动推导出最佳的排版方案（尺寸与位置）**。

因此，我们需要将排版决策权部分下放给大模型，从“固定预设版式”升级为 **AI 驱动的相对坐标智能排版引擎 (Semantic Layout Engine)**。

## 2. 核心架构设计

我们采用 **“AI 提供相对坐标 + 底层代码精准渲染”** 的混合策略。

### 2.1 数据结构扩展 (支持多图与智能边界)

将原本 `slide_plan` 中的对象 `native_image` 升级为列表字段 `native_images`。
在这个列表中，除了图片路径，我们引入相对坐标引擎，即 `bounding_box`。

```json
{
  "page_num": 3,
  "type": "content",
  "text_content": { ... },
  "visual_prompt": "...",
  "native_images": [
    {
      "path": "/absolute/path/to/img1.png",
      "semantic_role": "产品A，重点展示，需要占据较大空间",
      "bounding_box": { "left": 0.05, "top": 0.1, "width": 0.4, "height": 0.8 }
    },
    {
      "path": "/absolute/path/to/img2.png",
      "semantic_role": "产品B，辅助对比，放置在右侧稍小",
      "bounding_box": { "left": 0.55, "top": 0.2, "width": 0.4, "height": 0.6 }
    }
  ]
}
```

*   **`semantic_role`**: 给 AI 规划者阅读或由 AI 自己输出，解释这张图在这个页面的业务意图是什么。
*   **`bounding_box`**: 大模型根据排版意图输出的相对坐标（取值范围 0.0 ~ 1.0）。
    *   `left`, `top`: 图片区域左上角的相对位置。
    *   `width`, `height`: 图片区域的相对宽高。
*   *(向后兼容)*: 如果 JSON 仍使用旧的 `native_image` 且只提供了枚举 `layout`，代码需要在内部将其自动转换为包含 `bounding_box` 的 `native_images` 列表。

### 2.2 LLM 提示词动态生成（多区域智能留白）

在调用 Gemini API 生成底板图前（`generate_image`），拦截并解析 `native_images` 的边界框数据。
我们需要将这些相对坐标换算成通俗易懂的“自然语言区域”，组合成**多区域留白约束指令**，附加在 `full_prompt` 尾部。

例如，如果有两个坐标：
1. `(left:0.05, top:0.1, width:0.4, height:0.8)` -> 粗略转化为“The left area (approx 40% width)”
2. `(left:0.55, top:0.2, width:0.4, height:0.6)` -> 粗略转化为“The right area (approx 40% width)”

程序拼接出留白指令：
*"CRITICAL: The following areas MUST be left extremely clean, empty, or plain solid color to accommodate overlaid photos: (1) The left area (approx 40% width), (2) The right area (approx 40% width)."*

这让生成背景图的大模型能避开这些指定的绝对物理空间。

### 2.3 PPTX 导出逻辑（多图绝对坐标渲染）

在 `core/generator.py` 的 `create_advanced_pptx` 阶段：

1. 检测当前页是否包含 `native_images` 列表（或 `native_image`）。
2. 如果包含，则遍历每一张图：
    *   提取 `bounding_box`：如 `left: 0.1`。
    *   计算绝对坐标（英尺 Inches）：`target_l = prs.slide_width * 0.1`，以此类推计算出 `target_t`, `max_w`, `max_h`。
    *   使用 `PIL` 读取原图计算其真实宽高比。
    *   **等比例缩放与居中**：在计算出的目标绝对边界框内，将图片等比例放大或缩小，居中放置在边界框内，确保图片不变形。
3. 循环调用 `slide.shapes.add_picture` 插入所有原生图片。

## 3. 实现步骤 (待后续开发)

1. **兼容性重构引擎 (Generator/Executor)**：
   *   支持解析新的 `native_images` 数组与 `bounding_box` 坐标系。
   *   内置旧版 `layout` 枚举值（`right_half` 等）到相对坐标的映射字典，实现向下兼容。
2. **多区域留白自然语言翻译器 (Prompt Injection)**：
   *   编写一个小算法，把 0.0~1.0 的坐标简单翻译成 "top left", "bottom right", "center" 或者百分比描述，喂给背景生成大模型。
3. **坐标换算算法升级 (PPTX Exporter)**：
   *   从写死的固定逻辑，升级为一套通用的根据目标 `bounding_box` 等比例插入图片并居中的方法。
4. **Agent Planning 层接入 (可选前置环节)**：
   *   更新主 Agent 的 Prompt，告诉大模型在规划 PPT 时，可以根据内容逻辑（单图、双图对比、四宫格等）输出相对坐标矩阵。
