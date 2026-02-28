"""
Auto Pipeline (RFC v2.2)
全自动 PPT 生成入口：支持 plan / execute 两阶段调用，兼容 Agent 和交互式终端

目录结构:
  output/
    ppt/
      {date}_{project_name}/
        {date}_{project_name}.pptx   ← 最终交付的 PPTX
        plan_for_review.md
        plan.json
        template_assets/
          ref_cover.png ...
        slides/
          slide_01.png ...
"""
import os
import sys
import json
import logging
import re
from pathlib import Path

try:
    from dotenv import load_dotenv
except ImportError:
    load_dotenv = None


def _find_and_load_env() -> bool:
    """
    智能查找并加载 .env 文件
    优先级: 工具目录 → 上级目录 → 工作区根 → nano-banana-ppt skill 目录
    """
    if load_dotenv is None:
        return False
    tool_dir = Path(__file__).resolve().parent
    root = Path(os.getcwd())
    env_locations = [
        tool_dir / ".env",
        root / ".env",
        Path(__file__).resolve().parents[2] / ".env",  # workspace root
        Path.home() / ".cursor" / "skills" / "nano-banana-ppt" / ".env",
        Path.home() / ".claude" / "skills" / "ppt-generator" / ".env",
    ]
    for env_path in env_locations:
        if env_path.exists():
            load_dotenv(dotenv_path=env_path, override=True)
            logger = logging.getLogger(__name__)
            logger.info(f"Loaded .env from: {env_path}")
            return True
    load_dotenv(override=True)
    return False


# 在导入其他模块前加载环境变量
_find_and_load_env()

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from nano_banana_ppt.agents.narrative import NarrativeAgent
from nano_banana_ppt.agents.visual import VisualAgent
from nano_banana_ppt.agents.template import TemplateAgent
from nano_banana_ppt.core.executor import execute_plan
from nano_banana_ppt.utils.llm_client import reset_session
from nano_banana_ppt.utils.review_plan import (
    build_review_md,
    parse_review_md,
    derive_technical_plan,
    REVIEW_MD_FILENAME,
)

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def _resolve_project_dir(content_file: str, output_name: str = None) -> tuple[str, Path]:
    """根据内容文件或指定名称，生成项目名和项目目录"""
    name = output_name or Path(content_file).stem
    from datetime import date
    date_prefix = date.today().strftime("%Y%m%d")
    dir_name = f"{date_prefix}_{name}"
    project_dir = Path("output") / "ppt" / dir_name
    project_dir.mkdir(parents=True, exist_ok=True)
    return name, project_dir


# ──────────────────────────────────────────────
#  Phase 1: Plan
# ──────────────────────────────────────────────

