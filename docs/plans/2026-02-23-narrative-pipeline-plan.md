# Two-Step Narrative Generation Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Refactor `NarrativeAgent` to use a two-step pipeline (extract core logic first, then generate slide JSON) to improve the coherence of PPTs generated from long text.

**Architecture:** We will add `_extract_core_logic` to `NarrativeAgent` which prompts the LLM to output a Markdown "storyboard" skeleton. Then, we modify `generate_narrative_outline` to first call `_extract_core_logic`, and then inject that skeleton into the main prompt to guide the JSON generation.

**Tech Stack:** Python, OpenAI Python Client (Google Gemini API via proxy), JSON.

---

### Task 1: Add `_extract_core_logic` method

**Files:**
- Modify: `tools/nano_banana_ppt/agents/narrative.py`

**Step 1: Write the implementation**

Add the `_extract_core_logic` method to `NarrativeAgent` in `tools/nano_banana_ppt/agents/narrative.py`.

```python
    def _extract_core_logic(self, content_context: str, constraints: Dict) -> str:
        """
        [Step 1/2] 从海量文本中提取核心叙事逻辑骨架
        """
        logger.info("🧠 Narrative Agent: 正在提取核心叙事逻辑...")
        prompt = f"""你是一位顶级的商业战略分析师和结构化表达专家。
请阅读下面的源文档（可能非常长），并从中“榨取”出最核心的【叙事逻辑骨架】。这个骨架将作为后续制作 PPT 的唯一蓝本。

【项目背景】
- 目标受众: {constraints['target_audience']}
- 演示类型: {constraints['presentation_type']}
- 风格偏好: {constraints['style_preference']}

【输入内容】
{content_context[:50000]}

【任务要求】
请输出纯 Markdown 格式的叙事逻辑地图，必须包含以下四部分：
1. **核心洞察 (Core Thesis)**：用一句话总结全文到底想传达的最核心信息。
2. **现状与痛点 (Context & Problem)**：开场需要交代什么背景？听众为什么要听？
3. **逻辑支柱 (Logical Pillars)**：提炼出 3-5 个核心论证模块（例如：是什么 -> 为什么 -> 怎么做）。
4. **金句与关键数据 (Key Takeaways)**：文中绝对不能被遗漏的经典句子、硬核数据或核心方法论。

保持极简、犀利，不要废话。
"""
        max_retries = 2
        for attempt in range(max_retries):
            try:
                response = chat_completion_with_fallback(
                    self.client, model=self.model, model_fallback=MODEL_FALLBACK_CHAIN,
                    messages=[
                        {"role": "system", "content": "你是一个精通商业逻辑提炼的专家。请直接输出 Markdown 骨架，不要有多余的解释。"},
                        {"role": "user", "content": prompt}
                    ],
                    temperature=0.3
                )
                content = response.choices[0].message.content.strip()
                return content
            except Exception as e:
                if attempt < max_retries - 1:
                    logger.warning(f"逻辑骨架提取失败，重试 ({attempt + 1}/{max_retries}): {e}")
                else:
                    logger.error(f"逻辑骨架提取最终失败: {e}")
                    raise
```

**Step 2: Commit**

```bash
git add tools/nano_banana_ppt/agents/narrative.py
git commit -m "feat: add _extract_core_logic to NarrativeAgent"
```

---

### Task 2: Modify `generate_narrative_outline` to use the two-step pipeline

**Files:**
- Modify: `tools/nano_banana_ppt/agents/narrative.py`

**Step 1: Write the implementation**

Update `generate_narrative_outline` to call `_extract_core_logic` and inject the result into the prompt.

1. Call `_extract_core_logic` right after extracting images.
2. Inject the `core_logic_skeleton` into the `prompt`.

