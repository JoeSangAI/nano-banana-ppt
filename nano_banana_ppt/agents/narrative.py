"""
Narrative Architecture Agent
负责将用户输入转化为深度叙事大纲
"""
import os
import json
import logging
from typing import Dict, List, Optional
from openai import OpenAI

from ..utils.llm_client import chat_completion_with_fallback, MODEL_FALLBACK_CHAIN

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class NarrativeAgent:
    def __init__(self, api_key: str, api_base: str = None):
        self.client = OpenAI(
            api_key=api_key,
            base_url=api_base or "https://generativelanguage.googleapis.com/v1beta/openai",
            timeout=600.0,  # 50+ 页生成需较长时间
            max_retries=3
        )
        self.model = "gemini-3.1-pro-preview" # 使用高智力模型进行逻辑规划

    def collect_constraints(self) -> Dict:
        """
        交互式收集用户约束参数 (CLI模式)
        """
        print("\n=== 🎯 PPT 叙事目标设定 ===")
        
        target_audience = input("1. 目标受众是谁？(例如：投资人、公司高管、大众): ").strip() or "通用受众"
        presentation_type = input("2. 演讲类型？(例如：Pitch Deck、年终汇报、教育课件): ").strip() or "商业演示"
        duration = input("3. 预计演讲时长？(例如：10分钟、30分钟): ").strip() or "15分钟"
        page_count = input("4. 期望页数？(默认为 10-15 页): ").strip()
        style_preference = input("5. 风格偏好？(例如：极简、科技感、国潮): ").strip() or "专业商务"
        
        return {
            "target_audience": target_audience,
            "presentation_type": presentation_type,
            "duration": duration,
            "page_count": page_count,
            "style_preference": style_preference
        }
        
    def analyze_content(self, content_context: str) -> Dict:
        """
        [自动推导] 分析源文档，提取元数据
        """
        logger.info("🧠 Narrative Agent: 正在分析源文档元数据...")
        prompt = f"""请分析这份文档，提取以下关键信息：
1. 目标受众 (Target Audience)
2. 核心主题 (Core Topic)
3. 建议的演讲时长 (Duration)
4. 适合的演示风格 (Style)

文档内容前 5000 字:
{content_context[:5000]}

请输出 JSON 格式：
{{
  "target_audience": "...",
  "presentation_type": "...",
  "duration": "...",
  "style_preference": "..."
}}"""
        try:
            response = chat_completion_with_fallback(
                self.client, model=self.model, model_fallback=MODEL_FALLBACK_CHAIN,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.1
            )
            result = response.choices[0].message.content.strip()
            if result.startswith('```json'): result = result[7:]
            if result.endswith('```'): result = result[:-3]
            return json.loads(result)
        except Exception:
            return {}

    def extract_images_from_markdown(self, content: str, base_dir: str = None) -> List[str]:
        """
        从 Markdown 内容中提取图片链接
        """
        import re
        import os
        # 匹配 ![alt](url) 格式
        images = re.findall(r'!\[.*?\]\((.*?)\)', content)
        
        valid_images = []
        for img in images:
            img = img.strip()
            
            # 如果是网络图片，尝试下载到 base_dir 并替换为本地路径
            if img.lower().startswith('http://') or img.lower().startswith('https://'):
                if base_dir:
                    import urllib.request
                    from urllib.parse import urlparse
                    try:
                        # Extract filename from URL or generate one
                        parsed_url = urlparse(img)
                        filename = os.path.basename(parsed_url.path)
                        if not filename or not any(filename.lower().endswith(ext) for ext in ['.png', '.jpg', '.jpeg', '.gif', '.webp']):
                            import uuid
                            filename = f"{uuid.uuid4()}.jpeg" # default to jpeg if unknown
                        
                        local_path = os.path.join(base_dir, filename)
                        
                        # Only download if it doesn't exist
                        if not os.path.exists(local_path):
                            logger.info(f"下载网络图片: {img} -> {local_path}")
                            # Add headers to avoid 403 Forbidden
                            import ssl
                            context = ssl._create_unverified_context()
                            req = urllib.request.Request(img, headers={'User-Agent': 'Mozilla/5.0'})
                            with urllib.request.urlopen(req, context=context) as response, open(local_path, 'wb') as out_file:
                                out_file.write(response.read())
                        
                        valid_images.append(local_path)
                    except Exception as e:
                        logger.warning(f"无法下载网络图片 {img}: {e}")
                continue
                
            if img.lower().endswith(('.png', '.jpg', '.jpeg', '.gif', '.webp')):
                # 尝试将相对路径转换为绝对路径
                if base_dir and not os.path.isabs(img):
                    abs_path = os.path.normpath(os.path.join(base_dir, img))
                    if os.path.exists(abs_path):
                        valid_images.append(abs_path)
                    else:
                        valid_images.append(img) # 备用保留
                elif base_dir and img.startswith('http'):
                    # The previous logic incorrectly ignored all http links early on, but we want to download them
                    pass # Handled below
                else:
                    valid_images.append(img)
                    
        return valid_images

    def _extract_core_logic(self, content_context: str, constraints: Dict) -> str:
        """
        [Step 1/2] 从海量文本中提取深度叙事蓝图 (Narrative Blueprint)
        不仅提取骨架，更规划演讲的节奏、情绪起伏和内容映射。
        借鉴 NotebookLM：加入「解释层」——推断作者隐含意图、受众收获、So What。
        """
        logger.info("🧠 Narrative Agent: 正在提取深度叙事蓝图...")
        briefing_block = ""
        if constraints.get("briefing"):
            briefing_block = f"""
【用户意图 (User Briefing - CRITICAL)】
用户明确表达了这场 PPT 的核心目标，必须优先满足：
"{constraints['briefing']}"
请围绕此意图来构建蓝图，确保每一环节都服务于用户最想传达的信息。
"""

        prompt = f"""你是一位顶级的商业战略分析师、TED 演讲教练（如 Nancy Duarte）和结构化表达专家。
请阅读下面的源文档（可能非常长），判断其内容类型，并从中提取或重塑最合适的【深度叙事蓝图】(Narrative Blueprint)。这个蓝图将作为后续制作高质量 PPT 的唯一指南。
{briefing_block}
【项目背景】
- 目标受众: {constraints['target_audience']}
- 演示类型: {constraints['presentation_type']}
- 风格偏好: {constraints['style_preference']}

【叙事框架策略】
请判断源文档内容，并选择最匹配的叙事框架（或混合使用）：
1. SCQA (情境-冲突-疑问-解答) - 适合商业汇报、咨询
2. 乔布斯式发布会 (敌人-英雄-演示-愿景) - 适合产品/品牌
3. TED 演讲流 (钩子-核心理念-证据/故事-行动号召) - 适合布道、教育
4. 英雄之旅 (启程-考验-成长-回归) - 适合故事、设定
5. 用户原生结构 (User Defined) - **如果输入本身是结构化大纲（如包含章节数字、时间线等），必须严格尊重其原生结构，仅在此基础上增强节奏感。**

【输入内容】
{content_context[:50000]}

【任务要求】
请输出纯 Markdown 格式的深度叙事蓝图，必须包含以下五部分：
1. **核心洞察 (Core Thesis)**：用一句极其精炼、有穿透力的话总结全文的最终目的。
2. **叙事框架与节奏 (Narrative Arc & Pacing)**：说明你选用的框架，并描述情绪和逻辑的起伏节奏（例如：开头用什么痛点做钩子，中间如何层层递进，高潮在哪里，结尾如何升华）。
3. **内容映射与分页策略 (Content Mapping)**：
   - 梳理出主要章节（Section），并简述每个章节下需要展开几个关键点。
   - 标注出哪些内容应该被提炼为"金句/Hero页"（用于情绪共鸣或核心理念），哪些内容适合做"数据/图表页"。
   - 标注出哪些内容适合用"流程图 (flowchart)"呈现（如 Input→AI→Output）、"框架/层级图 (framework)"（如 1+N+X 金字塔）、"对比图 (comparison)"（如 注意力↘ vs 内容↗）。
   - 如果用户输入是详细大纲，请逐一映射其章节，不要遗漏重要模块。
4. **视觉与文案调性 (Tone & Visual Metaphor)**：为这个 PPT 设定一个统一的比喻或视觉意象（例如："攀登雪山"、"齿轮运转"、"破局的锤子"），并规定文案语言的"性格"（如：克制犀利、热血激情、专业严谨）。
5. **隐含意图与受众收获 (Implicit Intent & Takeaway)**：
   - 作者可能未在文中直说、但贯穿全文的潜台词或情绪弧是什么？
   - 观众听完这场 PPT，理想情况下应记住哪 1-3 个核心点？应采取什么行动或态度变化？
   - 列出 3-5 个对论证至关重要的关键证据/金句，并说明各自在叙事中的角色（铺垫/证据/转折/结论）。

保持结构清晰，洞察深刻，直接输出 Markdown，不要多余解释。
"""
        max_retries = 2
        for attempt in range(max_retries):
            try:
                response = chat_completion_with_fallback(
                    self.client, model=self.model, model_fallback=MODEL_FALLBACK_CHAIN,
                    messages=[
                        {"role": "system", "content": "你是一个精通商业逻辑与演讲设计的顶尖专家。请直接输出深度叙事蓝图的 Markdown，无需任何客套话。"},
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

    def generate_narrative_outline(self, content_context: str, constraints: Dict, content_file_path: str = None) -> List[Dict]:
        """
        生成深度叙事大纲 (Two-Step Pipeline)
        """
        logger.info("🧠 Narrative Agent: 正在构建叙事架构 (Phase 1/2: 提取蓝图)...")
        
        # Step 1: 提取蓝图
        core_logic_skeleton = self._extract_core_logic(content_context, constraints)
        logger.info("✅ 深度叙事蓝图提取完成。")
        logger.info("🧠 Narrative Agent: 正在构建叙事架构 (Phase 2/2: 生成分页 JSON)...")

        # 提取源文档中的图片
        base_dir = os.path.dirname(os.path.abspath(content_file_path)) if content_file_path else None
        source_images = self.extract_images_from_markdown(content_context, base_dir=base_dir)
        source_images_str = "\n".join([f"- {img}" for img in source_images[:10]]) # 列出前10张作为参考
        
        # 动态调整大纲结构要求
        page_count_constraint = constraints.get('page_count', '10')
        try:
            target_pages = int(page_count_constraint)
        except (ValueError, TypeError):
            target_pages = 10

        structure_instruction = ""
        if target_pages > 10:
            structure_instruction = """
   - **强制分节 (Section Structure)**：由于 PPT 页数较多，必须严格按照【深度叙事蓝图】来划分章节。
   - 每一页都必须归属于某个 Section。
   - 在每个 Section 开始时，必须插入一个 `section` 类型的过渡页。"""
        else:
            structure_instruction = """
   - **逻辑节奏**：必须严格按照【深度叙事蓝图】来划分 PPT 的起承转合。"""

        prompt = f"""你是一位顶尖的商业演示架构师（Presentation Architect）、TED 演讲教练与认知心理学专家。
你的任务是将一份完整的【深度叙事蓝图】和对应的【输入原文】，转化为一套逻辑严密、节奏感强、视觉张力拉满的 PPT 逐页设计 JSON。
请像 NotebookLM 等最聪明的 AI 一样，不仅提取信息，更懂得如何为演讲重塑信息。

【项目背景】
- 目标受众: {constraints['target_audience']}
- 演示类型: {constraints['presentation_type']}
- 预计时长: {constraints['duration']}
- 期望页数: {constraints['page_count'] or '根据内容自动规划(约10-15页，如内容极其丰富可延长至20-30页以保证不拥挤)'}
- 风格偏好: {constraints['style_preference']}

【深度叙事蓝图】 (CRITICAL: 必须严格遵循此蓝图的情绪节奏、核心洞察与内容映射。)
{core_logic_skeleton}

【输入原文】 (用于提取详细的论据、金句、数据和案例)
{content_context[:50000]} ... (内容过长已截断)

【可用素材图片 (Source Images)】
你需要仔细分析以下原生图片的 URL 名字或提供的信息。
如果用户在原文中包含了本地图片路径（如下所列），你必须判断该图片是否与当前幻灯片的主题和文本内容**强相关**。
**只有当图片的内容确实能作为当前页面观点的有效视觉证据或补充时，才将其加入 `native_images` 字段。**
**千万不要随意、草率地将不相关的图片硬塞到页面中！宁可不放图片，也不要放错图片。**
{source_images_str}

【任务要求】
1. **结构化与故事化 (Structure & Storytelling)**：{structure_instruction}
   - **严禁生硬堆砌**：所有的页面都必须服务于 Core Thesis，每一页都要有存在的理由。
   - **So What? 检查**：对每一页必须填写 `narrative_role`（在论证中的角色：铺垫/证据/转折/高潮/结论/金句）和 `one_takeaway`（观众听完本页应记住的唯一一句话，10字内）。这确保每页都有明确的叙事贡献。
   - **尊重源生框架**：如果【输入原文】是带有详细章节的目录或大纲（如 1.1, 1.2, 2.1...），请**细致地将其拆解为多张幻灯片**。不要把一整个大章节的内容全塞在一页里。一个知识点/一个小节对应一页或多页。

2. **内容提炼法则 (Content Refinement - CRITICAL)**：
   - PPT 不是 Word 的搬运工！**绝对不要把大段原话直接复制到 body 中**。
   - **Slide 上只放“提词器” (Body)**：将复杂的原文提炼为极简、有力、口语化或商业化的“Bullet Points (要点)”。每个论点最多 10-30 字，每页不超过 3-4 个论点。必须一目了然。
   - **把“肉”藏进备注 (Speaker Notes)**：为每页生成详尽的 `speaker_notes` 字段。将原文中那些精彩但冗长的长句、具体的案例细节、讲师需要补充的背景知识，全部放到这里。这样幻灯片才能保持清爽，同时不丢失任何信息深度。
   - **标题多设问、少平铺 (Headline - Q&A Style)**：大标题优先用设问句引导逻辑。**副标题按需出现**：仅当能补充关键信息或承上启下时使用；金句页、封面可省略。
   - **公式与金句 (Formula & Golden Quote)**：对核心概念须提炼为可记忆的形式。用 `hero` 页或显眼位置呈现。
   - **抬机率设计**：在合适位置穿插「可拍照页」——金句、翔实数据、框架图、公式、行动指引。每 10-15 页至少 2-3 处；结尾优先放一句可拍照金句。

3. **视觉与页面节奏 (Pacing & Visuals)**：
   - 使用 `hero` 页（大字报）来放大原文档中的金句、公式、情绪高潮，制造停顿和震撼。
   - **呼吸页 (breathing)**：适当穿插轻页面——只放一个问句、一个数字或半屏留白+过渡语，给听众 3-5 秒消化时间。
   - **密度交替**：信息页 ↔ 金句页 ↔ 数据页 ↔ 图/流程页，形成「强-弱」节奏。**结合演讲内容自然交替，不要为了节奏而节奏**。
   - 使用 `data` 页来单独呈现硬核数据对比。
   - **流程、框架、对比**：当内容描述过程（如 Input→AI→Output）、层级（如 1+N+X 金字塔）、或对比关系（如 注意力↘ vs 内容↗）时，必须使用 `flowchart`、`framework` 或 `comparison` 类型，并在 visual_suggestion 中明确要求绘制对应图表。
   - 首页 `cover` 极简，只写大主题和分享人。
   - **重要：`visual_suggestion` (配图/画面建议) 应该描述由 AI 生成的背景或插图。如果该页使用了 `native_images` (原生图片)，请在 `visual_suggestion` 中描述一个适合衬托这些原生图片的背景环境，并明确说明需要为原生图片留出空间。两者是互补关系。**

4. **页面类型定义**：
   - `cover`: 封面 (仅第1页)
   - `toc`: 目录 (可选用)
   - `section`: 章节过渡页 (用于开启新篇章)
   - `content`: 标准内容页 (图文混排)
   - `hero`: 金句页/核心观点页 (核心观点、公式，大字号，强视觉冲击)
   - `quote`: 名人名言页 (名人金句、引言。包含人物肖像与名言文字排版)
   - `infographic`: 信息图页 (高密度数据汇总、全景图、生态图、复杂架构图。使用 Bento Grid 或模块化布局)
   - `data`: 数据/图表页 (柱状图、折线图、饼图等)
   - `flowchart`: 流程图页 (过程、步骤、Input→Process→Output，body 为流程节点，左到右或上到下)
   - `framework`: 框架/层级页 (金字塔、层级模型，如 1+N+X，body 为各层定义)
   - `comparison`: 对比页 (两种趋势/力量对比，如 注意力↘ vs 内容↗，或 A vs B 对比)
   - `breathing`: 呼吸页 (轻页面：一个问句/一个数字/半屏留白+过渡语，用于消化与停顿)
   - `ending`: 封底/致谢页。**结尾优先放一句可拍照的金句**，提升「抬机率」。

   5. **图文重塑、图表与原生图片排版 (Text Layout, Charts & Native Images)**：
      - **全面弃用原生表格 (NO NATIVE TABLES)**：本系统不再支持原生PPT表格。遇到原文中的表格时：
        1. **纯数值表格**：若全是硬核数值（趋势/比例/份额），请提取为一页 `data` 类型，在 `text_content` 中增加 `table_data` 字段，且 `visualization` 必须指定为 `bar`、`line` 或 `pie`。
        2. **文字型表格/对比**：必须重构为普通的文字排版（如 `comparison` 双列对比、`framework` 逻辑结构 或 `bullets` 极简要点），将核心内容提炼放入 `body` 数组中。
        3. **极度复杂的巨型表格（如报价单）**：如果表格过于复杂无法简化，将其处理为一页包含总结性文字的 `content` 页面，并在 `speaker_notes` 中明确提示：“【重要】原文此处包含复杂表格，建议演讲者后续截图手动粘贴至本页”。
        **绝对禁止使用 type 为 table 或 visualization 为 table/auto！**
      - **原生图片智能排版 (Native Images Semantic Layout - VERY IMPORTANT)**：如果你判断原文中的某张本地图片与该页内容**强相关**（见上方"可用素材图片"列表），你**必须**在 JSON 中使用 `native_images` 字段来进行排版规划。
     - 只有在你非常有把握这张图片代表什么，并且它适合这张 PPT 时才使用它。
     - 为该页规划每个图片的绝对路径（path）和相对绝对坐标 `bounding_box`。
     - `left`, `top`, `width`, `height` 取值范围均在 `0.0` 到 `1.0` 之间。请根据内容的多少和图片的预期比例（横图/竖图）给出合理的 `width` 和 `height`，确保图片不要变形或被拉伸得太离谱。例如，如果是脑部扫描图（可能是横图或方图），给它大约 `width: 0.4, height: 0.5` 的空间。
     - **极度重要避让原则**：在 `visual_suggestion` 中，**必须明确写出**「请在画面[左侧/右侧/中间]留出大片纯净空白区域，用于放置原生图片」。如果不写，AI生成的文字会和原生图片严重重叠！

【JSON 数据结构标准】
[
  {{
    "page_num": 1,
    "section_title": "Part 1: 市场背景", 
    "type": "content", 
    "title": "系统内部标识用的页面标题",
    "core_message": "本页试图让观众记住的唯一核心信息（供 AI 绘图或设计参考）",
    "narrative_role": "铺垫|证据|转折|高潮|结论|金句",
    "one_takeaway": "观众听完本页应记住的唯一一句话（10字内）",
    "visualization": "bar/line/pie (仅在纯数值图表时填写，严禁使用table或auto)",
    "transition": "给演讲者的逻辑过渡提示（如何从上一页自然过渡到这一页）", 
    "text_content": {{
        "headline": "大标题，必须是带有观点的断言句 (例如：盲区：为何我们看不见？)",
        "table_data": {{ "headers": ["年度", "销量"], "rows": [["2023", "100"]] }}, // 仅在纯数值且 visualization=bar/line/pie 时使用，文字对比千万不要用！严禁使用 table
        "subhead": "副标题/导语（可选，仅当能补充关键信息时填写）",
        "body_format": "paragraph|bullets|data|quote|mixed",
        "body": [
            "极简论据1 (10-30字)：提炼自原文核心要点。", 
            "极简论据2 (10-30字)：提炼自原文核心要点。"
        ]
    }},
    "native_images": [
        {{
            "path": "原文中提到的图片路径或描述链接",
            "semantic_role": "这张图的业务意图，例如：新产品主界面，占据左侧",
            "bounding_box": {{ "left": 0.05, "top": 0.2, "width": 0.4, "height": 0.6 }}
        }}
    ],
    "speaker_notes": "演讲者备注（详细）：在这里保留原文中详细的案例、完整的长句论述、上下文背景等，确保讲师在看备注时能找回原文所有的细节深度。",
    "visual_suggestion": "画面隐喻/配图建议。结合蓝图中的视觉调性（Tone & Visual Metaphor），给出具体、有创意的画面描述。如果有可用的 source image 请注明。"
  }},
  ...
]

务必输出严格的、合法的 JSON 格式数组。绝不要包含 Markdown 代码块标记（如 ```json），直接从 [ 开始输出。不要截断！如果内容很长，请完整生成所有页面。"""

        max_retries = 2
        last_error = None
        for attempt in range(max_retries):
            try:
                response = chat_completion_with_fallback(
                    self.client, model=self.model, model_fallback=MODEL_FALLBACK_CHAIN,
                    messages=[
                        {"role": "system", "content": "你是一个代表世界最高水平的演示文稿架构师。你擅长把复杂的文档切分为有节奏感的演讲幻灯片。必须且只能输出合法的 JSON 数组，严禁在前后添加任何 Markdown 代码块标记（如 ```json 等）或其它说明文本。"},
                        {"role": "user", "content": prompt}
                    ],
                    temperature=0.4 if attempt > 0 else 0.5
                )
                content = response.choices[0].message.content.strip()
                # 尝试通过寻找外层中括号来提取 JSON
                start_idx = content.find('[')
                end_idx = content.rfind(']')
                if start_idx != -1 and end_idx != -1:
                    content = content[start_idx:end_idx + 1]
                
                return json.loads(content)
            except json.JSONDecodeError as e:
                last_error = e
                if attempt < max_retries - 1:
                    logger.warning(f"JSON 解析失败，重试 ({attempt + 1}/{max_retries}): {e}")
                else:
                    logger.error(f"叙事大纲 JSON 解析失败 (已重试): {e}")
                    raise
            except Exception as e:
                logger.error(f"叙事大纲生成失败: {e}")
                raise
        if last_error:
            raise last_error

    def preview_outline(self, outline: List[Dict]) -> str:
        """
        生成大纲的自然语言预览文本
        """
        preview_text = "=== 📋 PPT 叙事大纲预览 (Story Flow) ===\n\n"
        preview_text += f"**🤖 AI 架构师**：为了还原文章的深度逻辑，我为您规划了这份 **{len(outline)} 页** 的连贯叙事大纲。请重点关注每一页的【逻辑承接】与【演讲备注】：\n\n"
        
        for page in outline:
            preview_text += f"#### **P{page.get('page_num', '?')}: {page.get('text_content', {}).get('headline', page.get('title', '未命名'))}**  `[{page.get('type', 'content')}]`\n"
            
            # 增加过渡语展示，体现逻辑流
            if page.get('transition'):
                preview_text += f"> *🗣️ 逻辑承接*：{page['transition']}\n\n"
            if page.get('narrative_role') or page.get('one_takeaway'):
                parts = []
                if page.get('narrative_role'):
                    parts.append(f"角色：{page['narrative_role']}")
                if page.get('one_takeaway'):
                    parts.append(f"收获：{page['one_takeaway']}")
                preview_text += f"> *🎯 So What*：{' | '.join(parts)}\n\n"
            
            # 内容展示
            text_content = page.get('text_content', {})
            
            # 始终展示大标题和副标题（如果有）
            if text_content.get('headline'):
                preview_text += f"   **📌 幻灯片标题**：{text_content['headline']}\n"
            if text_content.get('subhead'):
                preview_text += f"   **📝 副标题/导语**：{text_content['subhead']}\n"
                
            if page.get('type') == 'hero':
                # Hero 页通常不需要冗长的 body，重点是 subhead 或 core_message
                pass
            elif page.get('type') in ['content', 'data'] and text_content.get('body'):
                preview_text += f"   **📄 极简要点 (Slide Text)**：\n"
                for item in text_content['body']:
                    preview_text += f"     - {item}\n"
            
            # 展示 speaker notes
            if page.get('speaker_notes'):
                preview_text += f"   **🎙️ 演讲备注 (Speaker Notes)**：\n     {page['speaker_notes']}\n"

            # 展示原生图片排版计划 (Native Images Layout)
            native_images = page.get('native_images', [])
            if not native_images and page.get('native_image'):
                native_images = [page.get('native_image')]
                
            if native_images:
                preview_text += f"   **📥 原生图片排版计划 (Native Images Layout)**：\n"
                for idx, img in enumerate(native_images):
                    path = img.get('path', 'unknown_path')
                    role = img.get('semantic_role', '')
                    bbox = img.get('bounding_box', {})
                    if bbox:
                        bbox_str = f"left: {bbox.get('left')}, top: {bbox.get('top')}, width: {bbox.get('width')}, height: {bbox.get('height')}"
                    else:
                        bbox_str = img.get('layout', 'center')
                    # 采用 HTML img 标签，可以在 Markdown 预览模式中直接显示小图，并隐藏长路径
                    import os
                    img_src = f"file://{path}" if os.path.isabs(path) else path
                    preview_text += f"     {idx+1}. {role} <img src=\"{img_src}\" height=\"40\" style=\"vertical-align: middle;\" /> (`bounding_box`: {bbox_str})\n"
            
            preview_text += "\n"
            
        preview_text += "---\n**🤖 系统提示**：这个逻辑流是否足够连贯？文案是否提炼得当？(Y/N/修改意见)"
        return preview_text

if __name__ == "__main__":
    pass