def generate_plan(content_file: str, template_file: str = None,
                  logo_file: str = None, output_name: str = None, page_count: int = None,
                  style_preference: str = None, briefing: str = None):
    """
    Phase 1: 生成人类可审阅的 plan_for_review.md，不执行生图。
    用户审阅、编辑确认后，再运行 execute 生成 plan.json 并生图。
    """
    reset_session()
    project_name, project_dir = _resolve_project_dir(content_file, output_name)
    tpl_assets_dir = project_dir / "template_assets"
    tpl_assets_dir.mkdir(exist_ok=True)
    review_md_path = project_dir / REVIEW_MD_FILENAME

    print(f"\n🚀 Nano Banana 2 — Phase 1: Plan")
    print(f"📂 项目名称: {project_name}")
    print(f"📂 项目目录: {project_dir}")
    print(f"📄 内容源: {content_file}")
    print(f"🎨 模版源: {template_file or '无 (AI 自动设计)'}")
    print(f"🏷️ Logo 源: {logo_file or '未指定'}")
    if briefing:
        print(f"📝 用户意图 (Briefing): {briefing[:60]}{'...' if len(briefing) > 60 else ''}")

    api_key = os.getenv("OPENAI_API_KEY") or os.getenv("GOOGLE_API_KEY")
    api_base = os.getenv("OPENAI_API_BASE") or "https://generativelanguage.googleapis.com/v1beta/openai"
    if not api_key:
        print("❌ 错误: 请设置 OPENAI_API_KEY 或 GOOGLE_API_KEY 环境变量")
        return None

    narrative_agent = NarrativeAgent(api_key, api_base)
    visual_agent = VisualAgent(api_key, api_base)
    template_agent = TemplateAgent(api_key, api_base, output_dir=str(tpl_assets_dir))

    if not os.path.exists(content_file):
        print(f"❌ 错误: 内容文件不存在 {content_file}")
        return None

    with open(content_file, 'r', encoding='utf-8') as f:
        content_context = f.read()

    # Step 1: 自动推导
    print("\n🔍 [Step 1/4] 正在分析文档内容...")
    inferred = narrative_agent.analyze_content(content_context)
    logger.info(f"自动推导参数: {json.dumps(inferred, ensure_ascii=False)}")

    # Step 2: 解析模版
    template_info = None
    assets = {}
    if template_file and os.path.exists(template_file):
        print(f"\n🖼️ [Step 2/4] 正在解析模版文件...")
        try:
            template_info = template_agent.process_template(template_file)
            assets['template_file'] = template_file
            assets['logo_path'] = template_info.get('logo_path')
            assets['template_images'] = template_info.get('reference_images')
            logger.info("模版解析成功")
        except Exception as e:
            logger.error(f"模版解析失败: {e}")
    elif template_file:
        logger.warning(f"模版文件不存在: {template_file}，将使用 AI 自动设计")

    if logo_file and os.path.exists(logo_file):
        assets['logo_path'] = logo_file
        print(f"🏷️ 使用用户指定 Logo: {logo_file} (优先于模版截取)")
    elif logo_file:
        logger.warning(f"Logo 文件不存在: {logo_file}，将回退到模版截取")

    # Step 3: 生成叙事大纲
    print("\n📝 [Step 3/4] 正在构建叙事架构...")
    constraints = {
        "target_audience": inferred.get("target_audience", "通用受众"),
        "presentation_type": inferred.get("presentation_type", "商业演示"),
        "duration": inferred.get("duration", "15分钟"),
        "page_count": str(page_count) if page_count else "10",
        "style_preference": style_preference or inferred.get("style_preference", "专业商务"),
        "briefing": briefing,
    }
    narrative_outline = narrative_agent.generate_narrative_outline(content_context, constraints)
    print(f"✅ 叙事大纲生成完成，共 {len(narrative_outline)} 页")

    # Step 4: 生成人类可审阅的 plan_for_review.md（不生成 plan.json）
    print("\n🎨 [Step 4/4] 正在生成人类可审阅计划...")
    style_definition = visual_agent.define_style(constraints, assets, template_info)
    if isinstance(style_definition, tuple):
        _, style_config = style_definition
    else:
        style_config = {"description": str(style_definition), "palette": [], "mode": "ai_minting"}

    meta = {
        "project_name": project_name,
        "project_dir": str(project_dir),
        "content_file": content_file,
        "template_file": assets.get('template_file'),
        "logo_file": assets.get('logo_path'),
    }
    review_md_content = build_review_md(narrative_outline, style_config, meta)
    with open(review_md_path, "w", encoding='utf-8') as f:
        f.write(review_md_content)

    # 打印大纲摘要
    print(f"\n{'='*60}")
    print(f"📋 人类可审阅计划已保存: {review_md_path} ({len(narrative_outline)} 页)")
    print(f"{'='*60}")
    for p in narrative_outline:
        p_num = p['page_num']
        p_type = p.get('type', 'content')
        tc = p.get('text_content', {})
        title = tc.get('headline') or p.get('title', '')
        print(f"  P{p_num} [{p_type.upper():8s}] {title}")
    print(f"{'='*60}")
    print(f"\n⏸️  Phase 1 完成。")
    print(f"    【重要】请审阅 plan_for_review.md，确认无误后再运行 execute。")
    print(f"    请勿在同一轮对话中自动运行 execute——必须等待用户确认。")
    print(f"    确认后运行: execute \"{project_dir}\"")

    return str(review_md_path)


