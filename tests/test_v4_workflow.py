"""
集成测试：v4 工作流端到端测试

测试完整的 PM intake -> Content -> Visual -> Execute 流程
"""

import os
import json
import tempfile
import shutil
from pathlib import Path
import pytest


class TestV4Workflow:
    """v4 架构端到端集成测试"""

    @pytest.fixture
    def temp_project_dir(self):
        """创建临时项目目录"""
        temp_dir = tempfile.mkdtemp()
        yield temp_dir
        shutil.rmtree(temp_dir, ignore_errors=True)

    @pytest.fixture
    def mock_client(self):
        """模拟 OpenAI 客户端"""
        class MockResponse:
            def __init__(self, content):
                self.choices = [type('obj', (object,), {
                    'message': type('obj', (object,), {'content': content})()
                })()]

        class MockClient:
            def __init__(self):
                self.chat = type('obj', (object,), {
                    'completions': type('obj', (object,), {
                        'create': self.create_completion
                    })()
                })()

            def create_completion(self, **kwargs):
                # 返回模拟的 JSON 响应
                if "input_type" in kwargs.get('messages', [{}])[0].get('content', ''):
                    return MockResponse(json.dumps({
                        "input_type": "topic",
                        "goal": "测试 PPT 生成",
                        "audience": "开发者",
                        "tone": "专业",
                        "constraints": ["控制在 10 页以内"],
                        "image_anchors": []
                    }))
                elif "image_type" in kwargs.get('messages', [{}])[0].get('content', ''):
                    return MockResponse(json.dumps({
                        "image_type": "screenshot",
                        "description": "测试图片",
                        "recommended_mode": "ELEMENT_PRESERVE",
                        "reason": "测试原因"
                    }))
                elif "modification_type" in kwargs.get('messages', [{}])[0].get('content', ''):
                    return MockResponse(json.dumps({
                        "modification_type": "content",
                        "rollback_to_gate": "Content",
                        "can_modify_single_page": False,
                        "reason": "测试原因",
                        "suggestions": ["建议1"]
                    }))
                return MockResponse("测试响应")

        return MockClient()

    def test_pm_agent_initialization(self, temp_project_dir, mock_client):
        """测试 PM Agent 初始化"""
        from tools.nano_banana_ppt.agents.pm import PMAgent

        pm_agent = PMAgent(mock_client, project_dir=temp_project_dir)

        assert pm_agent.project_dir == Path(temp_project_dir)
        assert pm_agent.image_assets_manager is not None

    def test_pm_intake_text_only(self, temp_project_dir, mock_client):
        """测试 PM intake 处理纯文本输入"""
        from tools.nano_banana_ppt.agents.pm import PMAgent

        pm_agent = PMAgent(mock_client, project_dir=temp_project_dir)

        user_input = {
            "text": "生成一个关于 AI 的 PPT",
            "images": [],
            "urls": [],
            "template_pptx": None
        }

        result = pm_agent.intake(user_input)

        assert result["status"] == "success"
        assert result["next_gate"] in ["Content", "Visual", "Execute"]

    def test_image_assets_manager(self, temp_project_dir, mock_client):
        """测试图片资产管理器"""
        from tools.nano_banana_ppt.utils.image_assets import ImageAssetsManager, ImageAsset, ImageMode

        manager = ImageAssetsManager(
            str(Path(temp_project_dir) / "image_assets.json"),
            client=mock_client
        )

        # 添加图片资产
        asset = ImageAsset(
            path="test.png",
            mode=ImageMode.INTENT_FUSION,
            semantic_anchor="测试锚点"
        )
        manager.add_asset(asset)

        # 保存
        manager.save_to_json()

        # 检查文件是否创建
        json_path = Path(temp_project_dir) / "image_assets.json"
        assert json_path.exists()

        # 加载并验证
        manager2 = ImageAssetsManager(str(json_path), client=mock_client)
        manager2.load_from_json()
        assert len(manager2.assets) == 1
        assert manager2.assets[0].path == "test.png"

    def test_image_assets_manager(self, temp_project_dir, mock_client):
        """测试文档规范化：content_plan"""
        from tools.nano_banana_ppt.utils.doc_normalizer import normalize_content_plan

        content = """# 第一页
这是内容

[IMAGE:测试锚点]

## 第二页
更多内容
"""

        normalized, issues = normalize_content_plan(content)

        assert normalized is not None
        assert isinstance(issues, list)

    def test_doc_normalizer_visual_plan(self):
        """测试文档规范化：visual_plan"""
        from tools.nano_banana_ppt.utils.doc_normalizer import normalize_visual_plan

        content = """# 第一页

```image
path: test.png
mode: INTENT_FUSION
role: 测试
position: center
```

## 第二页

```image
path: test2.png
mode: ELEMENT_PRESERVE
```
"""

        normalized, issues = normalize_visual_plan(content)

        assert normalized is not None
        assert isinstance(issues, list)

    def test_resource_check(self, temp_project_dir):
        """测试资源完整性检查"""
        from tools.nano_banana_ppt.utils.resource_check import check_resources

        # 创建测试文件
        content_plan_json = Path(temp_project_dir) / "content_plan.json"
        content_plan_json.write_text(json.dumps({
            "slides": [
                {"slide_number": 1, "title": "测试页"}
            ]
        }))

        visual_plan_json = Path(temp_project_dir) / "visual_plan.json"
        visual_plan_json.write_text(json.dumps({
            "pages": [
                {
                    "page_number": 1,
                    "title": "测试页",
                    "images": [
                        {
                            "path": "test.png",
                            "mode": "INTENT_FUSION",
                            "final_visual_prompt": "测试 prompt"
                        }
                    ]
                }
            ]
        }))

        report = check_resources(
            output_dir=temp_project_dir,
            check_images=False,  # 不检查图片文件是否存在
            check_placeholders=True,
            check_fields=True,
            check_consistency=True
        )

        assert report is not None
        assert hasattr(report, 'passed')
        assert hasattr(report, 'issues')

    def test_pm_determine_gate(self, temp_project_dir, mock_client):
        """测试 PM Agent 判断当前 Gate"""
        from tools.nano_banana_ppt.agents.pm import PMAgent

        pm_agent = PMAgent(mock_client, project_dir=temp_project_dir)

        # 初始状态：应该进入 Content Gate
        gate = pm_agent.determine_gate()
        assert gate == "Content"

        # 创建 content_plan
        content_plan_path = Path(temp_project_dir) / "content_plan.md"
        content_plan_path.write_text("# 测试内容")

        # 应该进入 Visual Gate
        gate = pm_agent.determine_gate()
        assert gate == "Visual"

        # 创建 visual_plan
        visual_plan_path = Path(temp_project_dir) / "visual_plan.md"
        visual_plan_path.write_text("# 测试视觉")

        # 应该进入 Execute Gate
        gate = pm_agent.determine_gate()
        assert gate == "Execute"

    def test_pm_analyze_modification(self, temp_project_dir, mock_client):
        """测试 PM Agent 分析修改请求"""
        from tools.nano_banana_ppt.agents.pm import PMAgent

        pm_agent = PMAgent(mock_client, project_dir=temp_project_dir)

        result = pm_agent.analyze_modification(
            modification_request="修改第 3 页的标题",
            target_pages=[3]
        )

        assert result is not None
        assert "modification_type" in result
        assert "rollback_to_gate" in result
        assert "can_modify_single_page" in result

    def test_compile_content_plan(self, temp_project_dir):
        """测试 content_plan 编译"""
        from tools.nano_banana_ppt.utils.compile_content_plan import compile_content_plan

        content_md = """# 第一页标题

这是第一页的内容。

[IMAGE: 封面图]

## 第二页标题

这是第二页的内容。
"""

        content_md_path = Path(temp_project_dir) / "content_plan.md"
        content_md_path.write_text(content_md)

        output_json_path = Path(temp_project_dir) / "content_plan.json"

        compile_content_plan(str(content_md_path), str(output_json_path))

        assert output_json_path.exists()

        with open(output_json_path, 'r') as f:
            data = json.load(f)

        assert "slides" in data
        assert len(data["slides"]) >= 2

    def test_compile_visual_plan(self, temp_project_dir):
        """测试 visual_plan 编译"""
        from tools.nano_banana_ppt.utils.compile_visual_plan import compile_visual_plan

        visual_md = """## 第 1 页 · 封面

```image
path: test.png
mode: INTENT_FUSION
role: 封面图
position: full
```

## 第 2 页 · 内容

```image
path: test2.png
mode: ELEMENT_PRESERVE
role: 内容图
position: center
```
"""

        visual_md_path = Path(temp_project_dir) / "visual_plan.md"
        visual_md_path.write_text(visual_md)

        # 创建对应的 content_plan.json
        content_json_path = Path(temp_project_dir) / "content_plan.json"
        content_json_path.write_text(json.dumps({
            "slides": [
                {"slide_number": 1, "title": "第一页", "content": "内容1"},
                {"slide_number": 2, "title": "第二页", "content": "内容2"}
            ]
        }))

        output_json_path = Path(temp_project_dir) / "visual_plan.json"

        compile_visual_plan(
            str(visual_md_path),
            str(output_json_path)
        )

        assert output_json_path.exists()

        with open(output_json_path, 'r') as f:
            data = json.load(f)

        assert "pages" in data
        assert len(data["pages"]) >= 2

    def test_visual_agent_review_visual_prompt_signature(self, monkeypatch):
        """测试 VisualAgent.review_visual_prompt 可用 3 个参数直接调用。"""
        from tools.nano_banana_ppt.agents.visual import VisualAgent

        class MockResponse:
            def __init__(self, content):
                self.choices = [type('obj', (object,), {
                    'message': type('obj', (object,), {'content': content})()
                })()]

        monkeypatch.setattr(
            "tools.nano_banana_ppt.agents.visual.chat_completion_with_fallback",
            lambda *args, **kwargs: MockResponse("改进后的 prompt")
        )

        agent = VisualAgent(api_key="test-key")
        result = agent.review_visual_prompt(
            visual_prompt="原始 prompt",
            visual_suggestion="请做一个极简封面",
            text_content={"headline": "封面标题", "body": ["一句话说明"]},
        )

        assert result == "改进后的 prompt"

    def test_visual_agent_generate_visual_plan_builds_v3_prompt(self, monkeypatch):
        """测试 VisualAgent 生成的新执行 prompt 结构完整。"""
        from tools.nano_banana_ppt.agents.visual import VisualAgent

        class MockResponse:
            def __init__(self, content):
                self.choices = [type('obj', (object,), {
                    'message': type('obj', (object,), {'content': content})()
                })()]

        monkeypatch.setattr(
            VisualAgent,
            "generate_chapter_visual_themes",
            lambda self, narrative_outline, style_config: {"global_consistency": {}, "chapters": []}
        )
        monkeypatch.setattr(
            VisualAgent,
            "analyze_content_depth",
            lambda self, narrative_outline: {"overall_theme": "测试", "stories": []}
        )
        monkeypatch.setattr(
            VisualAgent,
            "review_visual_prompt",
            lambda self, visual_prompt, visual_suggestion, text_content: visual_prompt
        )
        monkeypatch.setattr(
            "tools.nano_banana_ppt.agents.visual.chat_completion_with_fallback",
            lambda *args, **kwargs: MockResponse("blank template prompt")
        )

        agent = VisualAgent(api_key="test-key")
        slides = agent.generate_visual_plan(
            narrative_outline=[{
                "page_num": 1,
                "type": "content",
                "text_content": {
                    "headline": "封面标题",
                    "subhead": "一句副标题",
                    "body": ["第一条内容", "第二条内容"]
                },
                "visual_description": "左侧干净文字区，右侧是一盏台灯照亮书桌，整体克制温暖。"
            }],
            style_definition_tuple=(
                "Warm editorial presentation",
                {
                    "description": "Warm editorial presentation",
                    "palette": ["#FFF8EF", "#3A2F2A", "#C97B63"],
                    "fonts": ["Noto Sans CJK SC", "Noto Serif CJK SC"]
                }
            ),
            assets={},
            template_info=None
        )

        prompt = slides[0]["final_visual_prompt"]
        assert "【LANGUAGE RULE】" in prompt
        assert "【TEXT TO RENDER】" in prompt
        assert "【STYLE SYSTEM】" in prompt
        assert "【SEED / REFERENCE CONTROL】" in prompt
        assert "【VISUAL SCENE】" in prompt
        assert "【FINAL INSTRUCTION】" in prompt
        assert "封面标题" in prompt
        assert "第一条内容" in prompt

    def test_visual_agent_in_scene_text_requires_explicit_marker(self):
        """测试只有显式 marker 才会被视为场景内必渲染文字。"""
        from tools.nano_banana_ppt.agents.visual import VisualAgent

        agent = VisualAgent(api_key="test-key")

        cleaned, in_scene_text = agent._parse_in_scene_text(
            "用类似‘停、看、听’这样的路牌意象，但不要真的出现文字。"
        )
        assert cleaned == "用类似‘停、看、听’这样的路牌意象，但不要真的出现文字。"
        assert in_scene_text == ""

        cleaned_marked, marked_text = agent._parse_in_scene_text(
            "左侧是安静的走廊。\n【场景内文字】\n- 停、看、听\n- Focus on What Matters\n右侧留给正文。"
        )
        assert "【场景内文字】" not in cleaned_marked
        assert marked_text == "停、看、听\nFocus on What Matters"
        assert "右侧留给正文。" in cleaned_marked

    def test_visual_agent_build_execution_prompt_uses_explicit_in_scene_text_only(self):
        """测试执行 prompt 只注入显式声明的场景内文字，不误收集引号内容。"""
        from tools.nano_banana_ppt.agents.visual import VisualAgent

        agent = VisualAgent(api_key="test-key")
        prompt = agent._build_execution_prompt(
            page={"page_num": 1, "one_takeaway": "测试要点"},
            page_type="CONTENT",
            text_content={"headline": "标题", "body": ["正文"]},
            visual_suggestion=(
                "参考乔布斯发布会舞台的气场，不要真的把'Think Different'打在画面里。\n"
                "【场景内文字】\n- 仅此一句"
            ),
            style_definition="Modern editorial",
            style_config={"palette": ["#111111", "#F5F5F5"], "fonts": ["FontA", "FontB"]},
            reference_image_path=None,
            native_images=[],
            seed_family="content",
            seed_role="family_seed",
            chapter_theme_hint="",
        )

        assert "仅此一句" in prompt
        assert "Think Different" in prompt  # visual scene description still mentions the negated example
        assert "Required in-scene text, if any:\n仅此一句" in prompt

    def test_visual_agent_prompt_mode_changes_content_slide_prompt(self, monkeypatch):
        """测试 prompt_mode 会影响普通内容页的执行 prompt，而不仅是模板页。"""
        from tools.nano_banana_ppt.agents.visual import VisualAgent

        class MockResponse:
            def __init__(self, content):
                self.choices = [type('obj', (object,), {
                    'message': type('obj', (object,), {'content': content})()
                })()]

        monkeypatch.setattr(
            VisualAgent,
            "generate_chapter_visual_themes",
            lambda self, narrative_outline, style_config: {"global_consistency": {}, "chapters": []}
        )
        monkeypatch.setattr(
            VisualAgent,
            "analyze_content_depth",
            lambda self, narrative_outline: {"overall_theme": "测试", "stories": []}
        )
        monkeypatch.setattr(
            VisualAgent,
            "review_visual_prompt",
            lambda self, visual_prompt, visual_suggestion, text_content: visual_prompt
        )
        monkeypatch.setattr(
            "tools.nano_banana_ppt.agents.visual.chat_completion_with_fallback",
            lambda *args, **kwargs: MockResponse("blank template prompt")
        )

        narrative_outline = [{
            "page_num": 1,
            "type": "content",
            "text_content": {
                "headline": "封面标题",
                "subhead": "一句副标题",
                "body": ["第一条内容", "第二条内容"]
            },
            "visual_description": "左侧干净文字区，右侧是一盏台灯照亮书桌，整体克制温暖。"
        }]
        style_definition_tuple = (
            "Warm editorial presentation",
            {
                "description": "Warm editorial presentation",
                "palette": ["#FFF8EF", "#3A2F2A", "#C97B63"],
                "fonts": ["Noto Sans CJK SC", "Noto Serif CJK SC"],
                "accent_usage": "Only use accent on key metrics.",
                "manifesto": "Use restrained contrast. Avoid default AI metaphors."
            }
        )

        minimal_prompt = VisualAgent(api_key="test-key", prompt_mode="minimal").generate_visual_plan(
            narrative_outline=narrative_outline,
            style_definition_tuple=style_definition_tuple,
            assets={},
            template_info=None
        )[0]["final_visual_prompt"]
        verbose_prompt = VisualAgent(api_key="test-key", prompt_mode="verbose").generate_visual_plan(
            narrative_outline=narrative_outline,
            style_definition_tuple=style_definition_tuple,
            assets={},
            template_info=None
        )[0]["final_visual_prompt"]

        assert minimal_prompt != verbose_prompt
        assert len(minimal_prompt) < len(verbose_prompt)
        assert "Art Director manifesto" not in minimal_prompt
        assert "Art Director manifesto" in verbose_prompt

    def test_generate_single_slide_uses_seed_reference_for_follow_up(self, temp_project_dir):
        """测试 follow-up 页会把 seed 母版作为视觉语法参考图送入执行层。"""
        from PIL import Image
        from tools.nano_banana_ppt.core.executor import _generate_single_slide

        class FakeGenerator:
            def __init__(self):
                self.captured_prompt = None
                self.captured_reference_images = None

            def generate_image(self, description, aspect_ratio="16:9", reference_images=None,
                               is_background_only=False, resolution="1K", native_images=None):
                self.captured_prompt = description
                self.captured_reference_images = reference_images or []
                return Image.new("RGB", (64, 64), color="white")

        generator = FakeGenerator()
        slides_dir = Path(temp_project_dir) / "slides"
        slides_dir.mkdir(parents=True, exist_ok=True)

        slide = {
            "page_num": 2,
            "type": "content",
            "seed_role": "follow_up",
            "final_visual_prompt": "Base prompt"
        }
        masters = {
            "content": Image.new("RGB", (32, 32), color="gray"),
            "section": None,
            "hero": None
        }

        page_num, image = _generate_single_slide(
            slide=slide,
            visual_plan=[slide],
            slides_dir=slides_dir,
            generator=generator,
            resolution="1K",
            masters=masters,
            clean_background_image=None,
            project_dir=temp_project_dir
        )

        assert page_num == 2
        assert image.size == (64, 64)
        assert generator.captured_reference_images is not None
        assert len(generator.captured_reference_images) == 1
        assert "VISUAL GRAMMAR reference" in generator.captured_prompt

    def test_sync_content_plan_uses_review_markdown_format(self, temp_project_dir):
        """测试 content_plan.json 同步回当前 content_plan.md 审阅格式。"""
        from tools.nano_banana_ppt.utils.plan_sync import sync_content_plan

        json_path = Path(temp_project_dir) / "content_plan.json"
        json_path.write_text(json.dumps({
            "slides": [
                {
                    "slide_number": 1,
                    "type": "cover",
                    "title": "测试封面",
                    "content": "第一行内容\n第二行内容",
                    "speaker_notes": "开场介绍"
                }
            ]
        }, ensure_ascii=False), encoding="utf-8")

        md_path = Path(temp_project_dir) / "content_plan.md"
        md_path.write_text(
            "# PPT 内容计划 · 待您确认\n\n## 一、内容源信息\n\n- **内容源**：demo.md\n",
            encoding="utf-8"
        )

        result = sync_content_plan(str(json_path), str(md_path), record_history=False)
        output = md_path.read_text(encoding="utf-8")

        assert result["success"] is True
        assert "# PPT 内容计划 · 待您确认" in output
        assert "### 第 1 页 · 封面" in output
        assert "- **标题**：测试封面" in output
        assert "- **正文形态**：bullets" in output
        assert "开场介绍" in output

    def test_sync_visual_plan_uses_review_markdown_format(self, temp_project_dir):
        """测试 visual_plan.json 同步回当前 visual_plan.md 审阅格式。"""
        from tools.nano_banana_ppt.utils.plan_sync import sync_visual_plan

        json_path = Path(temp_project_dir) / "visual_plan.json"
        json_path.write_text(json.dumps({
            "meta": {"content_file": "demo.md"},
            "style": {
                "palette": ["#111111", "#EEEEEE"],
                "fonts": ["PingFang SC"],
                "description": "极简、克制、留白"
            },
            "manifesto": "保持留白，避免廉价装饰。",
            "slides": [
                {
                    "page_num": 1,
                    "type": "cover",
                    "text_content": {
                        "headline": "封面标题",
                        "body": ["一句话副文案"]
                    },
                    "visual_description": "深色背景配一束聚光，文字居中。",
                    "final_visual_prompt": "【TEXT TO RENDER】\nHeadline: 封面标题\n\n【VISUAL SCENE】\n深色背景配一束聚光，文字居中。",
                    "speaker_notes": "先讲问题，再讲方法。",
                    "seed_role": "family_seed",
                    "seed_usage_rule": "种子页：负责定义这一类页面的风格、排版语言和视觉语法，供后续同类页面继承。",
                    "native_images": [
                        {
                            "path": "image.png",
                            "semantic_role": "主视觉",
                            "mode": "INTENT_FUSION",
                            "bounding_box": {
                                "left": 0.0,
                                "top": 0.0,
                                "width": 1.0,
                                "height": 1.0
                            }
                        }
                    ]
                }
            ]
        }, ensure_ascii=False), encoding="utf-8")

        md_path = Path(temp_project_dir) / "visual_plan.md"
        result = sync_visual_plan(str(json_path), str(md_path), record_history=False)
        output = md_path.read_text(encoding="utf-8")

        assert result["success"] is True
        assert "# PPT 视觉计划 · 待您确认" in output
        assert "- **标题**：封面标题" in output
        assert "- **配图/画面**：深色背景配一束聚光，文字居中。" in output
        assert "- **种子页使用说明**：种子页：负责定义这一类页面的风格、排版语言和视觉语法，供后续同类页面继承。" in output
        assert "- **最终执行提示词**：" not in output
        assert "【TEXT TO RENDER】" not in output
        assert "[INTENT_FUSION] 主视觉" in output
        assert not (Path(temp_project_dir) / "master_plan.md").exists()

    def test_derive_technical_plan_reuses_existing_prompt_when_md_omits_prompt(self):
        """测试 visual_plan.md 未暴露 prompt 时，仍优先复用旧 JSON 中的 final_visual_prompt。"""
        from tools.nano_banana_ppt.utils.review_plan import derive_technical_plan

        parsed = {
            "meta": {"content_file": "demo.md"},
            "style": {"description": "极简风", "palette": ["#111111", "#EEEEEE"]},
            "pages": [
                {
                    "page_num": 1,
                    "type": "cover",
                    "text_content": {"headline": "封面标题", "body": ["一句话副文案"]},
                    "visual_description": "深色背景配一束聚光，文字居中。",
                    "speaker_notes": "先讲问题，再讲方法。",
                }
            ],
            "manifesto": "保持留白，避免廉价装饰。",
        }
        existing_plan = {
            "slides": [
                {
                    "page_num": 1,
                    "type": "cover",
                    "text_content": {"headline": "封面标题", "body": ["一句话副文案"]},
                    "visual_description": "深色背景配一束聚光，文字居中。",
                    "final_visual_prompt": "缓存下来的执行提示词",
                    "speaker_notes": "先讲问题，再讲方法。",
                }
            ]
        }

        result = derive_technical_plan(
            parsed=parsed,
            project_dir="/tmp/demo-project",
            content_file="demo.md",
            api_key="test-key",
            api_base=None,
            existing_plan=existing_plan,
        )

        assert result["slides"][0]["final_visual_prompt"] == "缓存下来的执行提示词"
        assert result["pages"][0]["final_visual_prompt"] == "缓存下来的执行提示词"

    def test_derive_technical_plan_regenerates_prompt_when_visual_description_changes(self, monkeypatch):
        """测试 visual_description 变化且 MD 未带 prompt 时，会重新生成 final_visual_prompt。"""
        from tools.nano_banana_ppt.utils.review_plan import derive_technical_plan

        class FakeVisualAgent:
            last_init = None

            def __init__(self, api_key, api_base=None, prompt_mode="verbose"):
                self.api_key = api_key
                self.api_base = api_base
                self.prompt_mode = prompt_mode
                FakeVisualAgent.last_init = {
                    "api_key": api_key,
                    "api_base": api_base,
                    "prompt_mode": prompt_mode,
                }

            def generate_visual_plan(self, narrative_outline, style_definition_tuple, assets, template_info):
                return [
                    {
                        "page_num": 1,
                        "type": "cover",
                        "visual_description": "新的视觉描述",
                        "final_visual_prompt": "新生成的执行提示词",
                        "visual_prompt": "新生成的执行提示词",
                    }
                ]

        monkeypatch.setattr("tools.nano_banana_ppt.agents.visual.VisualAgent", FakeVisualAgent)
        monkeypatch.setenv("PROMPT_MODE", "minimal")

        parsed = {
            "meta": {"content_file": "demo.md"},
            "style": {"description": "极简风", "palette": ["#111111", "#EEEEEE"]},
            "pages": [
                {
                    "page_num": 1,
                    "type": "cover",
                    "text_content": {"headline": "封面标题", "body": ["一句话副文案"]},
                    "visual_description": "新的视觉描述",
                }
            ],
            "manifesto": "保持留白，避免廉价装饰。",
        }
        existing_plan = {
            "slides": [
                {
                    "page_num": 1,
                    "type": "cover",
                    "text_content": {"headline": "封面标题", "body": ["一句话副文案"]},
                    "visual_description": "旧的视觉描述",
                    "final_visual_prompt": "旧提示词",
                }
            ]
        }

        result = derive_technical_plan(
            parsed=parsed,
            project_dir="/tmp/demo-project",
            content_file="demo.md",
            api_key="test-key",
            api_base=None,
            existing_plan=existing_plan,
        )

        assert result["slides"][0]["final_visual_prompt"] == "新生成的执行提示词"
        assert result["pages"][0]["final_visual_prompt"] == "新生成的执行提示词"
        assert FakeVisualAgent.last_init["prompt_mode"] == "minimal"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
