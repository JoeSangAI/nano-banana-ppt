"""
Visual Prompt 增强模块 - 问题3和问题7的改进
添加结构化约束和重复内容检测
"""

# 在 visual.py 中添加的全局约束模板
VISUAL_PROMPT_CONSTRAINTS = """
【页面布局规范 - 严格遵守】

### 绝对禁止
- 任何英文文字或字母
- 卡通人物、动漫角色
- 3D渲染效果
- 与内容无关的装饰元素

### 布局约束
- 标题区：顶部10-15%，居左或居中
- 内容区：中部60-70%
- 结论区：底部15-20%，结论文字必须最大最醒目

### 重复内容约束（问题7）
- 标题文字只出现在标题位置，不出现在画面装饰中
- 每个关键信息只允许在一个位置出现
- 禁止在画面中重复核心信息（最多出现1次）

### 数据展示规范
- 数字超过3个时用卡片/列表，不用柱状图对比
- 避免排名展示（抖音>视频号>快手）
- 强调用红色，背景/次要用灰色
"""

def enhance_visual_prompt_with_constraints(original_prompt: str, page_type: str, style_config: dict) -> str:
    """
    为 visual prompt 添加结构化约束
    解决问题3（描述不精确）和问题7（重复内容）
    """
    # 提取用户指定的禁止元素
    forbidden = style_config.get('forbidden', [])
    if forbidden:
        forbidden_text = "\n".join([f"- {item}" for item in forbidden])
        constraints = VISUAL_PROMPT_CONSTRAINTS.replace(
            "### 绝对禁止\n- 任何英文文字或字母",
            f"### 绝对禁止\n{forbidden_text}"
        )
    else:
        constraints = VISUAL_PROMPT_CONSTRAINTS

    # 组合原始 prompt 和约束
    enhanced_prompt = f"""{original_prompt}

{constraints}

【重要提醒】
以上约束必须严格遵守，任何违反都会导致生成失败。
"""

    return enhanced_prompt