# ──────────────────────────────────────────────
#  Phase 2: Execute
# ──────────────────────────────────────────────

def _resolve_execute_input(path_arg: str) -> tuple:
    """解析 execute 输入，支持目录或文件。返回 (plan_path, project_dir, from_review_md)"""
    p = Path(path_arg)
    if not p.exists():
        return None, None, False
    if p.is_dir():
        review_md = p / REVIEW_MD_FILENAME
        plan_json = p / "plan.json"
        # 优先使用 plan_for_review.md（用户审阅确认的），确保生成内容与大纲一致
        if review_md.exists():
            return str(review_md), str(p), True
        if plan_json.exists():
            return str(plan_json), str(p), False
        print(f"❌ 目录中未找到 {REVIEW_MD_FILENAME} 或 plan.json")
        return None, None, False
    if p.suffix.lower() == ".md":
        return str(p), str(p.parent), True
    if p.suffix.lower() == ".json":
        return str(p), str(p.parent), False
    print("❌ 请传入 plan_for_review.md、plan.json 或项目目录")
    return None, None, False


def execute_from_plan(plan_input: str, output_name: str = None, resolution: str = "1K", slide_filter: list = None, reassemble_only: bool = False):
    """
    Phase 2: 读取已审阅的计划，执行图片生成并组装 PPTX。
    plan_input: 项目目录、plan_for_review.md 或 plan.json 路径
    """
    plan_path, proj_dir, from_review = _resolve_execute_input(plan_input)
    if not plan_path:
        return None

    if from_review:
        reset_session()
        print("\n📄 检测到人类审阅计划，正在解析并派生技术计划...")
        with open(plan_path, "r", encoding="utf-8") as f:
            md_text = f.read()
        parsed = parse_review_md(md_text)
        if not parsed.get("pages"):
            print("❌ 解析失败，未找到有效页面")
            return None
        pmeta = parsed.get("meta", {})
        content_file = pmeta.get("content_file", "")
        api_key = os.getenv("OPENAI_API_KEY") or os.getenv("GOOGLE_API_KEY")
        api_base = os.getenv("OPENAI_API_BASE")
        plan_data = derive_technical_plan(parsed, proj_dir, content_file, api_key=api_key, api_base=api_base)
        plan_json_path = Path(proj_dir) / "plan.json"
        with open(plan_json_path, "w", encoding="utf-8") as f:
            json.dump(plan_data, f, ensure_ascii=False, indent=2)
        print(f"✅ 技术计划已保存: {plan_json_path}")
        plan_path = str(plan_json_path)

    with open(plan_path, 'r', encoding='utf-8') as f:
        plan_data = json.load(f)

    if isinstance(plan_data, list):
        slides = plan_data
        meta = {}
    else:
        slides = plan_data.get("slides", plan_data)
        meta = plan_data.get("meta", {})

    name = output_name or meta.get("project_name") or Path(meta.get("content_file", "presentation")).stem
    project_dir = meta.get("project_dir") or proj_dir
    if not project_dir:
        from datetime import date
        date_prefix = date.today().strftime("%Y%m%d")
        dir_name = f"{date_prefix}_{name}"
        project_dir = str(Path("output") / "ppt" / dir_name)
    
    template_path = meta.get("template_file")

    print(f"\n⚡ Nano Banana 2 — Phase 2: Execute")
    print(f"📋 计划文件: {plan_path} ({len(slides)} 页)")
    print(f"📂 项目目录: {project_dir}")
    print(f"📦 输出名称: {name}")
    print(f"🖼️ 分辨率: {resolution or '1K'}")

    # 写一份纯 slides list 供 executor 读取
    exec_plan_file = str(Path(project_dir) / "_exec_slides.json")
    Path(project_dir).mkdir(parents=True, exist_ok=True)
    with open(exec_plan_file, "w", encoding='utf-8') as f:
        json.dump(slides, f, ensure_ascii=False, indent=2)

    out = execute_plan(
        exec_plan_file, name, template_path, project_dir=project_dir,
        resolution=resolution or "1K", slide_filter=slide_filter,
        reassemble_only=reassemble_only
    )

    if os.path.exists(exec_plan_file):
        os.remove(exec_plan_file)

    return out, project_dir


