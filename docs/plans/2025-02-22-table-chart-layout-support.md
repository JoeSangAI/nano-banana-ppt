# 表格与图表布局支持 Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 为 nano-banana-ppt 增加表格布局与图表生成能力：当原文包含表格时，自动采用表格/图表布局，且图表数据忠实于原文表格。

**Architecture:** 
1) NarrativeAgent 识别原文中的 Markdown 表格并输出结构化 `table_data`，同时输出 `visualization` 建议 (table | bar | line | pie | auto)；
2) VisualAgent 新增 `table_dominant` 布局，并在 `_assign_layout` 中根据 `table_data` 或 `visualization` 分配；
3) 新增 `DataVisualizer` 模块，用 matplotlib 从 `table_data` 程序化渲染表格/图表 PNG，保证数据准确性；
4) Executor 对 `table_data` 页面分支：调用 DataVisualizer 而非 AI 生图。

**Tech Stack:** Python, matplotlib, markdown-table-parser 或正则, json, PIL

---

## 设计决策

| 决策点 | 选择 | 原因 |
|--------|------|------|
| 表格渲染 | 程序化 (matplotlib table) | AI 生图无法保证数字准确 |
| 图表渲染 | 程序化 (matplotlib) | 必须忠实展示数据 |
| 表格解析 | NarrativeAgent LLM + 正则回退 | 支持非标准 Markdown 表格 |
| visualization 建议 | LLM 输出 + 启发式回退 | 根据行列/数值类型自动选 bar/line/pie |

---

## Task 1: 新增 DataVisualizer 模块

**Files:**
- Create: `tools/nano_banana_ppt/core/data_visualizer.py`
- Modify: （本 Task 不修改其他文件）

**Step 1: 创建 data_visualizer.py 骨架**

```python
"""
Data Visualizer - 从 table_data 程序化渲染表格与图表
保证数据忠实展示，不依赖 AI 生图
"""
import io
from typing import Dict, List, Optional
from PIL import Image

def render_table_image(table_data: Dict, style_config: Dict, output_size: tuple = (1920, 1080)) -> Image.Image:
    """
    从 table_data 渲染表格为 PNG
    table_data: {"headers": [...], "rows": [[...], ...]}
    """
    raise NotImplementedError

def render_chart_image(table_data: Dict, chart_type: str, style_config: Dict, 
                       output_size: tuple = (1920, 1080)) -> Image.Image:
    """
    从 table_data 渲染图表为 PNG
    chart_type: "bar" | "line" | "pie"
    """
    raise NotImplementedError
```

**Step 2: 安装 matplotlib 依赖**

在项目根目录的 requirements 或 pyproject 中确保包含 `matplotlib`。若无统一依赖文件，在 `tools/nano_banana_ppt/` 下创建 `requirements.txt` 列出 matplotlib。

**Step 3: 实现 render_table_image**

使用 matplotlib 的 `table()` API 或 `plt.imshow` + 文本叠加，将 table_data 渲染为 16:9 PNG。配色从 style_config.palette 读取。

**Step 4: 实现 render_chart_image**

- bar: `plt.bar`，第一列/行作为类别，其余为数值
- line: `plt.plot`，适用于时间序列
- pie: `plt.pie`，适用于占比数据

**Step 5: 添加基础测试（可选）**

```python
# tests/test_data_visualizer.py
def test_render_table_basic():
    data = {"headers": ["A", "B", "C"], "rows": [["1", "2", "3"], ["4", "5", "6"]]}
    img = render_table_image(data, {"palette": ["#fff", "#333"]})
    assert img.size[0] > 0
```

---

## Task 2: NarrativeAgent 支持表格解析与 visualization

**Files:**
- Modify: `tools/nano_banana_ppt/agents/narrative.py`

**Step 1: 添加 extract_markdown_tables 方法**

```python
def extract_markdown_tables(self, content: str) -> List[Dict]:
    """
    从 Markdown 内容提取表格，返回 [{"headers": [...], "rows": [[...], ...]}, ...]
    """
    import re
    tables = []
    # 匹配 | xxx | xxx | 格式
    pattern = r'\|(.+)\|\s*\n\|[-:\s|]+\|\s*\n((?:\|.+\|\s*\n?)+)'
    for m in re.finditer(pattern, content):
        header_row = [c.strip() for c in m.group(1).split('|')]
        body = m.group(2).strip().split('\n')
        rows = [[c.strip() for c in line.split('|')[1:-1]] for line in body if line.strip()]
        tables.append({"headers": header_row, "rows": rows})
    return tables
```

**Step 2: 修改 generate_narrative_outline 的 prompt**

在 prompt 中增加：

