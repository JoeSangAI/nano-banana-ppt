# 分众墨西哥分公司 2026-2030 五年预算模型 Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 基于已达成的设计方案，使用 Python (pandas, openpyxl) 修改并延展原有的《分众墨西哥分公司_2026-2028预算模型 20250204（ODI）.xlsx》模型至 2030 年，确保 4 万块屏幕和 5 亿营收在逻辑和计算上严丝合缝。

**Architecture:** 我们将使用 `openpyxl` 库来读取原 Excel 模型，保留它原有的格式（Formatting），然后分别在“核心参数假设”、“总预算明细表”、“人力成本明细”三个 Sheet 中追加 2029、2030 年的列并写入计算公式和新数值，最后另存为一个新的 .xlsx 文件。

**Tech Stack:** Python, openpyxl

---

### Task 1: 扩展“核心参数假设” Sheet 到 2029 和 2030 年

**Files:**
- Modify: `分众/分众墨西哥分公司/价格体系/分众墨西哥分公司_2026-2028预算模型 20250204（ODI）.xlsx`
- Create Temp Script: `extend_assumptions.py`

**Step 1: Write script to append columns and data to '核心参数假设'**
读取原文件，在原 2028 列后面追加 2029、2030 两列。写入新目标数值（如：目标刊挂率 15%, 17.5% 等，保持 CAPEX 成本参数为 2513 等）。使用 `openpyxl` 写入公式或数值，保留单元格格式。

**Step 2: Run script to verify it works**
执行临时脚本，将修改保存为中间文件 `tmp/spreadsheets/budget_model_step1.xlsx`。
Run: `python3 extend_assumptions.py`
Expected: 成功创建 `tmp/spreadsheets/budget_model_step1.xlsx`

---

### Task 2: 扩展“人力成本明细” Sheet

**Files:**
- Modify: `tmp/spreadsheets/budget_model_step1.xlsx`
- Create Temp Script: `extend_hc.py`

**Step 1: Write script to append columns and adjust Headcount logic**
新增 2029 和 2030 年列。实现逻辑：
1. 中方团队涨薪（5-8%）。
2. 在 2029 和 2030 新增 2 名中方关键 HC。
3. 增加本地销售副总 (VP of Sales)，且本地销售人数与业绩同比例爆发式增加。
4. 增加 Designer 和 IT Support 岗位。地推主管数量不增。

**Step 2: Run script to verify it works**
执行脚本，另存为 `tmp/spreadsheets/budget_model_step2.xlsx`。
Run: `python3 extend_hc.py`
Expected: 成功创建并正确计算 HC 成本。

---

### Task 3: 扩展“总预算明细表” Sheet 并生成最终文件

**Files:**
- Modify: `tmp/spreadsheets/budget_model_step2.xlsx`
- Create Temp Script: `extend_summary.py`

**Step 1: Write script to append 2029 and 2030 to '总预算明细表'**
这部分最核心。需要增加：
1. **期末屏幕数**：2029 设为 25,000，2030 设为 40,000。
2. **有效运营屏幕数**：2029 = 20,000，2030 = 32,500。
3. **营收公式**：有效屏幕 * 单屏产值（从假设表抓取）。2030 年总营收指向 5 亿。
4. **总支出计算**：同步汇总。

**Step 2: Run script to save final output**
执行脚本，将最终成果保存到最终目录中 `output/spreadsheet/分众墨西哥分公司_2026-2030五年预算模型.xlsx`。
Run: `python3 extend_summary.py`
Expected: 生成最终的五年预算表，并在控制台打印出 2030 年的总营收验证（约 5 亿）。

**Step 3: Cleanup temporary scripts**
删除刚才新建的 `.py` 和中间 Excel 文件。
Run: `rm extend_assumptions.py extend_hc.py extend_summary.py tmp/spreadsheets/budget_model_step1.xlsx tmp/spreadsheets/budget_model_step2.xlsx`
