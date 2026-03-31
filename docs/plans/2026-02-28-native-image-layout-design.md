# PPT 原生图片排版与智能留白功能设计

## 1. 背景与目标

目前 `nano_banana_ppt` 倾向于使用 AI 生成全屏背景图作为幻灯片的底图。
但在实际业务场景中，用户经常需要插入**未经 AI 篡改的特定图片**（例如：广告上刊图、特定照片、品牌素材等），并要求：
1. **原图呈现**，拒绝 AI 重新读图生成导致的画质损毁或细节丢失。
2. **合理裁切或等比缩放**，根据预设的排版版式进行自适应处理。
3. **AI 智能留白**，在生成幻灯片底图时，AI 需要知道某个区域会被原生图片覆盖，从而在构图时主动留出干净的区域，避免背景元素与插入的图片发生重叠干扰。

## 2. 核心架构设计

我们采用 **方案 3：预设版式控制 + 原生图片插入** 的思路。

### 2.1 数据结构扩展

在 PPT 的配置 JSON (`slide_plan`) 中，扩展一个新的对象字段 `native_image`：

```json
{
  "page_num": 3,
  "type": "content",
  ...
  "native_image": {
    "path": "/absolute/path/to/image.png",
    "layout": "right_half"  // 预设枚举值
  }
}
```

支持的 `layout` 枚举值（初步设计）：
* `right_half`：占据右侧 50% 区域
* `left_half`：占据左侧 50% 区域
* `center`：屏幕居中
* `bottom_right`：右下角
* `fullscreen`：全屏（忽略背景图）

### 2.2 LLM 提示词动态注入（智能留白）

如果检测到当前 slide 配置了 `native_image`，在调用 `PPTGenerator.generate_image` 生成底图前，向传入的 `description` (即 `visual_prompt`) 中追加针对性留白指令。

例如：
* `layout: "right_half"` -> 追加: "CRITICAL: The right half of the image MUST be left extremely clean, empty, or plain solid color to accommodate an overlaid photo."
* `layout: "left_half"` -> 追加: "CRITICAL: The left half of the image MUST be left extremely clean, empty, or plain solid color to accommodate an overlaid photo."

这样生成的背景图片就会在指定位置留出干净的区域。

### 2.3 PPTX 导出逻辑（精确排版）

修改 `core/generator.py` 中的 `create_advanced_pptx` 方法：

1. 判断当前 `slide_plan` 中是否包含有效且路径存在的 `native_image`。
2. 使用 `PIL.Image` 读取原图，获取宽高比。
3. 根据 `layout` 枚举，结合 `prs.slide_width` (16 英寸) 和 `prs.slide_height` (9 英寸)，计算目标区域的坐标 `(left, top, width, height)`。
   - **等比例缩放处理**：确保图片在指定的边界框内最大化显示，且不改变宽高比（类似于 object-fit: contain）。
4. 调用 `slide.shapes.add_picture(path, left, top, width, height)` 将原生图片插入到 PPT 中，位于背景图之上。

## 3. 实现步骤

1. **修改数据生成端 (LLM 规划层)**：如果采用全自动化，可以在 AI 规划阶段允许其生成 `native_image` 配置（但这通常由用户手动干预更常见）。由于这里主要偏向底层执行，我们将重点放在 Executor 和 Generator 层面。
2. **修改 Generator Prompt 拼装**：在生成单张图之前，拦截 prompt 并追加留白指令。
3. **实现排版计算引擎**：在 `generator.py` 中编写辅助函数，处理坐标数学运算，确保缩放比例精确。
4. **集成测试**：使用用户提供的柯基山水图，手动构造一个带有 `native_image` 配置的 JSON plan，跑通整个链路，验证 PPT 生成效果。
