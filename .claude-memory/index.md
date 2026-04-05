# Nano Banana PPT 项目记忆

## 状态
🟢 开发中

## 最近更新
2026-04-05 - DeerAPI Gemini 生图同步（来自 nano-banana-pic）：
- 支持 1:4、1:8、9:16 等所有比例 + 4K 分辨率
- 参考图片自动压缩（>500KB 自动压）
- 混沌风格排版规则（细体正文、粗体标题、2x行高）

## DeerAPI Gemini 图片生成配置（已验证）
- API: `https://api.deerapi.com/v1`
- 模型: `gemini-3.1-flash-image-preview`
- 参数格式: `extra_body={"image_config": {"aspect_ratio": "1:4", "imageSize": "4K"}}`
- 支持比例: 1:1, 1:4, 1:8, 2:3, 3:2, 4:3, 3:4, 4:1, 1:2, 2:1, 9:16, 16:9, 21:9, 4:5, 5:4
- 支持分辨率: 512, 1K, 2K, 4K
- 参考图片: 最多 14 张（via base64 inline）

## 项目概述
Nano Banana 2 是一个 AI PPT 生成流水线，用自然语言描述主题，自动生成完整 PPT。

## 技术栈
- Python 3
- MiniMax via DeerAPI（文本）
- Gemini via DeerAPI（生图）
- PptxGenJS（PPT 组装）

## 关键文件
- `main.py` — CLI 入口
- `agents/narrative.py` — NarrativeAgent
- `agents/visual.py` — VisualAgent
- `core/executor.py` — 并发生图编排

## 当前任务
- 提升 JSON 解析稳定性
- 优化生图一致性

## 已知问题
- 并发过高会触发 rate limit（已从 5 降到 2）
- 缓存基于文件内容 SHA256
