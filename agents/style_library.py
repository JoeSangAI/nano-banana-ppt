"""
Curated Style Library for Nano Banana PPT

This module contains predefined, high-quality visual style definitions.
Organized by content scenario categories (from notebooklm-slide-prompt-coach).
Each style includes scene context + visual language for intelligent recommendations.

Category structure:
1. 内容讲解型 (Content / Educational)
2. 结构与技术型 (Structure & Technical)
3. 商务与高端型 (Business & Premium)
4. 人物与亲和型 (Human & Approachable)
5. 编辑、杂志与潮流型 (Editorial, Magazine & Street)
6. 流行、娱乐与高冲击型 (Pop, Youth & High-energy)
7. Artistic & Avant-garde
"""

STYLE_LIBRARY = {

    # ═══════════════════════════════════════════════════════════
    # 1. 内容讲解型 (Content / Educational)
    # ═══════════════════════════════════════════════════════════

    "blackboard": {
        "category": "内容讲解型",
        "aliases": ["blackboard", "黑板风", "粉笔风", "课堂风", "教学风", "培训风"],
        "description": "黑板讲解风格。适合培训、教学、逐步解释、概念入门场景。深色黑板/绿板背景搭配粉笔质感的手写文字和简单图形，传递课堂感和推导过程。",
        "palette": ["#1B3D2F", "#2E5D4B", "#FFFFFF", "#E8E4D9", "#F5F5DC"],
        "fonts": ["Marker Felt", "Comic Sans MS", "Handwritten"],
        "shape_language": "手绘线条、有机轮廓、不规则涂鸦感、箭头和简单图形",
        "imagery_style": "粉笔纹理、手绘图示、课堂场景、公式推导",
        "accent_usage": "白色粉笔字用于标题和重点，浅绿/浅黄用于强调线条和箭头。整体保持粉笔的哑光质感。",
        "best_for": ["培训课件", "教学演示", "概念入门", "逐步推导", "新人 onboarding"],
        "avoid": ["高端品牌汇报", "强烈商务气场", "高管战略沟通"]
    },

    "whiteboard": {
        "category": "内容讲解型",
        "aliases": ["whiteboard", "白板风", "马克笔风", "清爽风", "协作风"],
        "description": "白板整理风格。适合内部分享、头脑风暴、工作坊总结场景。白底背景搭配马克笔色块和彩色图形，传递即时记录感和清爽协作氛围。",
        "palette": ["#FFFFFF", "#FFFFFF", "#2C3E50", "#E74C3C", "#3498DB", "#F39C12"],
        "fonts": ["Segoe UI", "Arial", "Helvetica"],
        "shape_language": "方框+圆角、马克笔质感色块、箭头连接、网格辅助线",
        "imagery_style": "马克笔质感、平板手绘、即时贴、思维导图结构",
        "accent_usage": "红蓝绿马克笔色块用于分类和标注，黑色用于主标题。保持马克笔的饱和度和明快感。",
        "best_for": ["内部分享", "头脑风暴", "工作坊总结", "团队讨论", "快速迭代沟通"],
        "avoid": ["正式高层汇报", "对外商务提案", "数据密集型报告"]
    },

    "sketch_note": {
        "category": "内容讲解型",
        "aliases": ["sketch_note", "sketchnote", "手绘笔记风", "涂鸦风", "现场感"],
        "description": "可视化笔记风格。适合会议纪要、工作坊、组织文化、以人为中心的内容场景。白底搭配手绘图标和箭头连接，传递亲和力和现场感。",
        "palette": ["#FFFEF5", "#2D3436", "#636E72", "#E17055", "#00B894", "#6C5CE7"],
        "fonts": ["Caveat", "Kalam", "Patrick Hand", " handwritten"],
        "shape_language": "手绘线条、图标驱动、箭头和连接线、圆形和方形混合",
        "imagery_style": "手绘图标、人像简化图形、亲和插画、纸面纹理",
        "accent_usage": "暖色调（橙/绿/紫）用于图标和标注，灰色用于辅助线条。保持手绘的随意感和亲和力。",
        "best_for": ["会议纪要", "工作坊记录", "组织文化", "以人为本的内容", "团队故事"],
        "avoid": ["需要权威感的数据汇报", "高管战略", "技术架构展示"]
    },

    # ═══════════════════════════════════════════════════════════
    # 2. 结构与技术型 (Structure & Technical)
    # ═══════════════════════════════════════════════════════════

    "blueprint": {
        "category": "结构与技术型",
        "aliases": ["blueprint", "蓝图风", "工程风", "制图风", "深蓝工程风"],
        "description": "蓝图工程风格。适合架构图、工程改造、系统规划、制造业说明场景。深蓝色背景搭配白色/浅蓝精细线稿和网格，传递专业制图感和结构秩序。",
        "palette": ["#0A1929", "#132F4C", "#FFFFFF", "#B4D4E7", "#4FC3F7"],
        "fonts": ["Consolas", "Monaco", "Courier New", "monospace"],
        "shape_language": "精确网格、水平垂直线段、虚线辅助、标准化符号",
        "imagery_style": "工程制图、线稿为主、平面投影、网格背景",
        "accent_usage": "亮蓝/青色用于高亮重点区域，白色用于主要结构线。保持制图的精密感和冷静专业。",
        "best_for": ["架构图", "工程改造", "系统规划", "制造业说明", "技术方案展示"],
        "avoid": ["需要亲和感的人文内容", "情感叙事", "轻松活泼场景"]
    },

    "exploded_view": {
        "category": "结构与技术型",
        "aliases": ["exploded_view", "爆炸图", "拆解风", "分层风", "产品拆解"],
        "description": "拆解结构风格。适合产品结构、模块关系、系统组成、「这个东西怎么工作」的解释场景。将整体拆解为独立模块，清晰展示连接关系和层次结构。",
        "palette": ["#1A1A2E", "#16213E", "#E94560", "#0F3460", "#FFFFFF"],
        "fonts": ["Roboto Mono", "Space Mono", "monospace"],
        "shape_language": "爆炸分散布局、同心圆层次、连接线标注、分区框架",
        "imagery_style": "爆炸图示意、模块分离、编号标注、平面化渲染",
        "accent_usage": "红色/橙色用于高亮核心组件，青色用于连接关系线条。保持专业的技术说明感。",
        "best_for": ["产品拆解", "模块关系", "系统组成", "技术培训", "工作原理说明"],
        "avoid": ["纯概念叙事", "战略愿景", "情感故事", "品牌展示"]
    },

    "minimal_data": {
        "category": "结构与技术型",
        "aliases": ["minimal_data", "极简数据风", "扁平图表风", "数据可视化", "克制数据"],
        "description": "极简数据风格。适合统计汇报、市场分析、关键指标说明场景。扁平化图表配合极简配色和克制用色，让数据本身说话，不可辩驳。",
        "palette": ["#FFFFFF", "#F8F9FA", "#2D3436", "#0984E3", "#00B894", "#E17055"],
        "fonts": ["Inter", "Helvetica Neue", "Arial", "sans-serif"],
        "shape_language": "扁平几何、极简线条、网格辅助、高度结构化",
        "imagery_style": "扁平图表、简约图形、数字驱动、清晰分层",
        "accent_usage": "单色或双色系图表，数据标签清晰。保持克制的视觉噪音，让数据成为主角。",
        "best_for": ["统计汇报", "市场分析", "KPI展示", "数据对比", "研究结果"],
        "avoid": ["情感叙事", "创意提案", "品牌故事", "需要亲和力的人文主题"]
    },

    "terminal_tech": {
        "category": "结构与技术型",
        "aliases": ["terminal_tech", "终端风", "代码风", "黑客风", "技术深潜", "网络安全风"],
        "description": "终端技术风格。适合网络安全、技术深潜、压力测试、强调原始数据权威感的场景。纯黑背景搭配等宽字体和高对比绿色/白色文字，传递极客感和数据权威。",
        "palette": ["#0D0D0D", "#000000", "#00FF00", "#39FF14", "#FFFFFF", "#FF3333"],
        "fonts": ["JetBrains Mono", "Fira Code", "Consolas", "monospace"],
        "shape_language": "终端窗口边框、ASCII 线条、代码块结构、进度条元素",
        "imagery_style": "代码界面、终端截图风格、二进制元素、光标闪烁感",
        "accent_usage": "亮绿色用于主文字和成功状态，红色用于警告/错误。保持终端的真实还原感。",
        "best_for": ["网络安全", "技术深潜", "压力测试", "开发者分享", "数据权威展示"],
        "avoid": ["对外商务", "高管汇报", "品牌展示", "轻松活泼场景"]
    },

    "swiss_design": {
        "category": "结构与技术型",
        "aliases": ["swiss_design", "瑞士设计风", "网格风", "国际化设计", "严谨商务"],
        "description": "瑞士设计风格。适合严谨企业沟通、数据密集型报告、权威发布场景。严格的网格系统搭配无衬线字体和精确的排版，传递成熟稳重和国际化视野。",
        "palette": ["#FFFFFF", "#F5F5F5", "#111111", "#333333", "#0066CC", "#E30613"],
        "fonts": ["Helvetica Neue", "Arial", "Univers", "sans-serif"],
        "shape_language": "严格网格、分栏布局、精确边距、水平线分隔",
        "imagery_style": "精准图形、图表规范、摄影为主、国际化视觉语言",
        "accent_usage": "红色用于重要标记和品牌色，蓝黑用于正文。保持瑞士设计的理性和克制。",
        "best_for": ["严谨企业报告", "数据密集型分析", "国际化商务", "学术发布", "正式年报"],
        "avoid": ["创意行业", "情感叙事", "年轻化品牌", "轻松活泼场景"]
    },

    "academic_paper": {
        "category": "结构与技术型",
        "aliases": ["academic_paper", "学术风", "学术报告风", "nature风格", "science风格", "研究风"],
        "description": "学术研究风格。适合学术报告、研究结果展示、论文答辩场景。白色背景搭配经典衬线字体和精确的图表布局，传递权威性和学术严谨。",
        "palette": ["#FFFFFF", "#111111", "#004B87", "#A32638", "#F5F5F5", "#2C3E50"],
        "fonts": ["Times New Roman", "Georgia", "Arial", "serif"],
        "shape_language": "严格分栏、细线分隔、图表编号、引用标注",
        "imagery_style": "科学图表、数据可视化、示意图、引用样式",
        "accent_usage": "学术蓝用于章节编号和图表标签，深红用于重要发现和引用标记。保持学术的严肃和精确。",
        "best_for": ["学术报告", "研究结果展示", "论文答辩", "科学传播", "数据密集研究"],
        "avoid": ["商业提案", "品牌展示", "轻松活泼场景", "情感叙事"]
    },

    # ═══════════════════════════════════════════════════════════
    # 3. 商务与高端型 (Business & Premium)
    # ═══════════════════════════════════════════════════════════

    "claude_minimalist": {
        "category": "商务与高端型",
        "aliases": ["claude_minimalist", "claude", "claude风格", "克劳德风格", "claude minimalist", "claude minimal", "温暖知识风"],
        "description": "Claude 极简温暖风格。适合知识分享、思考型内容、AI助手介绍场景。柔和的米白/奶油色背景搭配古典衬线标题和现代无衬线正文，传递温暖、知识和思辨感。",
        "palette": ["#F9F8F6", "#2D2D2D", "#D97757", "#E6E2DD", "#8B7355"],
        "fonts": ["Tiempos Text", "Copernicus", "Georgia", "serif for headings", "Suisse Intl", "Inter", "sans-serif for body"],
        "shape_language": "柔和圆角、有机但结构化、大量留白、呼吸感布局",
        "imagery_style": "极简纹理、编辑插画、暖色光影、知识感图形",
        "accent_usage": "#D97757 暖赭石色用于重点数字、关键词、细线下划线或项目符号。契合温暖知识氛围。",
        "best_for": ["知识分享", "AI 助手介绍", "思考型内容", "数字花园", "个人品牌"],
        "avoid": ["高强度商务谈判", "数据密集型报告", "快节奏叙事"]
    },

    "apple_keynote": {
        "category": "商务与高端型",
        "aliases": ["apple_keynote", "苹果风", "苹果发布会风格", "keynote", "发布会风", "电影感"],
        "description": "Apple Keynote 演示风格。适合产品发布、高端品牌展示、重要演讲场景。深黑背景搭配超大白色字体和绚丽渐变，传递高级、戏剧性和电影感。",
        "palette": ["#000000", "#FFFFFF", "#0066CC", "#FF2D55", "#1D1D1F", "#5856D6"],
        "fonts": ["San Francisco", "SF Pro Display", "Helvetica Neue", "sans-serif"],
        "shape_language": "极简、隐形网格、中心聚焦、流动留白",
        "imagery_style": "电影光影、超写实3D渲染、戏剧性聚光、渐变发光元素",
        "accent_usage": "#0066CC 蓝色用于产品名或指标文字，#FF2D55 用于情感高潮时刻。两者在黑底上都能发光。",
        "best_for": ["产品发布", "高端品牌", "重要演讲", "苹果系产品", "科技感叙事"],
        "avoid": ["学术报告", "内部培训", "数据密集型分析", "严肃政策类"]
    },

    "liquid_glass": {
        "category": "商务与高端型",
        "aliases": ["liquid_glass", "glassmorphism", "毛玻璃风", "液态玻璃", "bento", "便当盒", "玻璃界面风", "金融科技风", "毛玻璃界面"],
        "description": "高级毛玻璃/液态玻璃风格。适合金融科技、高端 SaaS、下一代产品展示场景。半透明磨砂玻璃卡片叠加在虚幻光感的背景上，配合 Bento Grid 布局，传递高级科技和未来感。",
        "palette": ["#F2F2F7", "#1D1D1F", "#007AFF", "#34C759", "#8E8E93", "#5856D6"],
        "fonts": ["Inter", "Helvetica Neue", "SF Pro", "sans-serif"],
        "shape_language": "圆角矩形 (Bento grids)、非对称网格布局、磨砂玻璃面板",
        "imagery_style": "柔和水纹、光晕泄漏、抽象流动背景、宏纹理",
        "accent_usage": "#007AFF (iOS蓝) 用于重点数字、活跃指标或 CTA 文字。#34C759 (绿色) 用于正向指标。可作为发光文字或玻璃卡片边框。",
        "best_for": ["金融科技", "高端 SaaS", "AI 产品展示", "数字化转型", "下一代界面"],
        "avoid": ["传统行业汇报", "学术内容", "手工/温暖感内容"]
    },

    "dark_luxury": {
        "category": "商务与高端型",
        "aliases": ["dark_luxury", "luxury", "黑金风", "奢华", "黑金奢华", "premium", "高端奢华"],
        "description": "深色奢华风格。适合高端品牌、高净值人群内容、奢华产品展示场景。深炭色或纯黑背景搭配金色/黄铜/古铜色金属光泽，传递排他性和高价值感。",
        "palette": ["#0D0D0D", "#F5F5F5", "#D4AF37", "#C5B358", "#1A1A1A", "#B8860B"],
        "fonts": ["Cinzel", "Optima", "Lato", "serif/sans-serif mix"],
        "shape_language": "对称、锋利几何切角、细金线、优雅边框",
        "imagery_style": "低调光影、金属反射、高对比明暗分割、奢华纹理",
        "accent_usage": "#D4AF37 金色作为金属渐变文字、发光线条或重点数字。保留给强调使用——不用在正文。",
        "best_for": ["高端品牌", "奢侈品", "高端腕表/汽车", "私人银行", "顶奢品牌"],
        "avoid": ["大众消费品", "年轻化品牌", "数据密集型", "教育培训"]
    },

    "executive_dashboard": {
        "category": "商务与高端型",
        "aliases": ["executive_dashboard", "高管仪表盘风", "KPI风", "指挥中心风", "深色仪表盘", "财务看板"],
        "description": "高管仪表盘风格。适合 KPI 追踪、财务进度、指挥中心式总结场景。深色界面背景搭配模块化卡片和进度条/环形图，传递控制感和全局视野。",
        "palette": ["#0F172A", "#1E293B", "#334155", "#22D3EE", "#10B981", "#F59E0B"],
        "fonts": ["Inter", "Roboto", "sans-serif"],
        "shape_language": "模块化卡片、网格布局、进度环/条、数据条",
        "imagery_style": "数据看板、仪表盘 UI、实时数据可视化、低多边形背景",
        "accent_usage": "青色/蓝绿用于正向指标，琥珀色用于警示，金色用于关键决策点。保持数据驱动的高管视角。",
        "best_for": ["KPI 汇报", "财务进度", "业务总览", "指挥中心", "战略跟踪"],
        "avoid": ["创意提案", "品牌展示", "情感叙事", "对外商务"]
    },

    "strategic_infographic": {
        "category": "商务与高端型",
        "aliases": ["strategic_infographic", "战略信息图风", "路线图风", "章节感", "战略叙事", "商业蓝图"],
        "description": "战略信息图风格。适合路线图、高层战略、业务规划、影响力叙事场景。清晰的章节划分配合突出的重点数字，传递战略高度和清晰思路。",
        "palette": ["#FFFFFF", "#1A1A2E", "#4A90D9", "#E94560", "#F5F5F5", "#2D3436"],
        "fonts": ["Montserrat", "Helvetica Neue", "Arial", "sans-serif"],
        "shape_language": "章节分隔、流程箭头、时间轴、模块化区块",
        "imagery_style": "战略图示、里程碑标记、重点数字突出、干净的图形系统",
        "accent_usage": "蓝色系用于战略主线，红色用于关键转折点或警示。保持高管的清晰思路和战略高度。",
        "best_for": ["战略路线图", "高层汇报", "业务规划", "影响力叙事", "年度规划"],
        "avoid": ["技术细节", "实操培训", "创意提案", "轻松活泼场景"]
    },

    "sharp_minimalism": {
        "category": "商务与高端型",
        "aliases": ["sharp_minimalism", "高端极简商业风", "sharp-edged minimalism", "网格式商务", "克制商务"],
        "description": "锋利极简商务风格。适合公司介绍、产品介绍、高层沟通、商务提案场景。严格网格配合细线分隔和单色系，传递成熟稳重、高端克制但不浮夸的商务气质。",
        "palette": ["#FFFFFF", "#F8F9FA", "#111111", "#333333", "#666666", "#000000"],
        "fonts": ["Helvetica Neue", "Arial", "Futura", "sans-serif"],
        "shape_language": "刚性网格、细线分隔、左上角导航暗示、水平对称",
        "imagery_style": "高品质摄影、简洁产品图、黑白灰为主、精确留白",
        "accent_usage": "纯黑用于标题和重点文字，灰色用于辅助信息。保持绝对克制，不使用鲜艳色彩。",
        "best_for": ["公司介绍", "产品介绍", "高层沟通", "商务提案", "成熟企业"],
        "avoid": ["年轻化品牌", "创意提案", "创意行业", "活泼轻松场景"]
    },

    # ═══════════════════════════════════════════════════════════
    # 4. 人物与亲和型 (Human & Approachable)
    # ═══════════════════════════════════════════════════════════

    "soft_3d_clay": {
        "category": "人物与亲和型",
        "aliases": ["soft_3d_clay", "soft 3d", "clay", "3d clay", "3d粘土风", "粘土风", "macaron", "马卡龙", "cute", "可爱风", "软萌风"],
        "description": "柔和 3D 粘土风格。适合面向新人、轻松内容、亲和型产品讲解场景。柔软膨胀的 3D 元素配合马卡龙色系，传递可爱、温暖和易接近感。",
        "palette": ["#FDFBF7", "#2F4F4F", "#FFB6C1", "#87CEFA", "#98FB98", "#FFE4B5", "#DDA0DD"],
        "fonts": ["Quicksand", "Nunito", "Poppins", "sans-serif"],
        "shape_language": "膨胀圆润、极度圆角、药丸形状、柔软弹性质感",
        "imagery_style": "3D 粘土渲染、哑光表面、柔和光影、卡通化元素",
        "accent_usage": "#FFB6C1 柔粉和 #87CEFA 天蓝充满糖果感——适合强调词、药丸形标签或图标填充。保持可爱不腻。",
        "best_for": ["面向新人内容", "轻松产品讲解", "可爱风格", "儿童教育", "亲和型品牌"],
        "avoid": ["高管汇报", "严肃商务", "技术架构", "数据密集型"]
    },

    "corporate_memphis": {
        "category": "人物与亲和型",
        "aliases": ["corporate_memphis", "企业协作插画风", "扁平人物风", "团队风", "HR风", "组织文化风"],
        "description": "企业协作插画风格。适合 HR 内容、团队文化、组织说明、协作叙事场景。简化的扁平人物插画配合几何色块，传递专业但不冷漠的团队协作氛围。",
        "palette": ["#FFFFFF", "#F0F4F8", "#800020", "#FFB8D2", "#B8E0FF", "#FFEAA7"],
        "fonts": ["Nunito", "Poppins", "Quicksand", "sans-serif"],
        "shape_language": "扁平人物、几何色块、简化形状、自然姿态",
        "imagery_style": "扁平插画、人物为主、团队场景、轻商务感",
        "accent_usage": "柔和但饱和的蓝色和橙色用于人物服装和物体。保持温暖专业但不冰冷。",
        "best_for": ["HR 内容", "团队文化", "组织说明", "协作叙事", "员工沟通"],
        "avoid": ["技术架构", "金融数据", "高端奢华", "严肃政策"]
    },

    "paper_craft": {
        "category": "人物与亲和型",
        "aliases": ["paper_craft", "纸艺风", "手工风", "纸层风", "触感风", "教育风"],
        "description": "纸艺手作风格。适合创意提案、教育内容、需要降低技术压迫感的场景。层叠纸张效果配合手工质感，传递温暖、可触感和创作手工感。",
        "palette": ["#FFFEF0", "#F5E6D3", "#E8D5C4", "#C4A484", "#8B7355", "#D2691E"],
        "fonts": ["Caveat", "Kalam", "Patrick Hand", " handwritten"],
        "shape_language": "层叠纸张边缘、手撕质感、阴影层次、纸质纹理",
        "imagery_style": "纸张层叠、手工裁剪质感、拼贴组合、温暖的纸纹",
        "accent_usage": "暖棕色用于纸张边缘和阴影，彩色纸张用于信息卡片。保持手工的随意和温暖感。",
        "best_for": ["创意提案", "教育内容", "工作坊", "降低技术压迫感", "温暖叙事"],
        "avoid": ["高端奢华", "高管汇报", "数据密集型", "严肃商务"]
    },

    # ═══════════════════════════════════════════════════════════
    # 5. 编辑、杂志与潮流型 (Editorial, Magazine & Street)
    # ═══════════════════════════════════════════════════════════

    "magazine_editorial": {
        "category": "编辑、杂志与潮流型",
        "aliases": ["magazine_editorial", "magazine", "editorial", "时尚杂志风", "杂志风", "vogue", "kinfolk", "编辑风", "高阶杂志"],
        "description": "高端时尚杂志编辑风格。适合品牌内容、生活方式、社交传播型 deck 场景。大幅出血摄影配合极端留白和精致衬线混搭，传递高级媒体感和编辑力度。",
        "palette": ["#FAF9F6", "#1A1A1A", "#8B0000", "#D3D3D3", "#4A4A4A", "#C0C0C0"],
        "fonts": ["Playfair Display", "Didot", "Bodoni", "serif", "Montserrat", "sans-serif"],
        "shape_language": "极端留白、精细分割线、不对称但完美平衡、编辑节奏",
        "imagery_style": "时尚摄影、高端编辑、柔光颗粒、戏剧性打光",
        "accent_usage": "#8B0000 深绯红在需要克制时制造最大编辑冲击力——可用于关键词、细线、引言标记或页码。",
        "best_for": ["品牌内容", "生活方式", "女性向内容", "社交传播", "高端媒体"],
        "avoid": ["技术培训", "数据汇报", "内部沟通", "严肃政策"]
    },

    "yellow_black_editorial": {
        "category": "编辑、杂志与潮流型",
        "aliases": ["yellow_black_editorial", "黄黑编辑风", "黄底黑字风", "时尚杂志黄", "强冲击编辑"],
        "description": "黄黑编辑冲击力风格。适合年轻化品牌、强记忆点、趋势和观点表达场景。明黄背景搭配黑色粗体字，配合时尚杂志节奏和贴纸感点缀，传递高能量和强视觉记忆。",
        "palette": ["#FFD700", "#FFFF00", "#000000", "#1A1A1A", "#FF6600", "#FFFFFF"],
        "fonts": ["Impact", "Helvetica Bold", "Arial Black", "sans-serif"],
        "shape_language": "大字标题、粗黑边缘、贴纸点缀、杂志拼贴节奏",
        "imagery_style": "高对比、时尚杂志感、贴纸元素、流行文化引用",
        "accent_usage": "纯黑用于标题和主文字，橙色或其他亮色用于贴纸点缀。保持高能量但不混乱。",
        "best_for": ["年轻化品牌", "强记忆点内容", "趋势表达", "观点型叙事", "社交营销"],
        "avoid": ["高管汇报", "学术报告", "数据密集型", "稳重商务"]
    },

    "modern_newspaper": {
        "category": "编辑、杂志与潮流型",
        "aliases": ["modern_newspaper", "商业媒体风", "现代报纸风", "大标题编辑风", "media风格", "商业评论风"],
        "description": "现代商业媒体风格。适合趋势解读、商业评论、创始人表达、观点型汇报场景。超大大标题配合不对称排版和强留白，传递媒体感、编辑力度和思想领导力。",
        "palette": ["#FFFFFF", "#F5F5F0", "#111111", "#222222", "#CC0000", "#FFD700"],
        "fonts": ["Playfair Display", "Roboto Slab", "serif", "Roboto", "Helvetica", "sans-serif"],
        "shape_language": "大标题层级、不对称布局、强留白张力、细线分割",
        "imagery_style": "高质量编辑摄影、cutout主体、单色或低饱和图像",
        "accent_usage": "红色用于标记和高亮，黄/金色用于观点强调。保持媒体的思想性和权威感。",
        "best_for": ["趋势解读", "商业评论", "创始人演讲", "观点型汇报", "思想领导力"],
        "avoid": ["技术培训", "数据密集型报告", "内部沟通", "轻松活泼场景"]
    },

    "black_orange_creative": {
        "category": "编辑、杂志与潮流型",
        "aliases": ["black_orange_creative", "黑橙创意公司风", "创意机构风", "agency风", "广告风"],
        "description": "黑橙创意公司风格。适合创意提案、作品集展示、发布页场景。白色或浅色背景搭配黑色粗体字和血橙色点缀，传递创意信心、专业气质和现代商业感。",
        "palette": ["#FFFFFF", "#000000", "#FFFFFF", "#FF4500", "#1A1A1A", "#888888"],
        "fonts": ["Futura", "Helvetica Neue", "Arial", "sans-serif"],
        "shape_language": "简洁摄影、粗黑字体、血橙点缀、时尚动感",
        "imagery_style": "高品质摄影、创意构图、简洁有力、国际化广告感",
        "accent_usage": "血橙色用于 CTA 和重点元素。保持创意但不浮夸的专业感。",
        "best_for": ["创意提案", "作品集展示", "发布页", "广告公司", "品牌升级"],
        "avoid": ["学术报告", "政府汇报", "传统行业", "内部培训"]
    },

    # ═══════════════════════════════════════════════════════════
    # 6. 流行、娱乐与高冲击型 (Pop, Youth & High-energy)
    # ═══════════════════════════════════════════════════════════

    "neo_brutalism": {
        "category": "流行、娱乐与高冲击型",
        "aliases": ["neo_brutalism", "neo-brutalism", "neo brutalism", "新粗野主义", "新粗野主义宣言风格", "brutalist", "粗野主义"],
        "description": "新粗野主义风格。适合高能量传播、年轻化品牌、潮流产品的视觉宣言场景。高对比的纯色背景配合粗黑边框和亮色点缀，传递直接、有态度、不道歉的视觉冲击。",
        "palette": ["#FFFFFF", "#000000", "#E0FF4F", "#FF6666", "#4D96FF", "#FFFF00"],
        "fonts": ["Space Grotesk", "Helvetica Now Display", "Arial Black", "sans-serif"],
        "shape_language": "粗黑边框、硬投影偏移、尖角矩形、无渐变",
        "imagery_style": "波普艺术、高对比、醒目 cutout、平面色块、原始纹理",
        "accent_usage": "#E0FF4F 亮绿和 #FF6666 珊瑚红在黑白背景下格外有力——适合重点数字、强调词、填充标签盒或粗下划线。",
        "best_for": ["高能量传播", "年轻化品牌", "潮流产品", "社交媒体", "大胆声明"],
        "avoid": ["高管汇报", "学术报告", "需要温和感的场景", "传统行业"]
    },

    "holographic_chrome": {
        "category": "流行、娱乐与高冲击型",
        "aliases": ["holographic_chrome", "holographic", "chrome", "镭射风", "全息风", "全息渐变", "y2k", "Y2K", "虹彩"],
        "description": "全息铬金属风格。适合 AI 产品、开发者文化、年轻创业团队、Y2K 复兴场景。抛光铬金属表面反射蓝紫粉彩虹渐变，配合极深或极浅的背景，传递未来感、高科技和边缘感。",
        "palette": ["#121212", "#E0E0E0", "#4169E1", "#FF00FF", "#00FFFF", "#9370DB"],
        "fonts": ["Syne", "Space Mono", "Orbitron", "sans-serif"],
        "shape_language": "流体金属blob、锋利铬字形、液态金属扭曲",
        "imagery_style": "镜面铬反射、彩虹薄膜干扰、3D流体金属、棱镜光",
        "accent_usage": "#4169E1 蓝、#FF00FF 品红、#00FFFF 青作为彩虹渐变点缀——适合重点数字、标题词、铬色边框光晕。以全息闪烁方式使用，不做平面色块。",
        "best_for": ["AI 产品", "开发者文化", "年轻创业", "Y2K 复兴", "游戏/元宇宙"],
        "avoid": ["传统商务", "高管汇报", "学术报告", "稳重行业"]
    },

    "cyberpunk": {
        "category": "流行、娱乐与高冲击型",
        "aliases": ["cyberpunk", "赛博朋克风", "赛博朋克风格", "tech neon", "霓虹科技风"],
        "description": "赛博朋克高科技风格。适合激进未来科技、舞台型发布、视觉冲击优先场景。深海黑/深蓝背景配合霓虹青、品红、电黄元素，传递反乌托邦但充满活力的高科技感。",
        "palette": ["#0B0C10", "#E0E0E0", "#66FCF1", "#FF007F", "#45A29E", "#F3E600"],
        "fonts": ["JetBrains Mono", "Orbitron", "monospace"],
        "shape_language": "几何切割、线框网格、霓虹边框、角度锐利",
        "imagery_style": "霓虹灯光、故障艺术、高科技 HUD 叠加、深巷氛围",
        "accent_usage": "#66FCF1 霓虹青和 #FF007F 霓虹品红在深色背景上发光——适合重点数字、HUD 标签或发光标题词。",
        "best_for": ["激进未来科技", "舞台发布", "视觉冲击", "游戏/电竞", "亚文化"],
        "avoid": ["稳重高管汇报", "学术报告", "传统行业", "温和沟通"]
    },

    "manga_narrative": {
        "category": "流行、娱乐与高冲击型",
        "aliases": ["manga_narrative", "漫画风", "分镜风", "漫画叙事风", "日漫风", "动漫风"],
        "description": "漫画叙事风格。适合把复杂内容讲得更有趣、onboarding、面向普通人的说明内容场景。漫画分镜配合叙事序列，传递故事感、参与感和易记忆性。",
        "palette": ["#FFFFFF", "#FFFEFC", "#1A1A2E", "#E94560", "#0F3460", "#FFD700"],
        "fonts": ["Noto Sans JP", "M PLUS Rounded 1c", "sans-serif"],
        "shape_language": "漫画分镜、对话气泡、速度线、动作效果线",
        "imagery_style": "漫画风格、叙事序列、场景转换、人物动态",
        "accent_usage": "保持漫画的彩色/黑白对比节奏。标题和重点可用速度线强调。",
        "best_for": ["内容趣味化", "onboarding", "普通人说明", "故事型叙事", "培训课件"],
        "avoid": ["高管战略", "数据密集汇报", "严肃政策", "高端奢华"]
    },

    "sports_energy": {
        "category": "流行、娱乐与高冲击型",
        "aliases": ["sports_energy", "运动风", "热血风", "运动能量风", "速度感", "激励风"],
        "description": "运动热血风格。适合激励型内容、招募、战役型传播场景。对角线构图配合强对比和大字标题，传递速度感、能量和强节奏。",
        "palette": ["#000000", "#FFFFFF", "#FF3300", "#FFCC00", "#1A1A1A", "#FF6600"],
        "fonts": ["Impact", "Arial Black", "Helvetica Bold", "sans-serif"],
        "shape_language": "对角线构图、速度线、强烈对比、大字占据",
        "imagery_style": "运动摄影、动感模糊、聚光灯、能量光效",
        "accent_usage": "橙色/红色用于能量标记和 CTA。标题用大字全出血占据画面。保持高能但不混乱。",
        "best_for": ["激励演讲", "招募宣讲", "战役传播", "产品发布", "能量宣言"],
        "avoid": ["学术报告", "冷静分析", "数据密集型", "内部培训"]
    },

    "digital_neo_pop": {
        "category": "流行、娱乐与高冲击型",
        "aliases": ["digital_neo_pop", "数码拼贴风", "neo pop", "像素风", "builder风", "开发者文化"],
        "description": "数码拼贴潮流风格。适合 AI 产品、开发者文化、年轻创业团队场景。模块化色块配合粗轮廓和像素/开发者图标语言，传递反传统企业感的 builder 能量。",
        "palette": ["#FFFFFF", "#1A1A2E", "#FF6B6B", "#4ECDC4", "#FFE66D", "#95E1D3"],
        "fonts": ["Space Grotesk", "JetBrains Mono", "monospace", "sans-serif"],
        "shape_language": "模块化色块、粗像素轮廓、几何变形、拼贴组合",
        "imagery_style": "像素图标、dev工具截图风格、亮色块、年轻化图形",
        "accent_usage": "热粉/黄/青高饱和色块用于模块背景和图标。保持 builder 的活泼和反叛感。",
        "best_for": ["AI 产品", "开发者工具", "创业团队", "数字文化", "技术社区"],
        "avoid": ["传统商务", "高管汇报", "学术报告", "严肃行业"]
    },

    "pink_street_style": {
        "category": "流行、娱乐与高冲击型",
        "aliases": ["pink_street_style", "粉色街头风", "街潮风", "粉色系", "网红风"],
        "description": "粉色街头潮流风格。适合年轻 campaign、创作者 deck、活泼发布场景。更大胆的粉色使用配合街头时尚节奏，传递表达欲和现代潮流感。",
        "palette": ["#FFFFFF", "#FFF0F5", "#FF69B4", "#FF1493", "#1A1A1A", "#FFB6C1"],
        "fonts": ["Helvetica Neue", "Arial", "Quicksand", "sans-serif"],
        "shape_language": "圆角元素、柔和边缘、街头摄影节奏、表情符号点缀",
        "imagery_style": "街头摄影、柔和粉色系、活泼插画、社交媒体感",
        "accent_usage": "深粉色用于强调和 CTA，浅粉色用于背景和辅助。保持现代而不俗气。",
        "best_for": ["年轻 campaign", "创作者", "生活方式品牌", "社交营销", "活泼产品"],
        "avoid": ["高管汇报", "学术报告", "传统行业", "严肃商务"]
    },

    # ═══════════════════════════════════════════════════════════
    # 7. Artistic & Avant-garde
    # ═══════════════════════════════════════════════════════════

    "japanese_aesthetic": {
        "category": "Artistic & Avant-garde",
        "aliases": ["japanese_aesthetic", "wabi-sabi", "日式美学", "日式美学风", "和风", "日式极简", "枯山水"],
        "description": "日本侘寂美学风格。适合文化内容、冥想引导、体现「不完美之美」的叙事场景。大地色系配合极度留白和不规则平衡，传递禅意、宁静和文化深度。",
        "palette": ["#EAE7E0", "#4A4E4D", "#828C7E", "#B0A18F", "#2C3531", "#D4C5B0"],
        "fonts": ["Shippori Mincho", "Noto Serif JP", "serif"],
        "shape_language": "不规则平衡、细线分割、极度留白、自然比例",
        "imagery_style": "胶片摄影、自然光影、淡墨、枯山水纹理",
        "accent_usage": "#828C7E 灰绿色在克制使用时最契合——可用于单个关键词、细线或圆点标记。少即是多。",
        "best_for": ["文化叙事", "冥想引导", "茶道/花道", "日式品牌", "慢生活"],
        "avoid": ["快节奏叙事", "数据密集型", "高效商务", "轻松活泼"]
    },

    "traditional_chinese": {
        "category": "Artistic & Avant-garde",
        "aliases": ["traditional_chinese", "chinese", "国风", "新中式", "国潮", "水墨风", "中国美学"],
        "description": "现代传统中国美学风格。适合文化演讲、传统品牌、中式品牌升级场景。水墨元素配合现代简约布局，使用朱红、靛蓝和墨黑，传递诗意、文化和宁静感。",
        "palette": ["#F5F4F1", "#222222", "#C83C23", "#4B5CC4", "#817E7B", "#D4C5B0"],
        "fonts": ["Noto Serif SC", "FZShuTi", "STKaiti", "serif"],
        "shape_language": "圆形窗洞(月亮门)、竖排文字元素、流动墨线、留白",
        "imagery_style": "水墨晕染、淡墨山影、传统纹理、宁静氛围",
        "accent_usage": "#C83C23 朱红和 #4B5CC4 靛蓝承载文化重量——适合关键词、印章图案、竖线标记或章节编号。诗意克制最契合。",
        "best_for": ["文化演讲", "中式品牌", "传统节日", "诗词内容", "博物馆导览"],
        "avoid": ["快节奏商业", "年轻化品牌", "数据密集型", "轻松活泼"]
    },

    "royal_blue_red_watercolor": {
        "category": "Artistic & Avant-garde",
        "aliases": ["royal_blue_red_watercolor", "水彩风", "皇家蓝红水彩", "绘画感", "艺术风"],
        "description": "皇家蓝 × 深红水彩风格。适合愿景叙事、文化品牌故事、情感诠释场景。水彩纹理配合受控的色彩戏剧，传递艺术感、情感深度和视觉张力。",
        "palette": ["#FFFFFF", "#F5F5F0", "#002366", "#8B0000", "#4169E1", "#DC143C"],
        "fonts": ["Playfair Display", "Bodoni", "Georgia", "serif"],
        "shape_language": "水彩晕染边缘、流动线条、绘画性分割、戏剧性留白",
        "imagery_style": "水彩纹理、绘画感、色彩泼溅、艺术摄影",
        "accent_usage": "皇家蓝和深红作为主视觉色调。可做渐变晕染或色块并置。保持艺术感但不过度。",
        "best_for": ["愿景叙事", "文化品牌", "情感诠释", "艺术展示", "创始人故事"],
        "avoid": ["数据密集型", "技术培训", "冷静分析", "高效商务"]
    },

    "deformed_flat_persona": {
        "category": "Artistic & Avant-garde",
        "aliases": ["deformed_flat_persona", "变形扁平人物风", "艺术人物风", "身份认同", "抽象人物"],
        "description": "变形扁平人物风格。适合概念叙事、艺术驱动展示、身份认同强的内容场景。艺术化变形的抽象人物配合几何元素，传递独特个性、艺术气质和身份认同感。",
        "palette": ["#FFFFFF", "#2D3436", "#6C5CE7", "#FD79A8", "#00CEC9", "#E17055"],
        "fonts": ["Helvetica Neue", "Avenir", "Futura", "sans-serif"],
        "shape_language": "变形人物、几何碎片、抽象轮廓、解构重组",
        "imagery_style": "艺术插画、人物抽象化、几何拼贴、色彩解构",
        "accent_usage": "高饱和色彩用于变形人物和几何碎片。保持艺术感但保持可读性。",
        "best_for": ["概念叙事", "艺术展示", "身份认同", "创意演讲", "个人品牌"],
        "avoid": ["普通商务", "数据汇报", "技术培训", "传统行业"]
    },

    "studio_mockup_premium": {
        "category": "Artistic & Avant-garde",
        "aliases": ["studio_mockup_premium", "studio", "mockup", "高端产品风", "产品展示风", "摄影棚风"],
        "description": "高端摄影棚/模型产品风格。适合高端产品 deck、SaaS 定位、产品营销场景。哑光克制的视觉语言配合产品中心英雄图，传递高级质感、专业和精致。",
        "palette": ["#F8F9FA", "#FFFFFF", "#1A1A1A", "#333333", "#C0C0C0", "#2C3E50"],
        "fonts": ["Helvetica Neue", "Arial", "Futura", "sans-serif"],
        "shape_language": "极简背景、中心聚焦、产品为主、精确光影",
        "imagery_style": "高端产品摄影、模型感、精确打光、简约背景",
        "accent_usage": "中性灰色用于背景和辅助，深色用于产品主体。保持绝对克制和高级感。",
        "best_for": ["高端产品", "SaaS 定位", "精致品牌", "产品营销", "顶奢服务"],
        "avoid": ["内容密集型", "创意提案", "活泼场景", "教育培训"]
    },

    "classic_pop_sculpture_vaporwave": {
        "category": "Artistic & Avant-garde",
        "aliases": ["classic_pop_sculpture_vaporwave", "古典波普风", "雕塑风", "vaporwave", "蒸汽波", "复古未来"],
        "description": "古典与波普/蒸汽波融合风格。适合实验性品牌、创意 campaign、视觉大胆的内容场景。古典雕塑元素配合霓虹粉蓝渐变，传递复古未来感和艺术冲击力。",
        "palette": ["#FFFFFF", "#1A1A2E", "#FF71CE", "#01CDFE", "#B967FF", "#05FFA1"],
        "fonts": ["Times New Roman", "Courier New", "serif", "monospace"],
        "shape_language": "古典雕塑、网格透视、霓虹渐变、复古网格",
        "imagery_style": "雕塑 + 霓虹、复古3D渲染、蒸汽波美学、故障艺术",
        "accent_usage": "霓虹粉/蓝/紫渐变用于高光和特效。保持古典和未来的戏剧性对比。",
        "best_for": ["实验品牌", "创意 campaign", "艺术节", "音乐/娱乐", "大胆视觉"],
        "avoid": ["传统商务", "学术报告", "高管汇报", "教育培训"]
    },

    "tech_art_neon": {
        "category": "Artistic & Avant-garde",
        "aliases": ["tech_art_neon", "科技艺术风", "艺术科技风", "TechArt", "视觉艺术科技"],
        "description": "科技艺术霓虹风格。适合前沿 AI 展示、艺术科技融合、视觉激进的未来叙事场景。暗色舞台配合霓虹光效和高对比，传递科技与艺术的边界模糊感。",
        "palette": ["#0A0A0A", "#1A1A2E", "#00FFFF", "#FF00FF", "#FFFFFF", "#FFD700"],
        "fonts": ["Syne", "Orbitron", "Space Mono", "sans-serif"],
        "shape_language": "暗色舞台、光效叠加、几何切割、动态模糊",
        "imagery_style": "霓虹光效、科技艺术、粒子系统、动态光影",
        "accent_usage": "青色和品红作为主霓虹色，可做发光文字或光效叠加。保持视觉激进但不杂乱。",
        "best_for": ["AI 艺术展示", "科技艺术节", "前沿演讲", "实验项目", "激进未来叙事"],
        "avoid": ["普通商务", "学术报告", "冷静分析", "教育培训"]
    },

    # ═══════════════════════════════════════════════════════════
    # 8. 极简风格补充 (Minimalist Additions)
    # ═══════════════════════════════════════════════════════════

    "mincho_handwritten_mix": {
        "category": "Artistic & Avant-garde",
        "aliases": ["mincho_handwritten_mix", "明朝手写混搭风", "衬线手写混搭", "文学感", "人文风"],
        "description": "明朝体 × 手写体混搭风格。适合反思性散文、文化 deck、情感但有设计的沟通场景。衬线标题配合手写正文，传递文学感、个人声音和柔和人文气质。",
        "palette": ["#FFFEF5", "#2D3436", "#636E72", "#D63031", "#6C5CE7", "#00B894"],
        "fonts": ["Noto Serif JP", "Shippori Mincho", "serif", "Kalam", "Handwritten"],
        "shape_language": "文学排版、手写点缀、柔和分割线、呼吸感留白",
        "imagery_style": "文学感、书写质感、纸张纹理、手稿氛围",
        "accent_usage": "深色墨水感用于衬线标题，手写体用于引用和注释。保持文学的私人感。",
        "best_for": ["反思性散文", "文化 deck", "情感叙事", "个人品牌", "文学分享"],
        "avoid": ["高效商务", "数据密集型", "技术培训", "快节奏叙事"]
    },

}


def get_curated_style(user_preference: str) -> dict:
    """
    Check if the user preference matches any curated style aliases.
    Returns the style dict if found, else None.
    """
    if not user_preference:
        return None

    pref_lower = user_preference.lower().strip()

    for style_key, style_data in STYLE_LIBRARY.items():
        for alias in style_data.get("aliases", []):
            if alias.lower() in pref_lower or pref_lower in alias.lower():
                return style_data

    return None


def get_styles_by_category(category: str) -> list:
    """
    Return all styles in a given category.
    """
    return [
        {"key": k, **v}
        for k, v in STYLE_LIBRARY.items()
        if v.get("category") == category
    ]


def list_all_categories() -> list:
    """
    Return unique category names.
    """
    return list(set(v.get("category") for v in STYLE_LIBRARY.values()))
