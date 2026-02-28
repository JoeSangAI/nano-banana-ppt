# Nano Banana PPT

基于 Nano Banana 2 的全自动 PPT 生成工具。

## 目录结构

```
nano_banana_ppt/
  agents/           # AI 代理 (叙事、视觉、模版)
  core/             # 核心逻辑 (生成器、执行器)
  utils/            # 工具脚本 (修复、分析)
  main.py           # 统一入口
```

## 使用方法

### 1. 环境准备

确保已安装依赖：
```bash
pip install openai python-pptx pillow pymupdf requests
```

设置 API Key：
```bash
export OPENAI_API_KEY="your-key"
export OPENAI_API_BASE="https://generativelanguage.googleapis.com/v1beta/openai"
```

### 2. 一键生成 (Auto Pipeline)

这是推荐的使用方式，自动完成从文档解析到 PPT 生成的全过程。

```bash
# 仅提供内容，AI 自动设计风格
python -m nano_banana_ppt.main "your_content.md"

# 提供内容和模版 (PDF)
python -m nano_banana_ppt.main "your_content.md" "template.pdf" "output_filename"
```

### 3. 独立工具

**独立生图工具 (原 gen_image.py):**
```bash
python nano_banana_ppt/utils/image_gen.py "A futuristic city"
```

**PPT 修复工具:**
```bash
python -m nano_banana_ppt.utils.regenerate "output.pptx" "ppt_generation_plan.json"
```

## 开发指南

- **NarrativeAgent**: 负责将长文档转化为结构化的 JSON 大纲。
- **VisualAgent**: 负责将大纲转化为生图 Prompt (包含 Style Injection)。
- **TemplateAgent**: 负责解析 PDF 模版，提取 Logo 和参考图。
- **Executor**: 读取视觉计划，调用 Nano Banana 2 生成图片并组装 PPTX。
