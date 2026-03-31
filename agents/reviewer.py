"""
Visual Prompt Reviewer Agent
负责在 visual prompt 生成后、交给 NB2 生图前做最后一道质量把关
"""
import logging
import re

logger = logging.getLogger(__name__)


class ReviewerAgent:
    """Visual Prompt 质量审阅 Agent"""

    def __init__(self, llm_client):
        self.client = llm_client
        self.model = "MiniMax-M2.7"

    def review_visual_prompt(
        self,
        visual_prompt: str,
        headline: str = "",
        body: list = None,
        speaker_notes: str = "",
        page_num: int = None,
        style_config: dict = None,
        global_style: str = "",
        context: dict = None
    ) -> str:
        """
        审阅和改进单个 visual prompt

        Args:
            visual_prompt: MiniMax 生成的初稿
            headline: 页面标题
            body: 页面正文列表
            speaker_notes: 演讲备注
            page_num: 页码
            style_config: 全局风格配置
            global_style: 全局风格描述（Design Manifesto）
            context: 上下文（前后页的 visual_prompt，可选）

        Returns:
            改进后的 visual_prompt（终稿）
        """
        if body is None:
            body = []
        logger.info(f"🔍 Reviewer: 正在审阅 P{page_num or '?'}...")

        review_prompt = self._build_review_prompt(
            visual_prompt, headline, body, speaker_notes,
            style_config or {}, global_style, context
        )

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": self._get_system_prompt()},
                    {"role": "user", "content": review_prompt}
                ],
                temperature=0.3
            )

            result = response.choices[0].message.content.strip()

            # 清理 <think> 标签
            result = re.sub(
                r'<think>.*?</think>', '', result,
                flags=re.DOTALL | re.IGNORECASE
            ).strip()

            # 清理 markdown 标记
            result = re.sub(r'^```.*?\n', '', result)
            result = re.sub(r'```$', '', result).strip()

            logger.info(f"✅ Reviewer: P{page_num} 审阅完成")
            return result

        except Exception as e:
            logger.warning(f"⚠️ Reviewer: P{page_num} 审阅失败，使用原 prompt: {e}")
            return visual_prompt

    def _get_system_prompt(self) -> str:
        return """你是一位资深视觉设计师兼 PPT 艺术总监。你的任务是对 visual prompt 进行严格审阅和改进。

## 你的 6 大审阅维度

### 1. 风格守门人
确保 prompt 忠于全局风格定义：
- 纸艺技法是否统一？（剪影、纸雕、层叠纸片，而不是写实插画、卡通）
- 色彩系统是否在调色板内？
- 字体系统是否统一（Caveat/Kalam/Patrick Hand）？
- 光照和质感是否统一（暖黄灯光、手工纸张）？

### 2. 内容翻译官
确保原文意图被准确翻译：
- TEXT TO RENDER 中的文字是否与原文完全一致？
- VISUAL SCENE 是否准确传达了 visual_suggestion 的创意？
- 关键细节是否被强调（如"句号 vs 逗号"的对比）？
- 情感核心是否被准确传达？

### 3. 技术质检员
确保 prompt 技术上可执行：
- 构图是否是 16:9 全屏？（不是独立的卡片、海报浮在中间）
- TEXT TO RENDER 和 VISUAL SCENE 是否有文字重复？
- 是否有矛盾的指令（如"不要有文字"但又要求渲染文字）？
- 描述是否过于复杂导致模型无法执行？

### 4. 叙事编辑
确保页面在整体叙事中连贯：
- 与前后页的视觉过渡是否自然？
- 这一页的情感基调是否与内容匹配？
- 章节间的视觉区分是否恰当？

### 5. 精简大师
确保 prompt 精简准确无冗余：
- 是否有重复的描述？
- 是否有模糊或歧义的表达？
- 是否用最少的字表达最准确的意思？

### 6. 情感共鸣者
确保视觉表达能打动人：
- 这一页的情感基调是否正确？
- 关键情节是否被视觉强化？
- 是否有画龙点睛的视觉细节？

## 你的工作方式

1. 仔细阅读输入的 visual prompt 和相关内容
2. 从上述 6 个维度逐一审阅
3. 识别问题并进行改进
4. 输出改进后的 prompt

## 输出格式

直接输出改进后的 visual prompt，不要有任何解释或评论。
输出必须是纯文本，不是 JSON 或 markdown。
TEXT TO RENDER 和 VISUAL SCENE 部分用【TEXT TO RENDER】和【VISUAL SCENE】标记分开。"""

    def _build_review_prompt(
        self,
        visual_prompt: str,
        headline: str,
        body: list,
        speaker_notes: str,
        style_config: dict,
        global_style: str,
        context: dict
    ) -> str:
        """构建审阅 prompt"""

        palette = style_config.get('palette', [])
        fonts = style_config.get('fonts', [])
        manifesto = style_config.get('manifesto', '')

        body_text = '\n'.join([f"- {b}" for b in body]) if body else "(无正文)"
        context_str = ""
        if context:
            prev = context.get('prev_prompt', '')
            next_p = context.get('next_prompt', '')
            if prev:
                context_str += f"\n\n【前页 visual prompt（参考）】\n{prev[:300]}..."
            if next_p:
                context_str += f"\n\n【后页 visual prompt（参考）】\n{next_p[:300]}..."

        prompt = f"""## 当前页的 content plan
标题: {headline}
正文:
{body_text}
演讲备注: {speaker_notes[:200] if speaker_notes else '(无)'}

## 当前页的 visual_suggestion（master plan 中的描述）
{context.get('visual_suggestion', '(无)') if context else '(无)'}

## 当前页的 visual prompt（初稿，需要审阅）
{visual_prompt}

## 全局风格定义（Design Manifesto）
{global_style[:500] if global_style else '(无)'}

## 风格配置
调色板: {', '.join(palette) if palette else '(未定义)'}
字体: {', '.join(fonts) if fonts else '(未定义)'}

## 你的审阅任务
请从 6 个维度审阅上述 visual prompt，识别问题并进行改进。
输出改进后的 visual prompt。{context_str}

## 重要提醒
- TEXT TO RENDER 中的文字必须与原文完全一致，不得删改
- VISUAL SCENE 中禁止引用 TEXT TO RENDER 的具体文字内容
- 构图必须是 16:9 全屏，不能是独立的卡片或海报
- 人物必须用纸艺技法（剪影、纸雕），不能用写实插画或卡通风格
- 保持精简，删除冗余描述
- 保留并强化关键的情感细节（如"句号 vs 逗号"的对比）

直接输出改进后的 visual prompt："""

        return prompt
