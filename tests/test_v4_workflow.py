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
        assert pm_agent.brief_manager is not None
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

        # 检查 brief.md 是否创建
        brief_path = Path(temp_project_dir) / "brief.md"
        assert brief_path.exists()

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

    def test_brief_manager(self, temp_project_dir):
        """测试 Brief 管理器"""
        from tools.nano_banana_ppt.utils.brief_manager import BriefManager, Brief

        brief_path = str(Path(temp_project_dir) / "brief.md")
        manager = BriefManager(brief_path)

        # 创建 Brief
        brief = Brief(
            goal="测试目标",
            audience="测试受众",
            style_preference="专业",
            constraints=["约束1", "约束2"],
            image_requirements=[{"anchor": "测试", "description": "描述"}]
        )

        manager.save(brief)

        # 检查文件是否创建
        assert Path(brief_path).exists()

        # 加载并验证
        loaded_brief = manager.load()
        assert loaded_brief.goal == "测试目标"
        assert loaded_brief.audience == "测试受众"
        assert len(loaded_brief.constraints) == 2

    def test_doc_normalizer_content_plan(self):
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
                            "visual_prompt": "测试 prompt"
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
        from tools.nano_banana_ppt.utils.brief_manager import Brief

        pm_agent = PMAgent(mock_client, project_dir=temp_project_dir)

        # 初始状态：应该进入 Content Gate
        gate = pm_agent.determine_gate()
        assert gate == "Content"

        # 创建 brief 和 content_plan
        brief = Brief(goal="测试")
        pm_agent.brief_manager.save(brief)

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


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
