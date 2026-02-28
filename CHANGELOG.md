# Changelog

All notable changes to this project will be documented in this file.

## [v2.2.0] - 2026-02-28

### 🚀 新特性 (New Features)

*   **双阶段自动化流 (Two-Phase Auto Pipeline)**：
    *   **Phase 1 (Plan)**: 引入了基于 Markdown 的审阅机制。首先生成 `plan_for_review.md`，允许用户在生成昂贵的图片前进行确认和修改。
    *   **Phase 2 (Execute)**: 读取确认后的计划文件进行渲染和 PPT 组装。
*   **混合图表渲染系统 (Hybrid Tables & Charts)**：
    *   **原生表格支持**: 表格 (`visualization: table`) 现采用原生 PPT 表格渲染，允许用户直接在 PowerPoint 中修改文本、调整列宽和单元格样式。
    *   **静态图表渲染**: 引入 `data_visualizer.py`，支持将柱状图、折线图、饼图等数据渲染为与主风格一致的高清图片。
*   **演讲备注支持 (Speaker Notes)**：
    *   叙事代理 (`NarrativeAgent`) 升级，支持为每页自动生成详尽的“演讲备注”，从而保持 PPT 页面核心文案的精简，并将丰富的业务背景放入备注中。
*   **局部重新生成 (Partial Regeneration)**：
    *   支持在生成失败（如 API 限流出现灰色占位图）时，通过 `execute ... --slides X Y` 仅重新生成指定的出错页面，无需从头开始。

### 🛠 重构与优化 (Refactoring & Improvements)

*   **包结构标准化**: 重新组织代码架构为标准的 Python 模块 (`nano_banana_ppt`)，清理了原有分散的脚本，提供更清晰的 `agents`、`core` 和 `utils` 目录划分。
*   **API 稳定性提升**: 将默认重试次数增加至 5 次，并引入指数退避策略 (最高 48 秒)，有效降低由于 API 并发限流导致的生成失败概率。
*   **并发控制**: 设置最高并发线程数（max concurrent workers = 2），以平滑处理图片生成请求并防止触发速率限制。
*   **系统提示词优化 (Prompt Engineering)**：对 `NarrativeAgent` 和 `VisualAgent` 的系统提示词进行了全面升级，增强了各种业务分析模型（如 SCQA、金字塔原理、英雄之旅）的自适应性。

### 🐛 修复 (Bug Fixes)

*   修复了导入路径导致的 `ModuleNotFoundError`。
*   修复了生成全黑或不完整图片的角点问题。
