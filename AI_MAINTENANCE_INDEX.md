# AI Maintenance Index - Nano Banana PPT

> Optimized for AI parsing and quick code location
> Last updated: 2026-03-15 (Added structured outline detection)

---

## RECENT CHANGES

### 2026-03-15: Structured Outline Detection
- **Feature**: Auto-detect if user provided structured outline (e.g., "Slide 3: Title")
- **Files Modified**: `agents/narrative.py`
- **New Functions**:
  - `detect_structured_outline()` - Detects if input has page markers
  - `_parse_structured_outline()` - Parses structured outline preserving original titles
- **Behavior**:
  - If structured outline detected → Parse mode (preserves titles, saves tokens)
  - If unstructured content → Narrative mode (LLM rewrites titles)
- **Token Savings**: ~50-70% for structured outlines

---

## FUNCTION MAP: Feature → File → Function → Line Range

### Content Generation

```yaml
feature: "modify_outline_generation"
file: "agents/narrative.py"
class: "NarrativeAgent"
method: "generate_narrative_outline()"
returns: "List[Dict]"
dependencies: ["utils/llm_client.py:generate_text()"]
saves_to: "_content_state.json"
notes: "Now supports two modes: parse mode (structured) and narrative mode (unstructured)"
```

```yaml
feature: "detect_structured_outline"
file: "agents/narrative.py"
class: "NarrativeAgent"
method: "detect_structured_outline()"
line_range: "24-42"
search_keys: ["Slide\\s+\\d+", "第\\s*\\d+\\s*页"]
returns: "bool"
notes: "Static method, uses regex to detect page markers"
```

```yaml
feature: "parse_structured_outline"
file: "agents/narrative.py"
class: "NarrativeAgent"
method: "_parse_structured_outline()"
line_range: "196-323"
search_keys: ["解析模式", "保留原文标题"]
returns: "List[Dict] or None"
notes: "Preserves user's original titles, minimal LLM usage"
```

### Visual Style & Colors

```yaml
feature: "modify_color_palette"
file: "agents/style_library.py"
target: "STYLE_PRESETS dict"
search_key: "palette"
dependencies: []
affects: ["agents/visual.py:VisualAgent.generate_visual_plan()"]
```

```yaml
feature: "modify_image_generation_prompt"
file: "agents/visual.py"
class: "VisualAgent"
method: "generate_visual_plan()"
search_keys: ["DESIGN MANIFESTO", "Style:", "visual_prompt"]
dependencies: ["utils/llm_client.py:generate_image()"]
```

```yaml
feature: "modify_layout_logic"
file: "core/generator.py"
function: "_determine_layout()"
search_keys: ["centered_headline", "process_flow", "bento_grid"]
dependencies: []
affects: ["core/generator.py:create_slide()"]
```

### Content Generation

```yaml
feature: "modify_outline_generation"
file: "agents/narrative.py"
class: "NarrativeAgent"
method: "generate_narrative_outline()"
returns: "List[Dict]"
dependencies: ["utils/llm_client.py:generate_text()"]
saves_to: "_content_state.json"
```

```yaml
feature: "modify_page_type_logic"
file: "agents/narrative.py"
search_keys: ["page_type", "cover", "section", "content", "quote"]
related_function: "generate_narrative_outline()"
```

### Image Processing

```yaml
feature: "modify_image_api_call"
file: "utils/llm_client.py"
function: "generate_image()"
api: "Gemini"
search_keys: ["imagen-3.0-generate-002", "generateContent"]
error_handling: "retry logic with exponential backoff"
```

```yaml
feature: "modify_image_selection_logic"
file: "core/image_selector.py"
class: "ImageSelector"
method: "select_best_image()"
criteria: ["composition", "text_readability", "color_harmony"]
```

```yaml
feature: "modify_native_image_blend"
file: "core/executor.py"
search_key: "blend_pass"
related_field: "native_image_path in master_plan.md"
dependencies: ["utils/llm_client.py:generate_image()"]
```

### Execution Flow

