"""
Narrative Architecture Agent
负责将用户输入转化为深度叙事大纲
"""
import os
import json
import logging
import re
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

from openai import OpenAI
from ..utils.llm_client import chat_completion_with_fallback, MODEL_FALLBACK_CHAIN
from ..core.image_selector import ImageSelector

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class NarrativeAgent:
    def __init__(self, api_key: str, api_base: str = None, project_dir: str = None):
        self.client = OpenAI(
            api_key=api_key,
            base_url=api_base or "https://generativelanguage.googleapis.com/v1beta/openai",
            timeout=300.0,
            max_retries=3
        )
        self.model = "MiniMax-M2.7" # 统一使用 MiniMax M2.7
        self.outline_model = "MiniMax-M2.7" # 统一使用 MiniMax M2.7
        self.project_dir = project_dir  # 项目目录，用于保存下载的图片

    @staticmethod
    def detect_structured_outline(text: str) -> bool:
        """
        检测文本是否已经有成熟的分页大纲结构
        如果用户已经提供了明确的分页标题（如 "Slide 3: 标题"），返回 True
        """
        patterns = [
            r'Slide\s+\d+[:：]',      # "Slide 3: 标题"
            r'第\s*\d+\s*页[:：]',     # "第 3 页：标题"
            r'P\d+[:：]',             # "P3: 标题"
            r'幻灯片\s*\d+[:：]',      # "幻灯片 3：标题"
            r'##\s*第\s*\d+\s*页',    # "## 第 3 页"
            r'##\s*Slide\s+\d+',      # "## Slide 3"
        ]

        matches = sum(len(re.findall(p, text, re.IGNORECASE)) for p in patterns)

        # 如果找到 3 个以上的分页标记，认为是成熟大纲
        return matches >= 3

    @staticmethod
    def detect_complete_content_plan(text: str) -> Dict:
        """
        检测文本是否是一个完整的 content_plan.md

        返回：
        {
            "is_complete": bool,
            "page_count": int,
            "has_speaker_notes": bool,
            "has_tables": bool,
            "confidence": float  # 0-1
        }
        """
        # 检测分页标记
        page_patterns = [
            r'Slide\s+\d+[:：]',
            r'第\s*\d+\s*页[:：]',
            r'P\d+[:：]',
            r'幻灯片\s*\d+[:：]',
            r'##\s*第\s*\d+\s*页',
            r'##\s*Slide\s+\d+',
        ]

        page_matches = []
        for pattern in page_patterns:
            page_matches.extend(re.findall(pattern, text, re.IGNORECASE))

        page_count = len(page_matches)

        # 检测演讲备注
        speaker_notes_patterns = [
            r'\*\*演讲备注\*\*',
            r'\*\*Speaker Notes\*\*',
            r'演讲备注[:：]',
            r'Speaker Notes[:：]',
        ]
        speaker_notes_count = sum(len(re.findall(p, text, re.IGNORECASE)) for p in speaker_notes_patterns)
        has_speaker_notes = speaker_notes_count > 0

        # 检测数据表格 (Markdown table)
        table_pattern = r'\|[^\n]+\|[^\n]+\n\|[-:\s|]+\|'
        table_matches = re.findall(table_pattern, text)
        has_tables = len(table_matches) > 0

        # 检测副标题
        subtitle_patterns = [
            r'\*\*副标题\*\*',
            r'\*\*Subtitle\*\*',
        ]
        subtitle_count = sum(len(re.findall(p, text, re.IGNORECASE)) for p in subtitle_patterns)

        # 检测正文要点 (bullet points)
        bullet_pattern = r'^\s*[-*]\s+.+$'
        bullet_matches = re.findall(bullet_pattern, text, re.MULTILINE)
        has_bullets = len(bullet_matches) >= page_count  # 平均每页至少1个要点

        # 计算置信度
        confidence = 0.0

        if page_count >= 3:
            confidence += 0.3

        if has_speaker_notes and speaker_notes_count >= page_count * 0.5:
            confidence += 0.3

        if has_tables:
            confidence += 0.2

        if subtitle_count >= page_count * 0.3:
            confidence += 0.1

        if has_bullets:
            confidence += 0.1

        is_complete = page_count >= 3 and confidence >= 0.8

        return {
            "is_complete": is_complete,
            "page_count": page_count,
            "has_speaker_notes": has_speaker_notes,
            "has_tables": has_tables,
            "confidence": confidence
        }

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
            result = re.sub(r"^```(?:json)?\s*|```$", "", result, flags=re.MULTILINE|re.IGNORECASE).strip()
            return json.loads(result)
        except Exception:
            return {}

    def _load_feedback(self, project_dir: str = None) -> Dict:
        """
        加载用户对该项目/主题的历史反馈
        """
        if not project_dir:
            return {}

        feedback_file = Path(project_dir) / ".narrative_feedback.json"
        if feedback_file.exists():
            try:
                with open(feedback_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception:
                return {}
        return {}

    def _save_feedback(self, project_dir: str, feedback: Dict) -> None:
        """
        保存用户反馈到项目目录
        """
        if not project_dir:
            return

        feedback_file = Path(project_dir) / ".narrative_feedback.json"
        existing = self._load_feedback(project_dir)

        # 合并反馈，保留历史记录
        if 'history' not in existing:
            existing['history'] = []

        existing['history'].append({
            'timestamp': datetime.now().isoformat(),
            **feedback
        })

        # 更新最新反馈
        existing['latest'] = feedback

        try:
            with open(feedback_file, 'w', encoding='utf-8') as f:
                json.dump(existing, f, ensure_ascii=False, indent=2)
            logger.info(f"💾 用户反馈已保存到 {feedback_file}")
        except Exception as e:
            logger.warning(f"⚠️ 无法保存反馈: {e}")

    def _apply_feedback_to_constraints(self, constraints: Dict, feedback: Dict) -> Dict:
        """
        将历史反馈应用到约束中，优化生成效果
        """
        if not feedback:
            return constraints

        # 从反馈中提取调整项
        if 'page_count_adjustment' in feedback:
            pc = constraints.get('page_count', '10')
            try:
                base = int(pc)
                adj = feedback['page_count_adjustment']
                if isinstance(adj, int):
                    constraints['page_count'] = str(max(5, base + adj))
            except:
                pass

        if 'style_adjustment' in feedback:
            constraints['style_preference'] = feedback['style_adjustment']

        if 'narrative_notes' in feedback:
            # 将用户的叙事偏好注入 design_system
            notes = feedback['narrative_notes']
            existing_ds = constraints.get('design_system', '')
            constraints['design_system'] = f"{existing_ds}\n\n【用户叙事偏好】\n{notes}".strip()

        if 'avoid_topics' in feedback:
            # 用户不希望出现的话题
            avoid = feedback['avoid_topics']
            existing_ds = constraints.get('design_system', '')
            constraints['design_system'] = f"{existing_ds}\n\n【避免的话题】\n{avoid}".strip()

        return constraints

    def save_user_feedback(
        self,
        project_dir: str,
        feedback_type: str,
        feedback_content: Dict
    ) -> None:
        """
        公开方法：供外部调用保存用户反馈

        feedback_type: "outline_revision" | "page_modification" | "general"
        feedback_content: 具体反馈内容
        """
        feedback = {
            'type': feedback_type,
            **feedback_content
        }
        self._save_feedback(project_dir, feedback)

    def _enrich_outline_with_visual_decisions(self, outline: List[Dict], analyzed_images: List[Dict]) -> List[Dict]:
        """
        使用页面级自动选图器，对初始大纲做二次增强：
        - 固化 visual_intent / image_need_level / recommended_layout_family
        - 自动选择最适合的 native_images
        - 全局去重：同一张图不会出现在多个页面
        """
        if not outline:
            return outline

        selector = ImageSelector(self.client)
        enriched = []
        globally_selected_paths: List[str] = []

        for page in outline:
            decision = selector.select_images_for_page(
                page, analyzed_images, already_selected_paths=globally_selected_paths,
            )
            merged = dict(page)
            merged["visual_intent"] = decision.get("visual_intent", merged.get("visual_intent", "no_native_image"))
            merged["image_need_level"] = decision.get("image_need_level", merged.get("image_need_level", "none"))
            merged["recommended_layout_family"] = decision.get(
                "recommended_layout_family",
                merged.get("recommended_layout_family", "left_visual_right_text"),
            )
            merged["image_selection_reason"] = decision.get("selection_reason", "")
            merged["image_selection_confidence"] = decision.get("confidence", 0)

            selected_images = decision.get("native_images", [])
            if selected_images and decision.get("confidence", 0) >= 80:
                merged["native_images"] = selected_images
                for img in selected_images:
                    if img.get("path"):
                        globally_selected_paths.append(img["path"])
            else:
                merged.setdefault("native_images", [])

            enriched.append(merged)
        return enriched

    def extract_images_from_markdown(self, content: str, base_dir: str = None) -> List[str]:
        """
        从 Markdown 内容中提取图片链接
        如果设置了 project_dir，网络图片会下载到 project_dir/native_images/
        """
        import re
        import os
        # 匹配 ![alt](url) 格式
        images = re.findall(r'!\[.*?\]\((.*?)\)', content)

        # 确定下载目标目录：优先使用 project_dir/native_images，否则使用 base_dir
        download_dir = base_dir
        if self.project_dir:
            download_dir = os.path.join(self.project_dir, "native_images")
            os.makedirs(download_dir, exist_ok=True)
            logger.info(f"📁 图片将保存到项目目录: {download_dir}")

        valid_images = []
        for img in images:
            img = img.strip()

            # 如果是网络图片，尝试下载到 download_dir 并替换为本地路径
            if img.lower().startswith('http://') or img.lower().startswith('https://'):
                if download_dir:
                    import urllib.request
                    from urllib.parse import urlparse
                    try:
                        # Extract filename from URL or generate one
                        parsed_url = urlparse(img)
                        filename = os.path.basename(parsed_url.path)
                        if not filename or not any(filename.lower().endswith(ext) for ext in ['.png', '.jpg', '.jpeg', '.gif', '.webp']):
                            import uuid
                            filename = f"{uuid.uuid4()}.jpeg" # default to jpeg if unknown

                        local_path = os.path.join(download_dir, filename)

                        # Only download if it doesn't exist
                        if not os.path.exists(local_path):
                            logger.info(f"⬇️  下载网络图片: {img} -> {local_path}")
                            # Add headers to avoid 403 Forbidden
                            import ssl
                            context = ssl._create_unverified_context()
                            req = urllib.request.Request(img, headers={'User-Agent': 'Mozilla/5.0'})
                            with urllib.request.urlopen(req, context=context) as response, open(local_path, 'wb') as out_file:
                                out_file.write(response.read())
                            logger.info(f"✅ 下载成功: {os.path.basename(local_path)}")
                        else:
                            logger.info(f"♻️  图片已存在，跳过下载: {os.path.basename(local_path)}")

                        valid_images.append(local_path)
                    except Exception as e:
                        logger.warning(f"❌ 无法下载网络图片 {img}: {e}")
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

    def _parse_structured_outline(self, content_context: str, constraints: Dict) -> List[Dict]:
        """
        [大纲解析模式] 直接解析用户已有的成熟分页大纲
        保留用户的原始标题和结构，只做格式规范化
        这个模式不调用 LLM 改写标题，节省 token 和时间
        """
        logger.info("🧠 Narrative Agent: 检测到成熟大纲，使用解析模式（保留原文标题）...")

        # 使用正则表达式提取分页结构
        # 支持多种格式: "Slide 3: 标题", "第 3 页：标题", "## Slide 3" 等
        patterns = [
            (r'Slide\s+(\d+)[:：]\s*(.+?)(?=\n|$)', 'slide'),
            (r'第\s*(\d+)\s*页[:：]\s*(.+?)(?=\n|$)', 'page'),
            (r'P(\d+)[:：]\s*(.+?)(?=\n|$)', 'p'),
            (r'##\s*第\s*(\d+)\s*页[:：]?\s*(.+?)(?=\n|$)', 'markdown_page'),
            (r'##\s*Slide\s+(\d+)[:：]?\s*(.+?)(?=\n|$)', 'markdown_slide'),
        ]

        pages = []
        for pattern, pattern_type in patterns:
            matches = re.finditer(pattern, content_context, re.MULTILINE | re.IGNORECASE)
            for match in matches:
                page_num = int(match.group(1))
                title = match.group(2).strip()

                # 提取该页的内容（从当前标题到下一个标题之间的文本）
                start_pos = match.end()
                # 找到下一个分页标记的位置
                next_match = None
                for p, _ in patterns:
                    next_matches = list(re.finditer(p, content_context[start_pos:], re.MULTILINE | re.IGNORECASE))
                    if next_matches:
                        if next_match is None or next_matches[0].start() < next_match.start():
                            next_match = next_matches[0]

                if next_match:
                    page_content = content_context[start_pos:start_pos + next_match.start()].strip()
                else:
                    page_content = content_context[start_pos:].strip()

                pages.append({
                    'page_num': page_num,
                    'title': title,
                    'content': page_content[:1000],  # 限制长度
                    'pattern_type': pattern_type
                })

        if not pages:
            logger.warning("未能解析出分页结构，回退到智能叙事模式")
            return None

        # 按页码排序
        pages.sort(key=lambda x: x['page_num'])

        logger.info(f"✅ 解析到 {len(pages)} 页大纲，正在生成 JSON...")

        # 使用 LLM 将解析出的大纲转换为标准 JSON 格式
        # 但明确要求保留原标题，不要改写
        pages_summary = "\n".join([
            f"第 {p['page_num']} 页: {p['title']}\n内容摘要: {p['content'][:200]}..."
            for p in pages
        ])

        prompt = f"""你是一位 PPT 架构师。用户已经提供了一份成熟的分页大纲，你的任务是将其转换为标准 JSON 格式。

【重要】你必须严格保留用户的原始标题，不要改写或优化标题！

【用户大纲】
{pages_summary}

【项目背景】
- 目标受众: {constraints.get('target_audience', '通用受众')}
- 演示类型: {constraints.get('presentation_type', '商业演示')}
- 风格偏好: {constraints.get('style_preference', '专业商务')}

【任务要求】
1. 将每一页转换为 JSON 对象
2. **严格保留用户的原始标题**，放在 text_content.headline 字段中
3. 根据标题内容推断页面类型 (type)：
   - 如果标题包含"封面"、"标题"等 → cover
   - 如果标题包含"目录"、"大纲" → toc
   - 如果标题包含"vs"、"对比" → comparison
   - 如果标题包含"框架"、"模型" → framework
   - 如果标题包含"流程"、"步骤" → flowchart
   - 其他 → content
4. 从内容摘要中提取 2-4 个要点放入 body 数组
5. 生成简洁的 visual_suggestion（画面建议）

【JSON 格式】
[
  {{
    "page_num": 1,
    "type": "content",
    "text_content": {{
        "headline": "用户的原始标题（不要改写！）",
        "body": ["要点1", "要点2"]
    }},
    "speaker_notes": "根据内容摘要生成的演讲备注",
    "visual_suggestion": "画面建议"
  }}
]

务必输出严格的 JSON 数组，从 [ 开始，不要包含 Markdown 代码块标记。"""

        try:
            response = chat_completion_with_fallback(
                self.client, model=self.outline_model, model_fallback=MODEL_FALLBACK_CHAIN,
                messages=[
                    {"role": "system", "content": "你是一个 PPT 架构师。必须且只能输出合法的 JSON 数组。"},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.2  # 低温度，减少创造性改写
            )
            content = response.choices[0].message.content.strip()

            # 提取 JSON
            start_idx = content.find('[')
            end_idx = content.rfind(']')
            if start_idx != -1 and end_idx != -1:
                content = content[start_idx:end_idx + 1]

            outline = json.loads(content)
            logger.info(f"✅ 大纲解析完成，共 {len(outline)} 页")
            return outline

        except Exception as e:
            logger.error(f"大纲解析失败: {e}，回退到智能叙事模式")
            return None

    def _parse_complete_content_plan(self, content_context: str, content_file_path: str = None) -> List[Dict]:
        """
        [完整大纲直接复用模式] 纯文本解析，不调用 LLM

        100%保留用户原始内容，包括：
        - 标题、副标题
        - 正文要点（bullets）
        - 演讲备注
        - 数据表格
        """
        logger.info("🧠 Narrative Agent: 使用【直接复用模式】，100%保留原文...")

        # 提取分页结构
        page_patterns = [
            (r'Slide\s+(\d+)[:：]\s*(.+?)(?=\n|$)', 'slide'),
            (r'第\s*(\d+)\s*页[:：]\s*(.+?)(?=\n|$)', 'page'),
            (r'P(\d+)[:：]\s*(.+?)(?=\n|$)', 'p'),
            (r'##\s*第\s*(\d+)\s*页[:：]?\s*(.+?)(?=\n|$)', 'markdown_page'),
            (r'##\s*Slide\s+(\d+)[:：]?\s*(.+?)(?=\n|$)', 'markdown_slide'),
        ]

        pages_raw = []
        for pattern, pattern_type in page_patterns:
            matches = re.finditer(pattern, content_context, re.MULTILINE | re.IGNORECASE)
            for match in matches:
                page_num = int(match.group(1))
                title = match.group(2).strip()
                start_pos = match.end()

                # 找到下一个分页标记
                next_match = None
                for p, _ in page_patterns:
                    next_matches = list(re.finditer(p, content_context[start_pos:], re.MULTILINE | re.IGNORECASE))
                    if next_matches:
                        if next_match is None or next_matches[0].start() < next_match.start():
                            next_match = next_matches[0]

                if next_match:
                    page_content = content_context[start_pos:start_pos + next_match.start()].strip()
                else:
                    page_content = content_context[start_pos:].strip()

                pages_raw.append({
                    'page_num': page_num,
                    'title': title,
                    'content': page_content,
                    'pattern_type': pattern_type
                })

        if not pages_raw:
            logger.warning("未能解析出分页结构")
            return None

        # 按页码排序
        pages_raw.sort(key=lambda x: x['page_num'])

        logger.info(f"✅ 解析到 {len(pages_raw)} 页，正在提取详细内容...")

        # 解析每一页的详细内容
        outline = []
        for page in pages_raw:
            page_content = page['content']

            # 提取真正的标题（从 **标题**：xxx 格式中提取，而不是使用页面类型名）
            title_match = re.search(r'\*\*标题\*\*[:：]?\s*(.+?)(?=\n|$)', page_content, re.IGNORECASE)
            headline = title_match.group(1).strip() if title_match else page['title']

            # 提取副标题
            subtitle_match = re.search(r'\*\*副标题\*\*[:：]?\s*(.+?)(?=\n|$)', page_content, re.IGNORECASE)
            subtitle = subtitle_match.group(1).strip() if subtitle_match else ""

            # 提取演讲备注 (支持 🎙️ emoji 和 (Speaker Notes) 后缀)
            # 格式: **🎙️ 演讲备注**：[换行]> 内容 或 **演讲备注**：[换行]内容
            # 结束条件：空行+新块 / --- 分隔线 / 文件结尾
            speaker_notes_match = re.search(
                r'\*\*(?:🎙️\s*)?演讲备注\*\*(?:\s*\(Speaker Notes\))?[:：]?\s*\n\s*(>\s*)?(.*?)(?=\n\s*\n\*\*|\n\s*[-─]{3,}\s*(?:\n|$))',
                page_content, re.DOTALL | re.IGNORECASE
            )
            if speaker_notes_match:
                # group(1) = ">\s*" 前缀(如果存在), group(2) = 内容
                speaker_notes = (speaker_notes_match.group(2) or "").strip()
                # 去掉末尾可能残留的孤立 ">"
                if speaker_notes.endswith('>'):
                    speaker_notes = speaker_notes.rstrip('>').strip()
            else:
                speaker_notes = ""

            # 提取正文要点 (bullet points)
            bullet_pattern = r'^\s*[-*]\s+(.+)$'
            bullets = re.findall(bullet_pattern, page_content, re.MULTILINE)

            # 提取数据表格
            table_pattern = r'(\|[^\n]+\|[^\n]+\n\|[-:\s|]+\|[^\n]*(?:\n\|[^\n]+\|)*)'
            table_matches = re.findall(table_pattern, page_content)

            # 推断页面类型
            page_type = "content"
            title_lower = page['title'].lower()
            if any(kw in title_lower for kw in ["封面", "标题", "cover", "title"]):
                page_type = "cover"
            elif any(kw in title_lower for kw in ["目录", "大纲", "toc", "outline"]):
                page_type = "toc"
            elif any(kw in title_lower for kw in ["vs", "对比", "comparison"]):
                page_type = "comparison"
            elif any(kw in title_lower for kw in ["框架", "模型", "framework"]):
                page_type = "framework"
            elif any(kw in title_lower for kw in ["流程", "步骤", "flowchart"]):
                page_type = "flowchart"
            elif table_matches:
                page_type = "data"

            # 过滤掉 body 中混入的标题、副标题、演讲备注等项
            filtered_bullets = [b for b in bullets if not (
                '**标题**' in b or
                '**副标题**' in b or
                '演讲备注' in b
            )]

            # 构建 JSON 结构
            page_json = {
                "page_num": page['page_num'],
                "type": page_type,
                "text_content": {
                    "headline": headline,
                    "subhead": subtitle,
                    "body": filtered_bullets if filtered_bullets else []
                },
                "speaker_notes": speaker_notes,
                "visual_suggestion": f"根据标题「{headline}」设计画面"
            }

            # 如果有表格，添加到 body 中
            if table_matches:
                page_json["table_data"] = table_matches[0]

            outline.append(page_json)

        logger.info(f"✅ 完整大纲解析完成，共 {len(outline)} 页，100%保留原文")
        return outline

    def _fix_json_output(self, broken_json: str, expected_count: int = None) -> list:
        """
        修复破损的 JSON 数组，尝试多种策略：
        1. 提取内部完整数组
        2. 补全缺失的括号
        3. 修复尾部逗号
        4. 逐个提取 JSON 对象并重新组装
        """
        import json

        # 策略1: 找最完整的数组
        start_idx = broken_json.find('[')
        end_idx = broken_json.rfind(']')
        if start_idx != -1 and end_idx != -1 and end_idx > start_idx:
            candidate = broken_json[start_idx:end_idx + 1]
            try:
                return json.loads(candidate)
            except json.JSONDecodeError:
                pass

        # 策略2: 补全缺失的尾部
        candidate = broken_json.strip()
        if not candidate.endswith(']'):
            candidate = candidate.rstrip(',') + ']'
        try:
            return json.loads(candidate)
        except json.JSONDecodeError:
            pass

        # 策略3: 修复尾部逗号
        candidate = re.sub(r',(\s*[}\]])', r'\1', candidate)
        try:
            return json.loads(candidate)
        except json.JSONDecodeError:
            pass

        # 策略4: 逐个提取 JSON 对象
        objects = []
        # 找所有可能的 JSON 对象（以 { 开头）
        brace_positions = [m.start() for m in re.finditer(r'\{', candidate)]
        for i, start in enumerate(brace_positions):
            # 找对应的结束 brace
            depth = 0
            for j in range(start, len(candidate)):
                if candidate[j] == '{':
                    depth += 1
                elif candidate[j] == '}':
                    depth -= 1
                    if depth == 0:
                        obj_str = candidate[start:j + 1]
                        try:
                            obj = json.loads(obj_str)
                            # 验证关键字段
                            if 'page_num' in obj or 'type' in obj:
                                objects.append(obj)
                        except:
                            pass
                        break

        if objects and (expected_count is None or len(objects) >= expected_count * 0.5):
            # 按 page_num 排序并返回
            try:
                objects.sort(key=lambda x: x.get('page_num', 999))
            except:
                pass
            return objects

        raise ValueError(f"无法修复破损的 JSON，共提取到 {len(objects)} 个对象")

    def _build_minimal_outline_prompt(self, content_slice: str, constraints: Dict, core_logic_skeleton: str = None) -> str:
        """
        构建最小化输出 prompt，用于最终兜底
        只要求输出 page_num, type, text_content.headline, body 四个核心字段
        """
        return f"""你是一个 PPT 架构师。请将下面的文档转化为最简洁的幻灯片 JSON 数组。

【项目背景】
- 目标受众: {constraints.get('target_audience', '通用受众')}
- 演示类型: {constraints.get('presentation_type', '商业演示')}

【深度叙事蓝图】
{core_logic_skeleton[:2000] if core_logic_skeleton else '无'}

【输入原文】
{content_slice[:3000]}

【任务要求】
请生成 {constraints.get('page_count', '10')} 页幻灯片，每页只输出：
- page_num: 页码（整数）
- type: 页面类型（content/hero/cover/ending）
- text_content.headline: 标题
- body: 要点数组（2-3个简短要点）

【JSON 格式】
[
  {{"page_num": 1, "type": "cover", "text_content": {{"headline": "标题"}}, "body": ["要点1", "要点2"]}},
  ...
]

直接输出 JSON 数组，不要有任何其他文字："""

    def _heal_outline_schema(self, outline: list) -> list:
        """
        修复大纲中缺失或错误的关键字段
        """
        healed = []
        for page in outline:
            if not isinstance(page, dict):
                continue

            # 确保有 text_content
            if 'text_content' not in page:
                page['text_content'] = {}
            tc = page['text_content']

            # 确保 headline
            if 'headline' not in tc:
                # 尝试从其他字段获取
                tc['headline'] = page.get('title') or page.get('core_message') or f"第{page.get('page_num', '?')}页"
            elif not tc['headline']:
                tc['headline'] = f"第{page.get('page_num', '?')}页"

            # 确保 body
            if 'body' not in page:
                page['body'] = []
            elif page['body'] is None:
                page['body'] = []

            # 确保 type
            if 'type' not in page or not page['type']:
                page['type'] = 'content'

            # 确保 page_num
            if 'page_num' not in page or not isinstance(page['page_num'], int):
                try:
                    page['page_num'] = int(page.get('page_num', len(healed) + 1))
                except:
                    page['page_num'] = len(healed) + 1

            # 移动嵌套错误
            if 'title' in page and 'text_content' in page:
                if not tc['headline']:
                    tc['headline'] = page.pop('title')

            healed.append(page)

        return healed

    def _normalize_page_numbers(self, outline: list) -> list:
        """
        确保 page_num 是连续整数，从1开始
        """
        for i, page in enumerate(outline):
            page['page_num'] = i + 1
        return outline

    def _validate_outline_schema(self, outline: list) -> tuple:
        """
        验证大纲 schema 的关键字段，返回 (is_valid, errors)
        """
        errors = []
        required_fields = ['page_num', 'type', 'text_content']

        for i, page in enumerate(outline):
            if not isinstance(page, dict):
                errors.append(f"Page {i}: 不是字典对象")
                continue

            # 检查必需字段
            for field in required_fields:
                if field not in page:
                    errors.append(f"Page {i}: 缺少必需字段 '{field}'")

            # 验证 text_content 结构
            if 'text_content' in page:
                tc = page['text_content']
                if not isinstance(tc, dict):
                    errors.append(f"Page {i}: text_content 不是字典")
                elif 'headline' not in tc:
                    errors.append(f"Page {i}: text_content 缺少 headline")

            # 验证 page_num 是整数
            if 'page_num' in page and not isinstance(page['page_num'], int):
                try:
                    page['page_num'] = int(page['page_num'])
                except:
                    errors.append(f"Page {i}: page_num 无法转换为整数")

        return (len(errors) == 0, errors)

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

    def generate_narrative_outline(self, content_context: str, constraints: Dict, content_file_path: str = None, reuse_existing: bool = False) -> List[Dict]:
        """
        生成深度叙事大纲 (Three-Mode Pipeline)

        智能判断三种模式：
        1. 完整大纲直接复用模式（新增）- 100%保留原文，不调用LLM
        2. 成熟大纲解析模式（现有）- 保留原标题，LLM转换格式
        3. 智能叙事模式（现有）- LLM生成叙事架构
        """

        # 📝 加载用户历史反馈并应用到约束中
        project_dir = None
        if content_file_path:
            project_dir = os.path.dirname(os.path.abspath(content_file_path))

        feedback = self._load_feedback(project_dir)
        if feedback:
            logger.info(f"📝 检测到历史反馈，应用到本次生成...")
            constraints = self._apply_feedback_to_constraints(dict(constraints), feedback.get('latest', {}))

    def _merge_multiple_documents(self, file_paths: list) -> tuple:
        """
        合并多个文档的内容和元数据
        返回: (merged_content, doc_metadata_list)
        """
        merged_parts = []
        doc_metadata = []

        for path in file_paths:
            try:
                with open(path, 'r', encoding='utf-8') as f:
                    content = f.read()

                filename = os.path.basename(path)
                doc_label = os.path.splitext(filename)[0]

                merged_parts.append(f"【文档: {doc_label}】\n{content[:5000]}")
                doc_metadata.append({
                    'path': path,
                    'label': doc_label,
                    'length': len(content)
                })
                logger.info(f"📄 已加载文档: {doc_label} ({len(content)} 字)")
            except Exception as e:
                logger.warning(f"⚠️ 无法读取文档 {path}: {e}")

        merged_content = "\n\n---\n\n".join(merged_parts)
        return merged_content, doc_metadata

    def generate_narrative_outline_multi(
        self,
        content_file_paths: list,
        constraints: Dict,
        reuse_existing: bool = False
    ) -> List[Dict]:
        """
        多文档联合分析模式
        接收多个文档路径，联合分析后生成统一的叙事大纲
        """
        if len(content_file_paths) == 1:
            return self.generate_narrative_outline(
                content_context=open(content_file_paths[0], 'r', encoding='utf-8').read(),
                constraints=constraints,
                content_file_path=content_file_paths[0],
                reuse_existing=reuse_existing
            )

        logger.info(f"📚 检测到 {len(content_file_paths)} 个文档，进入联合分析模式...")

        merged_content, doc_metadata = self._merge_multiple_documents(content_file_paths)

        enhanced_constraints = dict(constraints)
        doc_names = [d['label'] for d in doc_metadata]
        enhanced_constraints['design_system'] = f"""
{enhanced_constraints.get('design_system', '')}

【多文档联合分析】
参与文档: {', '.join(doc_names)}
请识别各文档之间的关系（补充/对比/展开），并在叙事中体现这种关系。
""".strip()

        return self.generate_narrative_outline(
            content_context=merged_content,
            constraints=enhanced_constraints,
            content_file_path=content_file_paths[0],
            reuse_existing=reuse_existing
        )

    def generate_narrative_outline(self, content_context: str, constraints: Dict, content_file_path: str = None, reuse_existing: bool = False) -> List[Dict]:
        """
        生成深度叙事大纲 (Three-Mode Pipeline)

        智能判断三种模式：
        1. 完整大纲直接复用模式（新增）- 100%保留原文，不调用LLM
        2. 成熟大纲解析模式（现有）- 保留原标题，LLM转换格式
        3. 智能叙事模式（现有）- LLM生成叙事架构
        """

        # 📝 加载用户历史反馈并应用到约束中
        project_dir = None
        if content_file_path:
            project_dir = os.path.dirname(os.path.abspath(content_file_path))

        feedback = self._load_feedback(project_dir)
        if feedback:
            logger.info(f"📝 检测到历史反馈，应用到本次生成...")
            constraints = self._apply_feedback_to_constraints(dict(constraints), feedback.get('latest', {}))

        # 🔍 检测是否是完整的 content_plan.md
        complete_plan_info = self.detect_complete_content_plan(content_context)

        if reuse_existing or (complete_plan_info["is_complete"] and complete_plan_info["confidence"] >= 0.8):
            logger.info("✅ 检测到完整大纲，使用【直接复用模式】（100%保留原文，不调用LLM）")

            # 纯文本解析，不调用 LLM
            parsed_outline = self._parse_complete_content_plan(content_context, content_file_path)

            if parsed_outline:
                # 仅进行图片增强（不修改文本内容）
                base_dir = os.path.dirname(os.path.abspath(content_file_path)) if content_file_path else None
                raw_source_images = self.extract_images_from_markdown(content_context, base_dir=base_dir)

                analyzed_images = []
                if raw_source_images:
                    logger.info(f"🧠 Narrative Agent: 从源文档找到 {len(raw_source_images)} 张图片，正在进行语义过滤...")
                    selector = ImageSelector(self.client)
                    analyzed_images = selector.batch_analyze_images(raw_source_images)

                return self._enrich_outline_with_visual_decisions(parsed_outline, analyzed_images)

        # 🔍 检测用户输入是否已有成熟的分页大纲
        has_structured_outline = self.detect_structured_outline(content_context)

        if has_structured_outline:
            logger.info("✅ 检测到成熟大纲结构，使用【解析模式】（保留原标题，节省 token）")

            # 尝试直接解析大纲
            parsed_outline = self._parse_structured_outline(content_context, constraints)

            if parsed_outline:
                # 解析成功，进行图片增强
                base_dir = os.path.dirname(os.path.abspath(content_file_path)) if content_file_path else None
                raw_source_images = self.extract_images_from_markdown(content_context, base_dir=base_dir)

                analyzed_images = []
                if raw_source_images:
                    logger.info(f"🧠 Narrative Agent: 从源文档找到 {len(raw_source_images)} 张图片，正在进行语义过滤...")
                    selector = ImageSelector(self.client)
                    analyzed_images = selector.batch_analyze_images(raw_source_images)

                return self._enrich_outline_with_visual_decisions(parsed_outline, analyzed_images)
            else:
                logger.warning("⚠️ 解析失败，回退到【智能叙事模式】")
        else:
            logger.info("✅ 未检测到成熟大纲，使用【智能叙事模式】（LLM 生成叙事架构）")

        # 智能叙事模式（原有逻辑）
        logger.info("🧠 Narrative Agent: 正在构建叙事架构 (Phase 1/2: 提取蓝图)...")

        # Step 1: 提取蓝图
        core_logic_skeleton = self._extract_core_logic(content_context, constraints)
        logger.info("✅ 深度叙事蓝图提取完成。")
        logger.info("🧠 Narrative Agent: 正在构建叙事架构 (Phase 2/2: 生成分页 JSON)...")

        # 提取源文档中的图片，并使用多模态视觉过滤掉无用/不相关的图
        base_dir = os.path.dirname(os.path.abspath(content_file_path)) if content_file_path else None
        raw_source_images = self.extract_images_from_markdown(content_context, base_dir=base_dir)
        
        source_images = []
        analyzed_images = []
        if raw_source_images:
            logger.info(f"🧠 Narrative Agent: 从源文档找到 {len(raw_source_images)} 张图片，正在进行语义过滤...")
            selector = ImageSelector(self.client)
            analyzed_images = selector.batch_analyze_images(raw_source_images)
            
            # 将有用的图片附带上它们的语义理解提供给模型，不再盲人摸象
            for img_info in analyzed_images:
                path = img_info.get("path", "")
                summary = img_info.get("semantic_summary", "")
                img_type = img_info.get("image_type", "unknown")
                source_images.append(
                    f"- 图片ID: {os.path.basename(path)}\n  类型: {img_type}\n  画面内容: {summary}"
                )
        else:
            logger.info("🧠 Narrative Agent: 未从源文档找到有效图片")

        source_images_str = "\n\n".join(source_images[:8]) # 供日志与后续 review 使用
        
        # 动态调整大纲结构要求
        page_count_constraint = constraints.get('page_count', '10')
        try:
            target_pages = int(page_count_constraint)
        except (ValueError, TypeError):
            target_pages = 10

        structure_instruction = ""
        # 估算内容密度，决定拆分粒度
        content_length = len(content_context)
        content_density = content_length / max(target_pages, 1)  # 每页平均字数

        if target_pages > 10:
            structure_instruction = f"""
   - **【精确分页规则】**：用户要求 {target_pages} 页，每页内容密度约 {int(content_density)} 字/页。
   - **每个主要论点 = 1-3 页**：一个核心观点需要"金句页(1页) + 论述页(1-2页)"
   - **每个小节标题 = 1 页 section 过渡页**
   - **数据/案例 = 单独 1 页**
   - **禁止**：把 2 个独立论点塞进同一页
   - **强制分节 (Section Structure)**：必须严格按叙事蓝图划分章节，每节以 `section` 类型过渡页开始。"""
        else:
            # 短PPT：每个主要论点单独成页
            structure_instruction = f"""
   - **【分页规则】**：每个主要论点单独成页，每页控制在 {int(content_density * 1.5)} 字以内。
   - **禁止**：把多个独立观点合并到一页。
   - **逻辑节奏**：严格按叙事蓝图划分起承转合。"""

        outline_content_limit = 8000 if len(content_context) > 20000 else 16000
        content_slice = content_context[:outline_content_limit]

        def build_outline_prompt(content_excerpt: str, lightweight: bool = False) -> str:
            lightweight_note = ""
            if lightweight:
                lightweight_note = """
【轻量模式说明】
- 当前请求处于稳定性优先模式。
- 请优先保证输出合法完整的 JSON 数组。
- 如有必要，减少页数密度，避免过细拆分。
- 不要尝试输出过度复杂的图片规划，只需输出视觉意图、图片需求强度和推荐布局倾向。"""

            return f"""你是一位顶尖的商业演示架构师（Presentation Architect）、TED 演讲教练与认知心理学专家。
你的任务是将一份完整的【深度叙事蓝图】和对应的【输入原文】，转化为一套逻辑严密、节奏感强、视觉张力拉满的 PPT 逐页设计 JSON。
请像 NotebookLM 等最聪明的 AI 一样，不仅提取信息，更懂得如何为演讲重塑信息。

【项目背景】
- 目标受众: {constraints['target_audience']}
- 演示类型: {constraints['presentation_type']}
- 预计时长: {constraints['duration']}
- 期望页数: {constraints['page_count'] or '根据内容自动规划(约10-15页)'} （系统指令：必须至少生成 {constraints['page_count']} 页，如果不够请将内容拆分得更细致！比如一个观点拆成两页，一页是金句，一页是案例展开。）
- 风格偏好: {constraints['style_preference']}

【深度叙事蓝图】 (CRITICAL: 必须严格遵循此蓝图的情绪节奏、核心洞察与内容映射。)
{core_logic_skeleton}

{constraints.get('design_system', '')}

【输入原文】 (用于提取详细的论据、金句、数据和案例)
{content_excerpt} ... (内容过长已截断)

【可用素材图片 (Source Images)】
图片候选会在后续由"自动视觉导演"模块单独做页面级选图和布局判断，你无需在此规划选图。
{lightweight_note}

【任务要求】
1. **结构化与故事化 (Structure & Storytelling)**：{structure_instruction}
   - **严禁生硬堆砌**：所有的页面都必须服务于 Core Thesis，每一页都要有存在的理由。
   - **So What? 检查**：对每一页必须填写 `narrative_role`（在论证中的角色：铺垫/证据/转折/高潮/结论/金句）和 `one_takeaway`（观众听完本页应记住的唯一一句话，10字内）。这确保每页都有明确的叙事贡献。
   - **尊重源生框架**：如果【输入原文】是带有详细章节的目录或大纲（如 1.1, 1.2, 2.1...），请**细致地将其拆解为多张幻灯片**。不要把一整个大章节的内容全塞在一页里。一个知识点/一个小节对应一页或多页。
   - **语言一致性 (Language Consistency)**：确保输出语言与【输入原文】及【目标受众】的语言习惯保持一致。除非需要引用外文名言、专有名词，或者明确知道受众是外语人群，否则不要在中文语境下随机跳转到英文。

2. **内容提炼法则 (Content Refinement - CRITICAL)**：
   - PPT 不是 Word 的搬运工！**绝对不要把大段原话直接复制到 body 中**。
   - **【Body 简洁硬性规则】**：每条 body 不超过 20 字！使用短语而非完整句子。例如：”用户流失严重” 而非 “根据数据显示，用户流失情况非常严重”。
   - **【打破僵化列表】**：不要全篇都用生硬的”名词：解释”这样的 Bullet Points！
     - 你可以使用连贯的**一两句短语或短段落 (Paragraph)**。
     - 你也可以只放**几个核心关键词 (Keywords)**。
     - 只有在真正需要并列列举时，才使用列表项。增加文案的可读性、连贯性和力量感。
   - **【Speaker Notes 详细度强制要求】**：每页 speaker_notes 至少 50 字！必须包含：具体案例细节 / 原文背景 / 听众可能的问题及回答思路。如果没有详细内容，标注”（无）”。
   - **【标题必须设问】**：至少 60% 的页面标题必须是设问句！格式：”[核心词]是什么/为何/如何？” 例如：”为何增长陷入停滞？”、”如何突破瓶颈？”、”什么才是真正的机会？”
   - **公式与金句 (Formula & Golden Quote)**：对核心概念须提炼为可记忆的形式。用 `hero` 页或显眼位置呈现。
   - **抬机率设计**：在合适位置穿插「可拍照页」——金句、翔实数据、框架图、公式、行动指引。每 10-15 页至少 2-3 处；结尾优先放一句可拍照金句。

3. **视觉与页面节奏 (Pacing & Visuals)**：
   - 使用 `hero` 页（大字报）来放大原文档中的金句、公式、情绪高潮，制造停顿和震撼。
   - **呼吸页 (breathing)**：适当穿插轻页面——只放一个问句、一个数字或半屏留白+过渡语，给听众 3-5 秒消化时间。
   - **密度交替**：信息页 ↔ 金句页 ↔ 数据页 ↔ 图/流程页，形成「强-弱」节奏。**结合演讲内容自然交替，不要为了节奏而节奏**。
   - 使用 `data` 页来单独呈现硬核数据对比。
   - **流程、框架、对比**：当内容描述过程（如 Input→AI→Output）、层级（如 1+N+X 金字塔）、或对比关系（如 注意力↘ vs 内容↗）时，必须使用 `flowchart`、`framework` 或 `comparison` 类型，并在 visual_suggestion 中明确要求绘制对应图表。
   - 首页 `cover` 极简，只写大主题和分享人。
   - **【最重要的一点】`visual_suggestion` (配图/画面建议)**：
     - 请确保你设计的任何场景或画面建议，都**必须百分百符合并融合进全局视觉风格（Global Visual Design System）**中！
     - 无论是隐喻、场景还是构图，都不要与这套视觉规范产生任何冲突。你需要思考：在这个特定风格下，这个概念应该如何呈现。
     - 如果该页使用了 `native_images` (原生图片)，请描述一个适合衬托原生图片的背景环境，并明确说明需要为原生图片留出空白安全区。

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
      - **原生图片 (Native Images)**：`native_images` 字段可选输出。后续自动视觉导演会基于候选图做最终决定。

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
            "这里可以是一句有力量的短句，或者一小段说明文本。", 
            "也可以是几个并列的关键词，不要拘泥于生硬的列表格式。"
        ]
    }},
    "native_images": [
        {{
            "path": "原文中提到的图片路径或描述链接",
            "semantic_role": "这张图的业务意图，例如：新产品主界面，占据左侧",
            "integration_mode": "overlay", // "overlay" 或 "blend"
            "bounding_box": {{ "left": 0.05, "top": 0.2, "width": 0.4, "height": 0.6 }}
        }}
    ],
    "speaker_notes": "演讲者备注（详细）：在这里保留原文中详细的案例、完整的长句论述、上下文背景等，确保讲师在看备注时能找回原文所有的细节深度。",
    "visual_suggestion": "画面隐喻/配图建议。结合蓝图中的视觉调性（Tone & Visual Metaphor），给出具体、有创意的画面描述。如果有可用的 source image 请注明。"
  }},
  ...
]

务必输出严格的、合法的 JSON 格式数组。绝不要包含 Markdown 代码块标记（如 ```json），直接从 [ 开始输出。不要截断！如果内容很长，请完整生成所有页面。"""

        prompt = build_outline_prompt(content_slice, lightweight=False)

        max_retries = 3  # 增加一次重试
        last_error = None
        for attempt in range(max_retries):
            try:
                if attempt == 1:
                    # Stability fallback: shorter input, simpler planning burden.
                    prompt = build_outline_prompt(content_slice[: min(len(content_slice), 5000)], lightweight=True)
                elif attempt == 2:
                    # 最后的兜底：要求模型只输出最核心的字段
                    prompt = self._build_minimal_outline_prompt(content_slice, constraints, core_logic_skeleton)
                    logger.info("🧠 Narrative Agent: 使用最小化输出提示进行最终尝试...")

                response = chat_completion_with_fallback(
                    self.client, model=self.outline_model, model_fallback=MODEL_FALLBACK_CHAIN,
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

                # 策略1: 直接解析
                try:
                    outline = json.loads(content)
                except json.JSONDecodeError:
                    # 策略2: 尝试修复破损 JSON
                    logger.warning(f"JSON 直接解析失败，尝试修复...")
                    outline = self._fix_json_output(content)

                # 策略3: 验证 schema 并修复
                is_valid, errors = self._validate_outline_schema(outline)
                if not is_valid:
                    logger.warning(f"Schema 验证失败，尝试修复: {errors[:3]}")
                    outline = self._heal_outline_schema(outline)

                # 确保 page_num 是连续整数
                outline = self._normalize_page_numbers(outline)

                logger.info(f"✅ 叙事大纲生成完成，共 {len(outline)} 页")
                return self._enrich_outline_with_visual_decisions(outline, analyzed_images)

            except json.JSONDecodeError as e:
                last_error = e
                if attempt < max_retries - 1:
                    logger.warning(f"JSON 解析失败，重试 ({attempt + 1}/{max_retries}): {e}")
                else:
                    logger.error(f"叙事大纲 JSON 解析失败 (已重试 {max_retries} 次): {e}")
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
                    mode = img.get('integration_mode', 'overlay')
                    mode_str = "[融合]" if mode == "blend" else "[叠加]"
                    bbox = img.get('bounding_box', {})
                    if bbox:
                        bbox_str = f"left: {bbox.get('left')}, top: {bbox.get('top')}, width: {bbox.get('width')}, height: {bbox.get('height')}"
                    else:
                        bbox_str = img.get('layout', 'center')
                    # 采用 HTML img 标签，可以在 Markdown 预览模式中直接显示小图，并隐藏长路径
                    import os
                    img_src = f"file://{path}" if os.path.isabs(path) else path
                    preview_text += f"     {idx+1}. {mode_str} {role} <img src=\"{img_src}\" height=\"40\" style=\"vertical-align: middle;\" /> (`bounding_box`: {bbox_str})\n"
            
            preview_text += "\n"
            
        preview_text += "---\n**🤖 系统提示**：这个逻辑流是否足够连贯？文案是否提炼得当？(Y/N/修改意见)"
        return preview_text

if __name__ == "__main__":
    pass
