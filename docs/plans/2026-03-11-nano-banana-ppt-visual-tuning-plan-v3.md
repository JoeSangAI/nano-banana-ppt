# Nano Banana PPT Fixes: Visual Tuning & Layout Loosening

## Context & Problem Statement
After fixing the body text bug, the generated presentation (V3) successfully included all text. However, the user observed that the visual output felt extremely rigid, described as "forcing text into pre-existing glassmorphism boxes." The original magic of Nano Banana 2—where the layout organically adapted to the semantic meaning of the text—was lost.

The user prefers to give Nano Banana 2 more freedom to use its native semantic layout capabilities, while only strictly enforcing:
1. **Style alignment** (matching user intent)
2. **Color palette consistency** (matching target brand/theme colors)

## Root Cause Analysis
1. **Rigid Layout Assignment**: The `VisualAgent._assign_layout` method contained hardcoded logic that forced text into rigid structures (e.g., `bento_grid` if `len(body) >= 4`, `three_column_grid` if `len(body) == 3`). This overrode the semantic page types (`flowchart`, `comparison`, etc.) determined by the Narrative Agent.
2. **Overbearing Prompt Directives**: The prompt generation explicitly stated: *"The Global Style ALWAYS OVERRIDES the stylistic implications of the Initial Visual Suggestion."* This discouraged the AI from drawing unique metaphorical structures (like funnels, pyramids, or organic flows) if they didn't explicitly match the strict "shape language" of the global style.
3. **Template/Layout Straightjacket**: The prompt included explicit layout instructions like `Assigned layout for this page: bento_grid — Asymmetrical Bento Grid...` which forced the AI into drawing specific box types regardless of the content.

## Proposed Solutions (The Plan)

### 1. Remove the "Bullet-Counting" Layout Trap
- **Action**: In `VisualAgent._assign_layout`, delete the `elif len(body)...` conditions that hardcode layouts based on text item counts.
- **Why**: This stops the system from forcing a `bento_grid` just because a page has 4 bullet points, allowing the `page_type` (like `flowchart` or `framework`) to dictate the conceptual structure.

### 2. Soften the "Global Style Override" Clause
- **Action**: Rewrite the `STYLE ADAPTATION RULE` in the prompt.
- **New Logic**: Instruct the AI to *blend* the global style (colors, textures, lighting) with the *specific semantic layout* required by the page content.
- **Draft Prompt**:
  ```text
  【STYLE & SEMANTIC ADAPTATION RULE】
  You MUST apply the Global Style (especially the exact Color Palette and lighting/texture) to the scene. 
  HOWEVER, the layout and structural metaphor MUST adapt to the specific content. 
  If the Initial Visual Suggestion asks for a "flywheel" or "comparison split", you must draw that specific structure, but render it using the textures, colors, and mood of the Global Style.
  Allow the text to shape the layout organically rather than forcing it into rigid boxes.
  ```

### 3. Emphasize Color and Typography over Rigid Geometry
- **Action**: Adjust `_get_page_type_specific_instruction` to remove rigid instructions like "Use a Bento Grid" or "split into 1/3 and 2/3". 
- **New Logic**: Use semantic guidance. "Design an organic layout that naturally guides the eye through the steps", "Create a dynamic split that contrasts two ideas", etc.

### 4. Provide Nano Banana with Layout Freedom
- **Action**: Change the layout string passed to the prompt. Instead of a highly specific architectural mandate, provide the semantic layout goal.

## Execution Strategy
I will update `tools/nano_banana_ppt/agents/visual.py` to implement these loosened constraints, preserving the color and font extraction while handing layout authority back to the core Nano Banana 2 prompt.