def _parse_slides_arg(s: str) -> list:
    """解析用户输入的页号，如 '3 5 7' 或 '3,5,7'"""
    if not s or not s.strip():
        return None
    nums = re.findall(r'\d+', s)
    return [int(n) for n in nums] if nums else None


def _interactive_rerun_prompt(plan_input: str, output_name: str, resolution: str, project_dir: str = None):
    """生成完成后，交互式询问是否需要重跑部分页面。rerun 使用 project_dir 以命中 plan.json"""
    if not sys.stdin.isatty():
        return
    print("\n" + "=" * 50)
    print("是否需要重跑部分页面？")
    print("  输入页号（如 3 5 7 或 3,5,7），直接回车跳过")
    print("=" * 50)
    try:
        user_input = input("> ").strip()
    except EOFError:
        return
    slides = _parse_slides_arg(user_input)
    if not slides:
        return
    rerun_input = project_dir or plan_input
    execute_from_plan(rerun_input, output_name, resolution=resolution, slide_filter=slides)
    _interactive_rerun_prompt(plan_input, output_name, resolution, project_dir=project_dir)


# ──────────────────────────────────────────────
#  Legacy: 一键全自动
# ──────────────────────────────────────────────

def auto_generate_ppt(content_file: str, template_file: str = None,
                      logo_file: str = None, output_name: str = None, resolution: str = "1K", page_count: int = None,
                      style_preference: str = None, briefing: str = None):
    """交互式终端下的一键全自动流程"""
    plan_file = generate_plan(content_file, template_file, logo_file, output_name, page_count=page_count, style_preference=style_preference, briefing=briefing)
    if not plan_file:
        return

    if sys.stdin.isatty():
        user_input = input("\n请确认是否继续执行生图？(Y/n): ").strip().lower()
        if user_input == 'n':
            print(f"❌ 用户取消。计划已保存在 '{plan_file}'，可稍后执行。")
            return
    else:
        print("\n⚠️ 非交互模式，自动继续执行...")

    resolution = (resolution or "1K").strip().upper()
    if resolution not in ("1K", "2K", "4K"):
        resolution = "1K"

    out_name = output_name or Path(plan_file).parent.name
    result = execute_from_plan(plan_file, out_name, resolution=resolution)
    out_path, proj_dir = result if isinstance(result, tuple) else (result, None)
    _interactive_rerun_prompt(plan_file, out_name, resolution, project_dir=proj_dir)


# ──────────────────────────────────────────────
#  CLI 入口
# ──────────────────────────────────────────────

