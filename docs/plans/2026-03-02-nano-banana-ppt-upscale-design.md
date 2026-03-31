# Nano Banana PPT: 独立 Upscale (高保真放大) 功能设计

## 1. 业务背景与目标 (Context & Goals)
在 Nano Banana PPT 生成流程中，用户默认通常使用 `1K` 分辨率进行全流程的草稿生成和内容确认（速度快、成本低）。
当 PPT 内容、版面和整体设计被确认后，如果存在个别页面（或整个文档）分辨率不够（例如需要投影在大屏上），此时需要一个**独立、安全的后置放大功能**，将其提升至 `2K` 或 `4K` 分辨率。

**核心约束：**
- **高保真 (High-Fidelity)**：在放大过程中，绝对不能改变任何排版、文字内容、或者擅自增加/删减设计元素。它必须像一个“高清复印机”。
- **隔离性 (Isolation)**：这个功能是低频操作，不能干扰现有的 `plan` 或 `execute` 命令，必须作为一个独立的命令存在。

## 2. 设计决策 (Design Decisions)

### 2.1 纯视觉放大策略 (Option A1)
**决策**：不向模型提供原 Markdown 文本，仅提供原低分辨率图片和一段极其严厉的“保真放大” Prompt。
**理由**：Gemini 3.1 Pro/Flash Image 模型对 1K 图片上的文字识别能力极强。如果不提供源文本，模型会专注于像素级的锐化和分辨率提升；一旦提供文本，模型极易触发“重新排版”和“创意发散”的隐藏逻辑，导致原来确认好的版面被破坏。

**Upscale 专属 Prompt 设计**：
> "Upscale this image to [2K/4K] resolution. ACT AS A HIGH-FIDELITY UPSCALER. You must maintain all text, details, layouts, and colors exactly as they appear in the source image. Do NOT change any words, do NOT move any text, do NOT add or remove any design elements. Simply increase the resolution, sharpness, and clarity."

### 2.2 独立的 CLI 命令 (`upscale`)
**决策**：新增一个专门的 `upscale` 子命令。
**交互设计**：
```bash
# 全局放大
python -m tools.nano_banana_ppt.main upscale <项目目录> --resolution 4K

# 指定页面放大（节约成本和时间）
python -m tools.nano_banana_ppt.main upscale <项目目录> --resolution 4K --slides 3 5 7
```

## 3. 技术实现方案 (Technical Plan)

### 3.1 `core/generator.py` 扩展
在现有的 `PPTGenerator` 或相关的生图工具类中，新增 `upscale_image` 方法：
- **输入**：`image_path` (待放大的原图路径), `resolution` (目标分辨率 `2K`/`4K`)
- **逻辑**：
  1. 读取原图片为字节流。
  2. 构造包含上述严格提示词和图片数据的 Payload。
  3. 调用与 `generate_image` 相同的 Google API Endpoint，但忽略原 `plan.json` 中的视觉 Prompt，覆盖 `imageSize` 配置为目标分辨率。
  4. 接收返回的高清图片流并覆盖保存原文件。

### 3.2 `main.py` CLI 路由扩展
- 在 CLI 参数解析处，支持解析 `upscale` 命令及其参数。
- 新增 `execute_upscale(proj_dir: str, resolution: str, slide_filter: list)` 流程控制器：
  1. 验证 `<项目目录>` 及其内部的图片 (`bg_01.png`, `bg_02.png` 等) 是否存在。
  2. 根据 `slide_filter` 过滤需要处理的图片索引。
  3. 遍历目标图片，调用 `upscale_image` 进行逐张放大并原地覆盖。
  4. 放大流程全部完成后，复用现有的 PPTX 组装逻辑（等价于执行 `reassemble_only`），读取高清背景图生成最终的高清 PPTX。

## 4. 边界处理与容错
- **分辨率兜底**：如果 `upscale` 传入的分辨率不是 `2K` 或 `4K`，给予警告并退出（放大至 `1K` 无意义）。
- **缺失图片**：如果指定的 slide 没有找到对应的 `bg_XX.png`，在控制台抛出警告并跳过该页。
- **并发与限流**：若全局放大所有页面，应考虑加入或复用现有的限流重试机制（指数退避），防止大批量并发导致 API 429 Rate Limit。