```yaml
feature: "modify_cli_arguments"
file: "main.py"
search_key: "argparse"
arguments: ["--pages", "--style", "--slides", "--regenerate", "--reassemble"]
```

```yaml
feature: "modify_execution_pipeline"
file: "core/executor.py"
function: "execute_plan()"
flow: ["load plan.json", "generate images", "blend pass", "assemble pptx"]
```

### Logo & Branding

```yaml
feature: "modify_logo_position"
file: "core/generator.py"
search_key: "add_logo"
parameters: ["left", "top", "width", "height"]
units: "Inches"
command_to_test: "execute --reassemble"
```

---

## FILE DEPENDENCY GRAPH

```
main.py
├─→ agents/narrative.py (NarrativeAgent)
│   └─→ utils/llm_client.py (generate_text)
├─→ agents/visual.py (VisualAgent)
│   ├─→ agents/style_library.py (STYLE_PRESETS)
│   └─→ utils/llm_client.py (generate_text)
├─→ core/executor.py (execute_plan)
    ├─→ utils/llm_client.py (generate_image)
    ├─→ core/image_selector.py (ImageSelector)
    └─→ core/generator.py (PPTXGenerator)
        ├─→ core/data_visualizer.py (create_chart)
        └─→ utils/image_utils.py (process_image)
```

---

## DATA FLOW

```
User Input (markdown/text)
  ↓
[plan-content] agents/narrative.py
  ↓ saves
_content_state.json + content_plan.md
  ↓
[plan-visual] agents/visual.py
  ↓ saves
master_plan.md (with visual_suggestion per slide)
  ↓
[execute/prototype] core/executor.py
  ↓ generates (if not exists)
plan.json (with visual_prompt per slide)
  ↓ calls
utils/llm_client.py → Gemini API
  ↓ saves
slides/slide_XX.png
  ↓ assembles
core/generator.py → .pptx file
```

---

## KEY FILES QUICK REFERENCE


| File                      | Primary Responsibility           | Key Classes/Functions                                 | Read Priority                        |
| ------------------------- | -------------------------------- | ----------------------------------------------------- | ------------------------------------ |
| `main.py`                 | CLI entry point                  | `argparse`, command routing                           | LOW (only for CLI changes)           |
| `agents/narrative.py`     | Content outline generation       | `NarrativeAgent.generate_narrative_outline()`         | HIGH (content logic)                 |
| `agents/visual.py`        | Visual prompt generation         | `VisualAgent.generate_visual_plan()`                  | HIGH (image style)                   |
| `agents/style_library.py` | Preset styles storage            | `STYLE_PRESETS` dict                                  | MEDIUM (color/font presets)          |
| `core/executor.py`        | Orchestration & image generation | `execute_plan()`, `blend_pass()`                      | HIGH (pipeline control)              |
| `core/generator.py`       | PPTX assembly                    | `PPTXGenerator.create_slide()`, `_determine_layout()` | HIGH (layout & text)                 |
| `core/image_selector.py`  | Image quality evaluation         | `ImageSelector.select_best_image()`                   | LOW (unless image selection issues)  |
| `utils/llm_client.py`     | API calls                        | `generate_text()`, `generate_image()`                 | MEDIUM (API changes)                 |
| `utils/image_utils.py`    | Image processing                 | `resize_image()`, `crop_image()`                      | LOW (unless image processing issues) |


---

## COMMON MODIFICATION PATTERNS

### Pattern 1: Change Color Scheme

```
1. READ: agents/style_library.py
2. LOCATE: STYLE_PRESETS["{style_name}"]["palette"]
3. EDIT: color hex codes
4. TEST: python3 -m tools.nano_banana_ppt.main plan-visual <project> --style {style_name}
```

### Pattern 2: Modify Image Generation Style

```
1. READ: agents/visual.py (lines ~100-200, VisualAgent class)
2. LOCATE: prompt template in generate_visual_plan()
3. EDIT: DESIGN MANIFESTO or Style: section
4. TEST: python3 -m tools.nano_banana_ppt.main execute <project> --regenerate
```

