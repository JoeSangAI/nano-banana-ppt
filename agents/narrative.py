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