```python
    def generate_narrative_outline(self, content_context: str, constraints: Dict) -> List[Dict]:
        """
        生成深度叙事大纲 (Two-Step Pipeline)
        """
        logger.info("🧠 Narrative Agent: 正在构建叙事架构 (Phase 1/2: 提取骨架)...")
        
        # Step 1: 提取骨架
        core_logic_skeleton = self._extract_core_logic(content_context, constraints)
        logger.info("✅ 核心逻辑提取完成。")
        logger.info("🧠 Narrative Agent: 正在构建叙事架构 (Phase 2/2: 生成分页 JSON)...")

        # 提取源文档中的图片
        source_images = self.extract_images_from_markdown(content_context)
        source_images_str = "\n".join([f"- {img}" for img in source_images[:5]]) # 仅列出前5张作为参考
        
        # 动态调整大纲结构要求
        page_count_constraint = constraints.get('page_count', '10')
        try:
            target_pages = int(page_count_constraint)
        except:
            target_pages = 10

        structure_instruction = ""
        if target_pages > 10:
            structure_instruction = """
   - **强制分节 (Part Structure)**：由于 PPT 页数较多（>10页），必须严格按照【核心叙事逻辑】中的逻辑支柱来划分章节（Section）。
   - 每一页都必须归属于某个 Section。
   - 在每个 Section 开始时，必须插入一个 `section` 类型的转场页。"""
        else:
            structure_instruction = """
   - **逻辑分节**：必须严格按照【核心叙事逻辑】中的逻辑支柱来划分 PPT 的节奏。"""

        prompt = f"""你是一位顶尖的商业演示设计专家和视觉传达顾问。
请根据我已经为你提炼好的【核心叙事逻辑】，结合原始【输入内容】，帮我设计一份逻辑清晰且极具说服力的演示文稿大纲。

【项目背景】
- 目标受众: {constraints['target_audience']}
- 演示类型: {constraints['presentation_type']}
- 预计时长: {constraints['duration']}
- 期望页数: {constraints['page_count'] or '根据内容自动规划(约10-15页)'}
- 风格偏好: {constraints['style_preference']}

【核心叙事逻辑】 (CRITICAL: 你的分页大纲必须严格支撑这个骨架)
{core_logic_skeleton}

【输入内容】 (用于提取详细的论据和原文金句)
{content_context[:50000]} ... (内容过长已截断)

【可用素材图片】
(如果内容涉及到以下图片所代表的场景或产品，请在 visual_suggestion 中明确引用)
{source_images_str}

【任务要求】
1. **结构化叙事 (Structure)**：{structure_instruction}
   - **严禁偏题**：所有的页面都必须服务于【核心叙事逻辑】中的 Core Thesis。

2. **内容精细度 (Granularity)**：
   - **语言要求 (CRITICAL)**：大纲内容（headline, subhead, body）**必须尽量保留用户源文档的原文表述**，确保信息传递准确。不要自行翻译或改写为纯英文。如果源文档是中文或中英混排，大纲也应保持同样的语言风格。
   - **突出金句与数据**：请务必将【核心叙事逻辑】中提到的“金句与关键数据”设计为视觉冲击力强的 `hero` 或 `data` 页。
   - **首页极简**：封面页只包含标题、副标题和演讲人信息，**严禁堆砌其他素材**，保持纯粹的设计感。
   - **Content 页详实度**：每页包含 3-4 个核心论据。**每个论据的字数控制在 30-100 字之间**。既要讲透，又不能太长。保留原文的关键数据和案例。
   - **智能拆页**：如果某章节内容过多，请自动拆分为多页（如 P2-1, P2-2）。

3. **连贯性 (Flow)**：
   - 使用 `transition` 字段描述逻辑承接。

4. **页面类型强制**：
   - `cover`: 封面 (仅第1页)
   - `toc`: 目录
   - `section`: 章节页 (转场，必选，用于开启新章节)
   - `content`: 标准内容页 (图文混排)
   - `hero`: 金句页/英雄页 (核心观点，大字号，强视觉冲击)
   - `data`: 数据页 (图表、数据可视化)
   - `ending`: 封底/致谢页

5. **表格与图表 (Table & Chart)**：
   - 如果源文档包含 Markdown 表格（| 列1 | 列2 | ...），必须单独作为一页，且 type 为 "table" 或 "chart"。
   - 在 text_content 中增加 table_data 字段：
     table_data: {{ "headers": ["列1", "列2", ...], "rows": [["val1", "val2", ...], ...] }}
   - 增加 visualization 字段：表格式展示用 "table"；适合图表展示用 "bar"|"line"|"pie"|"auto"（auto 由系统根据数据自动选择）。
   - body 可保留表格的简要说明，但核心数据必须在 table_data 中完整保留。

【JSON 数据结构】
[
  {{
    "page_num": 1,
    "section_title": "Part 1: 市场背景", 
    "type": "content", 
    "title": "页面标题",
    "core_message": "本页核心传递的信息",
    "visualization": "table/bar/line/pie/auto",
    "transition": "逻辑过渡...", 
    "text_content": {{
        "headline": "大标题 (例如：盲区：为何我们看不见？)",
        "table_data": {{ "headers": ["H1", "H2"], "rows": [["v1", "v2"]] }},
        "subhead": "导语/总起句 (CRITICAL)：这一页的核心观点或承接语。",
        "body": [
            "详细论据1 (30-100字)：...", 
            "详细论据2 (30-100字)：..."
        ]
    }},
    "visual_suggestion": "画面建议。如果可以使用源文档中的图片，请注明：'Use source image: [url]'"
  }},
  ...
]

请确保输出严格的 JSON 格式，不要包含 Markdown 代码块标记。"""
```

**Step 2: Commit**

```bash
git add tools/nano_banana_ppt/agents/narrative.py
git commit -m "feat: modify generate_narrative_outline to use two-step pipeline"
```
