# Mini-Spec: Visual Color Palette in Markdown Preview

## 1. Goal
Add a new section `## 三、色彩规范 (Color Palette)` in the generated `plan_for_review.md` (via `build_review_md`) to visually display the selected colors (Background, Text, Accent) using `placehold.co` image badges. This makes it instantly intuitive for users to preview the PPT's color scheme in Feishu/Markdown without manually looking up hex codes.

## 2. Changes in `build_review_md` (`tools/nano_banana_ppt/utils/review_plan.py`)

1. **Extract and Process `palette`:**
   We will iterate through `style_config.get("palette", [])` up to the number of colors available.
   - Index `0`: `背景大色块 (Background)`
   - Index `1`: `主体文字 (Text)`
   - Index `2`: `核心点缀色 (Accent 1)`
   - Index `3`: `次要点缀色 (Accent 2)`
   - Strip the `#` prefix for the `placehold.co` URL.

2. **Generate the Markdown Section:**
   Insert the new section after `## 二、视觉主张 (Design System Manifesto)` and before `## 四、各页预览`.
   ```markdown
   ## 三、色彩规范 (Color Palette)

   - **背景大色块 (Background)**：![#1A1A1A](https://placehold.co/15x15/1A1A1A/1A1A1A.png) `#1A1A1A`
   - **主体文字 (Text)**：![#FFFFFF](https://placehold.co/15x15/FFFFFF/FFFFFF.png) `#FFFFFF`
   - **核心点缀色 (Accent 1)**：![#0088FF](https://placehold.co/15x15/0088FF/0088FF.png) `#0088FF`

   ---

   ## 四、各页预览
   ```
   *(Note: The previous "各页预览" was "三、各页预览", we will rename it to "四、各页预览")*

## 3. Changes in `parse_review_md` (`tools/nano_banana_ppt/utils/review_plan.py`)

To ensure we do not break the reverse-parsing logic:
1. The regex for extracting `manifesto` is `r"##\s*[二三]、视觉主张.*?\n(.*?)---"`. This is robust enough because it explicitly looks for the next `---`.
2. The page parser regex uses `r"###\s*第\s*(\d+)\s*页"`. Since the color section does not use `### 第 N 页`, it will safely be ignored by the page block parser.
3. Therefore, no modifications are strictly required for `parse_review_md` to accommodate the new section. The existing `palette` regex extracts colors from `| 配色 | #xxx, #yyy |` in the "一、整体设计" section. We can leave it as is, or if we want, parse it from the new section as a fallback. For simplicity, we'll keep the existing extraction from the table.

## 4. Edge Cases Handled
- Missing palette: Show `> （自动生成，未指定具体配色方案）`.
- Invalid hex: If a color like "black" is passed, `placehold.co` also accepts named colors. However, our prompt generates strict Hex codes.

I am ready to implement this mini-spec using the `StrReplace` tool.