```
5. **表格与图表 (Table & Chart)**：
   - 如果源文档包含 Markdown 表格（| 列1 | 列2 | ...），必须单独作为一页，且 type 为 "table" 或 "chart"。
   - 在 text_content 中增加 table_data 字段：
     table_data: { "headers": ["列1", "列2", ...], "rows": [["val1", "val2", ...], ...] }
   - 增加 visualization 字段：表格式展示用 "table"；适合图表展示用 "bar"|"line"|"pie"|"auto"（auto 由系统根据数据自动选择）。
   - body 可保留表格的简要说明，但核心数据必须在 table_data 中完整保留。
```

**Step 3: 后处理：将 extract_markdown_tables 的结果注入 outline**

在 `generate_narrative_outline` 返回前，遍历 outline，若某页的 visual_suggestion 或 body 中提到表格但缺少 table_data，尝试用 extract_markdown_tables 的结果匹配并注入。

---

## Task 3: VisualAgent 新增 table_dominant 布局

**Files:**
- Modify: `tools/nano_banana_ppt/agents/visual.py`

**Step 1: 在 LAYOUT_LIBRARY 中新增**

```python
"table_dominant": "Top 15% for headline/subhead. Main area (85%) dedicated to a clear, readable table with headers and rows. Minimal decoration, high contrast for readability.",
```

**Step 2: 修改 _assign_layout**

在方法签名中增加 `page` 参数（或从 text_content 传入 table_data/visualization）。在判断逻辑中：

```python
# 在 page_type == 'toc' 之后添加
table_data = page.get('text_content', {}).get('table_data') or page.get('table_data')
visualization = page.get('visualization', '')
if table_data:
    if visualization in ('bar', 'line', 'pie'):
        return 'chart_from_table', CHART_LAYOUT_DESC  # 或复用 table_dominant 的变体
    return 'table_dominant', VisualAgent.LAYOUT_LIBRARY['table_dominant']
```

**Step 3: 在 generate_visual_plan 中处理 table/chart 页**

对于 `layout == 'table_dominant'` 或 `visualization in ('bar','line','pie')` 的页面：
- 不调用 LLM 生成 visual_prompt
- 设置 `use_data_visualizer: True`，`chart_type` 或 `table_only`
- 不生成 background_only 类型的冗余页（若该页为表格/图表）

---

## Task 4: Executor 集成 DataVisualizer

**Files:**
- Modify: `tools/nano_banana_ppt/core/executor.py`

**Step 1: 导入 DataVisualizer**

```python
from tools.nano_banana_ppt.core.data_visualizer import render_table_image, render_chart_image
```

**Step 2: 修改执行逻辑**

在 `_generate_single_slide` 或主循环中，对每页检查：

```python
table_data = slide.get('table_data') or slide.get('text_content', {}).get('table_data')
visualization = slide.get('visualization', '')
if table_data:
    if visualization in ('bar', 'line', 'pie'):
        image = render_chart_image(table_data, visualization, slide.get('style_config', {}))
    else:
        image = render_table_image(table_data, slide.get('style_config', {}))
    # 保存到 slides_dir，加入 images_dict
    # 跳过 generate_image 调用
    continue
```

**Step 3: 确保 table/chart 页参与 images_dict 与 create_advanced_pptx**

与现有 AI 生图流程共用 `images_dict[page_num]`，保证 PPTX 组装时正常插入。

---

## Task 5: 端到端联调与文档更新

**Files:**
- Modify: `tools/nano_banana_ppt/main.py`（如有需要）
- Modify: `skills/nano-banana-ppt/SKILL.md`

**Step 1: 编写带表格的测试文档**

创建 `临时/test_table_content.md`，包含简单 Markdown 表格。

**Step 2: 运行 plan + execute**

```bash
python -m tools.nano_banana_ppt.main plan 临时/test_table_content.md
# 检查 plan.json 中是否包含 table_data 和 visualization
python -m tools.nano_banana_ppt.main execute output/test_table_content/plan.json
```

**Step 3: 更新 SKILL.md**

在「布局库」小节补充 `table_dominant` 及图表能力说明。

---

## 附录：table_data 与 visualization 约定

```json
{
  "page_num": 5,
  "type": "content",
  "visualization": "bar",
  "text_content": {
    "headline": "2024年各季度营收对比",
    "subhead": "单位：万元",
    "table_data": {
      "headers": ["季度", "营收"],
      "rows": [["Q1", "120"], ["Q2", "150"], ["Q3", "180"], ["Q4", "200"]]
    }
  }
}
```

`visualization` 取值：
- `"table"`: 纯表格展示
- `"bar"`: 柱状图
- `"line"`: 折线图
- `"pie"`: 饼图
- `"auto"`: 由 DataVisualizer 根据数据特征自动选择