def print_usage():
    print("""
Nano Banana 2 PPT Generator

用法:
  # Phase 1: 生成计划（停在生图前，供审阅）
  python -m nano_banana_ppt.main plan <content_file> [template_file] [logo_file] [output_name] [--pages N]

  # Phase 2: 执行计划（生图 + 组装 PPTX）
  # 可传入项目目录、plan_for_review.md 或 plan.json
  python -m nano_banana_ppt.main execute <项目目录或plan文件> [output_name] [--resolution 1K|2K|4K] [--slides 3 5 7] [--reassemble]

  # 一键全自动（交互式终端下可用）
  python -m nano_banana_ppt.main auto <content_file> [template_file] [logo_file] [output_name] [--resolution 1K|2K|4K]

参数:
  --pages       期望页数，如 --pages 15
  --style       风格偏好，如 --style "毕加索立体主义"
  --briefing    用户意图，如 --briefing "我最想传达的是：投资需警惕左尾风险"
  --resolution  分辨率，1K|2K|4K，默认 1K
  --slides      仅重跑指定页号，如 --slides 3 5 7
  --reassemble  仅从已有 slides 重新组装 PPTX，不生成新图（用于修复布局问题）

交互:
  执行完成后（交互式终端），可输入页号（如 3 5 7）重跑部分页面，直接回车跳过。

目录结构:
  output/ppt/{date}_{name}/
    {date}_{name}.pptx               ← 最终交付的 PPTX
    plan_for_review.md               ← 人类可审阅计划
    plan.json                        ← 技术计划
    template_assets/                 ← 模版提取物
    slides/                          ← 生成的页面图片
""")


def _parse_cli_args(args):
    """解析 CLI 参数，提取 --resolution、--slides、--pages、--style、--briefing、--reassemble"""
    rest = []
    resolution = None
    slides = None
    pages = None
    style = None
    briefing = None
    reassemble = False
    i = 0
    while i < len(args):
        a = args[i]
        if a == "--pages" and i + 1 < len(args):
            try:
                pages = int(args[i + 1])
            except ValueError:
                pages = None
            i += 2
        elif a == "--style" and i + 1 < len(args):
            style = args[i + 1]
            i += 2
        elif a == "--briefing" and i + 1 < len(args):
            briefing = args[i + 1]
            i += 2
        elif a == "--resolution" and i + 1 < len(args):
            resolution = args[i + 1]
            i += 2
        elif a == "--reassemble":
            reassemble = True
            i += 1
        elif a == "--slides":
            i += 1
            nums = []
            while i < len(args) and args[i].isdigit():
                nums.append(int(args[i]))
                i += 1
            slides = nums if nums else None
        else:
            rest.append(a)
            i += 1
    return rest, resolution, slides, pages, style, briefing, reassemble


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print_usage()
        sys.exit(1)

    rest, resolution, slides, pages, style, briefing, reassemble = _parse_cli_args(sys.argv[1:])
    command = rest[0].lower() if rest else ""

    if command == "plan":
        if len(rest) < 2:
            print("❌ 缺少 content_file 参数")
            sys.exit(1)
        content = rest[1]
        template = rest[2] if len(rest) > 2 else None
        logo = rest[3] if len(rest) > 3 else None
        out_name = rest[4] if len(rest) > 4 else None
        generate_plan(content, template, logo, out_name, page_count=pages, style_preference=style, briefing=briefing)

    elif command == "execute":
        if len(rest) < 2:
            print("❌ 缺少 plan_file 或项目目录参数")
            sys.exit(1)
        pf = rest[1]
        on = rest[2] if len(rest) > 2 else None
        result = execute_from_plan(pf, on, resolution=resolution, slide_filter=slides, reassemble_only=reassemble)
        if result and sys.stdin.isatty():
            _, proj_dir = result if isinstance(result, tuple) else (None, None)
            _interactive_rerun_prompt(pf, on or Path(pf).parent.name, resolution or "1K", project_dir=proj_dir)

    elif command == "auto":
        content = rest[1] if len(rest) > 1 else None
        if not content:
            print("❌ 缺少 content_file 参数")
            sys.exit(1)
        template = rest[2] if len(rest) > 2 else None
        logo = rest[3] if len(rest) > 3 else None
        output = rest[4] if len(rest) > 4 else None
        auto_generate_ppt(content, template, logo, output, resolution=resolution, page_count=pages, style_preference=style, briefing=briefing)

    else:
        print(f"❌ 未知命令: {command}")
        print_usage()
        sys.exit(1)
