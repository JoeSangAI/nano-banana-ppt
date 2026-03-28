"""
全局风格一致性模块 - 问题6的改进
确保种子页风格传给所有页面类型
"""

# 在 executor.py 中修改种子页生成逻辑

def generate_seed_slides_with_global_style(plan, slides_dir, generator, resolution, visual_plan):
    """
    生成种子页，并确保风格全局一致

    改进点：
    1. 首先生成一个"全局风格样例页"
    2. 所有后续页面（包括不同类型）都引用这个样例页
    3. 在 visual_prompt 中强制添加全局风格约束
    """

    # 提取全局风格配置
    style_config = visual_plan.get('style_config', {})

    # 构建全局风格约束文本
    global_style_constraint = f"""
【全局风格约束 - 所有页面必须遵守】
- 配色方案: 主色={style_config.get('primary_color', '#FFFFFF')}, 辅色={style_config.get('secondary_color', '#000000')}, 强调色={style_config.get('accent_color', '#CC0000')}
- 装饰元素位置: {style_config.get('decoration_bar', 'top')}
- 标题位置: {style_config.get('title_position', 'top-left')}
- 禁止元素: {', '.join(style_config.get('forbidden', ['英文文字', '卡通人物', '3D效果']))}

【重要】无论页面类型（封面/章节/内容），都必须使用相同的风格规范。
"""

    # 为所有页面的 visual_prompt 添加全局约束
    for slide in plan:
        if 'visual_prompt' in slide:
            slide['visual_prompt'] = slide['visual_prompt'] + "\n\n" + global_style_constraint

    # 生成种子页（封面、第一个章节页、第一个内容页）
    seed_slides = {}
    for page_type in ['cover', 'section', 'content']:
        for slide in plan:
            if slide.get('type') == page_type:
                # 生成这一页
                page_num, image = _generate_single_slide(
                    slide, visual_plan, slides_dir, generator, resolution, {}, None
                )
                seed_slides[page_type] = image
                print(f"✅ 生成种子页: {page_type} (P{page_num})")
                break

    return seed_slides


# 在生成后续页面时，将种子页作为 reference_images 传入
def generate_remaining_slides_with_seed_reference(plan, slides_dir, generator, resolution, visual_plan, seed_slides):
    """
    生成剩余页面，所有页面都引用种子页的风格
    """
    for slide in plan:
        page_type = slide.get('type', 'content')

        # 根据页面类型选择对应的种子页作为参考
        if page_type in seed_slides:
            slide['reference_images'] = [seed_slides[page_type]]
        elif 'content' in seed_slides:
            # 如果没有对应类型的种子页，使用 content 类型作为默认参考
            slide['reference_images'] = [seed_slides['content']]

        # 生成页面
        _generate_single_slide(slide, visual_plan, slides_dir, generator, resolution, seed_slides, None)