### Pattern 3: Adjust Layout Logic

```
1. READ: core/generator.py
2. LOCATE: _determine_layout() function
3. EDIT: conditional logic (if/elif blocks)
4. TEST: python3 -m tools.nano_banana_ppt.main execute <project> --reassemble
```

### Pattern 4: Fix Logo Position

```
1. READ: core/generator.py
2. SEARCH: "add_logo"
3. EDIT: left/top/width/height values (in Inches)
4. TEST: python3 -m tools.nano_banana_ppt.main execute <project> --reassemble
```

---

## CRITICAL VARIABLES & CONSTANTS

### In agents/visual.py

- `DESIGN_MANIFESTO`: Core visual principles injected into every prompt
- `visual_prompt`: Final prompt sent to Gemini API

### In core/generator.py

- `SLIDE_WIDTH = Inches(10)`: Standard slide dimensions
- `SLIDE_HEIGHT = Inches(5.625)`: 16:9 aspect ratio
- Layout types: `centered_headline`, `process_flow`, `bento_grid`, `three_column_grid`, `left_text_right_visual`, `top_visual_bottom_text`

### In core/executor.py

- `plan.json`: Technical execution plan with visual_prompt per slide
- `master_plan.md`: User-facing blueprint with Chinese visual descriptions
- `--regenerate`: Flag to force regeneration of plan.json
- `--reassemble`: Flag to skip image generation, only reassemble PPTX

---

## ERROR HANDLING LOCATIONS

### Image Generation Failures

- **File**: `utils/llm_client.py`
- **Function**: `generate_image()`
- **Logic**: Retry 5 times with exponential backoff
- **Fallback**: Returns None, executor skips that slide

### API Rate Limiting

- **File**: `core/executor.py`
- **Symptom**: Gray slides in output
- **Solution**: Use `--slides N M` to regenerate specific slides

### Missing Native Images

- **File**: `core/executor.py`
- **Check**: `blend_pass()` validates file existence
- **Fallback**: Skips blend, uses generated background only

---

## MODIFICATION SAFETY RULES

1. **Never modify** `_content_state.json` manually (auto-generated)
2. **Always backup** `plan.json` before `--regenerate`
3. **Test with `prototype**` before full `execute`
4. **Use `--reassemble**` for layout/text changes (skips image generation)
5. **Check git diff** before committing changes

---

## TOKEN OPTIMIZATION STRATEGY FOR AI

When user requests modification:

1. **Ask for specific feature** (use FUNCTION MAP above)
2. **Read ONLY the target file** (check "file" field in YAML)
3. **Search for specific keys** (use "search_key" or "search_keys")
4. **Check dependencies** (read "dependencies" files only if needed)
5. **Provide line-specific edits** (use Edit tool with exact old_string)

**Example efficient workflow:**

```
User: "我想改配色"
AI: [Reads AI_MAINTENANCE_INDEX.md → finds "modify_color_palette"]
AI: [Reads ONLY agents/style_library.py]
AI: [Locates STYLE_PRESETS dict]
AI: [Proposes specific edit with line numbers]
```

**Avoid:**

- Reading entire codebase
- Reading files not in dependency chain
- Proposing changes without reading target file first

---

## QUICK COMMAND REFERENCE

```bash
# Content planning (2 LLM calls)
python3 -m tools.nano_banana_ppt.main plan-content <file> [--pages N]

# Visual planning (1-2 LLM calls)
python3 -m tools.nano_banana_ppt.main plan-visual <project> [--style NAME]

# Prototype (auto-select 2-3 slides)
python3 -m tools.nano_banana_ppt.main prototype <project>

# Full execution
python3 -m tools.nano_banana_ppt.main execute <project>

# Regenerate after editing master_plan.md
python3 -m tools.nano_banana_ppt.main execute <project> --regenerate

# Reassemble without regenerating images
python3 -m tools.nano_banana_ppt.main execute <project> --reassemble

# Regenerate specific slides
python3 -m tools.nano_banana_ppt.main execute <project> --slides 1 5 8
```