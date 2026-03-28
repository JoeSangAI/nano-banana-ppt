# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Nano Banana PPT is a multi-agent pipeline that converts documents (Markdown, PDF, text) into professional PowerPoint presentations using Google Gemini (via OpenAI-compatible API). It is designed to be invoked as a Skill from AI agents (Cursor, Claude Code).

## Environment Setup

Install dependencies:
```bash
pip install openai python-pptx pillow pymupdf requests python-dotenv matplotlib
```

Configure API keys in `.env` (auto-discovered at project root or `~/.cursor/skills/nano-banana-ppt/.env`):
```
OPENAI_API_KEY=sk-...
OPENAI_API_BASE=https://your-proxy/v1
```
`GOOGLE_API_KEY` is also accepted as a fallback for `OPENAI_API_KEY`.

## CLI Commands

**main.py 自动处理所有路径问题** — 无需关心工作目录或模块路径，任意位置均可直接运行。

```bash
# 从任意目录直接运行（推荐）
python3 /Users/Joe_1/Desktop/nano-banana-ppt/main.py <command> ...

# 或通过 skills 目录运行
cd ~/.claude/skills/nano-banana-ppt && python3 main.py <command> ...

# 从 Desktop 使用模块方式运行
cd /Users/Joe_1/Desktop && python3 -m tools.nano_banana_ppt.main <command> ...

```bash
# Phase 1a: Generate content outline (saves content_plan.md)
python3 -m tools.nano_banana_ppt.main plan-content <content_file> [template_file] [logo_file] [output_name] [--pages N]

# Phase 1b: Generate visual plan (saves visual_plan.md / master_plan.md)
python3 -m tools.nano_banana_ppt.main plan-visual <project_dir> [--style <style_name>]

# Phase 1 shortcut (runs both 1a + 1b):
python3 -m tools.nano_banana_ppt.main plan <content_file> [template_file] [logo_file] [output_name] [--style <style_name>] [--pages N]

# Optional: text-only prototype PPTX (no image generation)
python3 -m tools.nano_banana_ppt.main prototype <project_dir_or_plan_md> [output_name] [--slides 1 2]

# Phase 2: Generate images + assemble PPTX
python3 -m tools.nano_banana_ppt.main execute <project_dir_or_plan_md> [output_name] [--resolution 1K|2K|4K] [--slides 3 5 7]

# Upscale existing slides
python3 -m tools.nano_banana_ppt.main upscale <project_dir> [--resolution 4K] [--slides 1 3 5]

# Legacy one-shot (non-interactive)
python3 -m tools.nano_banana_ppt.main auto <content_file> [template_file] [logo_file] [output_name]
```

## Running Tests

```bash
# Run all tests
pytest tests/

# Run a single test file
pytest tests/test_llm_client.py -v

# Run a specific test
pytest tests/test_image_selector_logic.py::test_name -v
```

Tests import from `tools.nano_banana_ppt.*`, so run pytest from the Desktop directory (which has the `tools/` symlink):

```bash
cd /Users/Joe_1/Desktop && pytest tests/
```

## Architecture

```
nano-banana-ppt/
  main.py              # CLI entry point; orchestrates all phases
  agents/
    narrative.py       # NarrativeAgent: content → structured slide outline (JSON)
    visual.py          # VisualAgent: outline → visual prompts + style definition
    visual_flash.py    # Lighter/faster variant of VisualAgent
    template.py        # TemplateAgent: PDF/PPTX → extracted style + reference images
    style_library.py   # 12 curated style presets (claude_minimalist, apple_keynote, etc.)
  core/
    executor.py        # execute_plan(): orchestrates parallel image generation
    generator.py       # PPTGenerator: calls Gemini image API, assembles PPTX via python-pptx
    image_selector.py  # ImageSelector: VLM-based image quality/relevance filtering
    data_visualizer.py # render_chart_image(): Matplotlib chart rendering (bar/line/pie)
  utils/
    llm_client.py      # chat_completion_with_fallback(): model fallback chain (429/503 handling)
    review_plan.py     # parse/build master_plan.md ↔ plan.json conversion
    regenerate.py      # Partial slide regeneration helpers
    image_utils.py     # Image download, WebP conversion, aspect-ratio utilities
    analyzer.py        # Content analysis helpers
```

### Data Flow

1. `plan-content`: `NarrativeAgent` reads source doc → produces `content_plan.md` (human-readable outline with speaker notes)
2. `plan-visual`: `VisualAgent` + `TemplateAgent` read `content_plan.md` → produce `visual_plan.md` / `master_plan.md` (Art Director manifesto + per-slide visual descriptions)
3. **Human review gate** — agent MUST stop and show the plan to the user before proceeding
4. `execute`: `review_plan.py` parses `visual_plan.md` → derives `plan.json` (with `visual_prompt` per slide) → `executor.py` generates images in parallel (max 2 workers) → `generator.py` assembles final `.pptx`

### Key Design Patterns

- **Auto-bootstrap**: `main.py` automatically resolves its own location and sets up the correct `sys.path` / `tools/` structure, regardless of where it is invoked from.
- **API client**: All agents use `openai.OpenAI` pointed at a Gemini-compatible endpoint. Image generation uses the native Gemini REST API (not OpenAI images).
- **Model fallback**: `utils/llm_client.py` maintains a session-scoped set of 429-exhausted models and falls back through `MODEL_FALLBACK_CHAIN` automatically.
- **Seed-then-parallel execution**: `executor.py` first generates "seed" slides (first of each type: `content`, `section`, `hero`) serially to establish visual consistency masters, then generates remaining slides in parallel using those masters as `reference_images`.
- **All-Blend architecture**: Native images from source documents are never hard-overlaid; they are passed as `reference_images` to Gemini with a redraw prompt for seamless integration.
- **Output structure**: All artifacts land in `~/Desktop/AI output/ppt/{YYYYMMDD}_{project_name}/`.

### Available Style Presets (`--style`)

31 styles across 8 categories. Key ones:
`blackboard`, `whiteboard`, `sketch_note`, `blueprint`, `exploded_view`, `minimal_data`, `terminal_tech`, `swiss_design`, `academic_paper`, `claude_minimalist`, `apple_keynote`, `liquid_glass`, `dark_luxury`, `executive_dashboard`, `strategic_infographic`, `sharp_minimalism`, `soft_3d_clay`, `corporate_memphis`, `paper_craft`, `magazine_editorial`, `yellow_black_editorial`, `modern_newspaper`, `black_orange_creative`, `neo_brutalism`, `holographic_chrome`, `cyberpunk`, `manga_narrative`, `sports_energy`, `digital_neo_pop`, `pink_street_style`, `japanese_aesthetic`, `traditional_chinese`, `royal_blue_red_watercolor`, `deformed_flat_persona`, `studio_mockup_premium`, `classic_pop_sculpture_vaporwave`, `tech_art_neon`, `mincho_handwritten_mix`
