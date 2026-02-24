"""
Auto Pipeline (RFC v2.0 Final Implementation) - Skill Version
全自动 PPT 生成入口：智能解析内容、自动提取模版、生成计划并执行
"""
import os
import sys
import json
import logging
from pathlib import Path

# 添加 src 目录到路径，以便导入 nano_banana_ppt 包
# __file__ = ~/.cursor/skills/nano-banana-ppt/scripts/ppt_gen_v2.py
# src      = ~/.cursor/skills/nano-banana-ppt/src
src_path = Path(__file__).resolve().parent.parent / 'src'
sys.path.insert(0, str(src_path))

# 尝试加载 .env 文件 (从 script 目录)
try:
    from dotenv import load_dotenv
    env_path = Path(__file__).parent / '.env'
    if env_path.exists():
        load_dotenv(dotenv_path=env_path)
    # 也尝试加载当前工作目录下的 .env
    load_dotenv()
except ImportError:
    pass

# Adjusted imports for Skill structure
try:
    from nano_banana_ppt.agents.narrative import NarrativeAgent
    from nano_banana_ppt.agents.visual import VisualAgent
    from nano_banana_ppt.agents.template import TemplateAgent
    from nano_banana_ppt.core.executor import execute_plan
except ImportError as e:
    print(f"❌ Error importing dependencies: {e}")
    print("Please install required packages: pip install openai pymupdf python-pptx pillow python-dotenv requests")
    sys.exit(1)

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def auto_generate_ppt(content_file: str, template_file: str = None, output_name: str = None):
    """
    一键生成 PPT 的主函数
    
    Args:
        content_file: 内容源文件 (Markdown/Text)
        template_file: 模版文件 (PDF/PPTX/Image)，可选
        output_name: 输出文件名，可选
    """
    print(f"\n🚀 Nano Banana Pro Auto Pipeline (Skill Version) 启动")
    print(f"📄 内容源: {content_file}")
    print(f"🎨 模版源: {template_file if template_file else '无 (AI 自动设计)'}")
    
    # 0. 环境检查
    api_key = os.getenv("OPENAI_API_KEY") or os.getenv("GOOGLE_API_KEY")
    api_base = os.getenv("OPENAI_API_BASE") or "https://generativelanguage.googleapis.com/v1beta/openai"
    
    if not api_key:
        print("❌ 错误: 请设置 OPENAI_API_KEY 或 GOOGLE_API_KEY 环境变量")
        # 尝试提示用户
        print("Tip: You can set it in .env file or export it in your shell.")
        return

    # 1. 初始化 Agents
    try:
        narrative_agent = NarrativeAgent(api_key, api_base)
        visual_agent = VisualAgent(api_key, api_base)
        template_agent = TemplateAgent(api_key, api_base)
    except Exception as e:
        print(f"❌ 初始化 Agents 失败: {e}")
        return
    
    # 2. 读取内容并自动推导参数
    if not os.path.exists(content_file):
        print(f"❌ 错误: 内容文件不存在 {content_file}")
        return
        
    with open(content_file, 'r', encoding='utf-8') as f:
        content_context = f.read()
        
    # 自动推导约束参数 (Auto-Inference)
    print("\n🔍 [Step 1] 正在分析文档内容...")
    try:
        inferred_constraints = narrative_agent.analyze_content(content_context)
        logger.info(f"自动推导参数: {json.dumps(inferred_constraints, ensure_ascii=False)}")
    except Exception as e:
        logger.error(f"内容分析失败: {e}")
        inferred_constraints = {}
    
    # 3. 解析模版 (如果有)
    template_info = None
    assets = {}
    if template_file:
        if os.path.exists(template_file):
            print(f"\n🖼️ [Step 2] 正在解析模版文件...")
            try:
                template_info = template_agent.process_template(template_file)
                assets['template_file'] = template_file
                assets['logo_path'] = template_info.get('logo_path')
                assets['template_images'] = template_info.get('reference_images') # 传递参考图字典
                logger.info("模版解析成功")
            except Exception as e:
                logger.error(f"模版解析失败: {e}")
        else:
            logger.warning(f"模版文件不存在: {template_file}，将使用 AI 自动设计")

    # 4. 生成叙事大纲
    print("\n📝 [Step 3] 正在构建叙事架构...")
    # 合并自动推导的参数
    constraints = {
        "target_audience": inferred_constraints.get("target_audience", "通用受众"),
        "presentation_type": inferred_constraints.get("presentation_type", "商业演示"),
        "duration": inferred_constraints.get("duration", "15分钟"),
        "page_count": "10", # 默认10页
        "style_preference": inferred_constraints.get("style_preference", "专业商务")
    }
    narrative_outline = narrative_agent.generate_narrative_outline(content_context, constraints)
    print(f"✅ 叙事大纲生成完成，共 {len(narrative_outline)} 页")

    # 4.1 预览并确认
    print("\n" + narrative_agent.preview_outline(narrative_outline))
    
    # 交互模式检查: 如果是在 Cursor Agent 环境下运行，可能无法获得 stdin 输入
    # 我们假设如果用户通过 Skill 调用，通常希望自动执行，或者 Agent 已经处理了交互。
    # 这里我们添加一个 --auto 标志或者简单判断 stdin
    # 为了简化 Skill 调用，我们默认自动继续，除非明确取消 (这里不做取消逻辑)
    
    print("\n⚠️ 自动模式: 继续执行生成...")

    # 5. 生成视觉计划
    print("\n🎨 [Step 4] 正在进行视觉规划与 Prompt 工程...")
    style_definition = visual_agent.define_style(constraints, assets, template_info)
    visual_plan = visual_agent.generate_visual_plan(narrative_outline, style_definition, assets, template_info)
    
    # 保存计划
    plan_file = "ppt_generation_plan.json"
    with open(plan_file, "w", encoding='utf-8') as f:
        json.dump(visual_plan, f, ensure_ascii=False, indent=2)
    print(f"✅ 视觉计划已保存: {plan_file}")

    # 6. 执行生成
    print("\n⚡ [Step 5] 开始执行生成...")
    final_output_name = output_name or Path(content_file).stem
    # 确保输出目录存在
    Path("output").mkdir(exist_ok=True)
    
    try:
        execute_plan(plan_file, final_output_name)
    except Exception as e:
        logger.error(f"执行生成失败: {e}")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("用法: python ppt_gen_v2.py <content_file> [template_file] [output_name]")
        sys.exit(1)
        
    content_file = sys.argv[1]
    template_file = sys.argv[2] if len(sys.argv) > 2 else None
    output_name = sys.argv[3] if len(sys.argv) > 3 else None
    
    auto_generate_ppt(content_file, template_file, output_name)
