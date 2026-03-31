# Two-Step Narrative Generation for Nano Banana PPT

## Overview
The current `NarrativeAgent.generate_narrative_outline` processes long texts (up to 50k characters) and directly outputs a complex 10-15 page JSON structure. This single-pass approach often results in a loss of logical coherence and core focus, making the final presentation feel disjointed, especially for long-form content like articles or course outlines.

This design introduces a two-step pipeline to extract a strong narrative skeleton before generating the final slide-by-slide JSON, mimicking the effective summarization techniques seen in tools like NotebookLM.

## Goals
- Improve the logical flow and narrative structure of generated PPTs.
- Ensure key takeaways, data points, and quotes from the original text are highlighted.
- Better handle long-form, unstructured, or multi-source inputs.

## Two-Step Pipeline Design

### Step 1: Extract Core Narrative Skeleton (`_extract_core_logic`)
Before generating slides, the agent will analyze the source text to build a robust structural foundation.
- **Input**: Raw text context (up to 50k chars).
- **Prompt Objective**: Extract the "Sense-making" skeleton.
- **Output Format**: Markdown text containing:
  1.  **Core Thesis**: A single sentence summarizing the overarching message.
  2.  **Context & Problem**: The background setting and the core pain point or reason for the presentation.
  3.  **Logical Pillars**: 3-5 distinct structural sections (e.g., What -> Why -> How -> Case Study -> Conclusion).
  4.  **Key Takeaways & Data**: Crucial quotes, statistics, or conclusions that *must* be included in the final deck.

### Step 2: Pagination & Formatting (Modified `generate_narrative_outline`)
The existing JSON generation step will be updated to utilize the skeleton from Step 1.
- **Inputs**: Raw text context + The Narrative Skeleton (from Step 1) + User Constraints.
- **Prompt Objective**: Map the source material onto the logical skeleton to create individual slides.
- **New Instructions**:
  - Strongly adhere to the "Logical Pillars" for dividing sections.
  - Ensure the "Core Thesis" is reflected in the opening.
  - Actively prioritize turning "Key Takeaways & Data" into `hero` or `data` slide types.
  - Maintain the existing strict JSON schema.

## Implementation Details
- **File**: `tools/nano_banana_ppt/agents/narrative.py`
- **Class**: `NarrativeAgent`
- **Add Method**: `def _extract_core_logic(self, content_context: str, constraints: Dict) -> str:`
  - Uses `chat_completion_with_fallback`.
  - Prompts for the Markdown skeleton.
- **Update Method**: `def generate_narrative_outline(self, content_context: str, constraints: Dict) -> List[Dict]:`
  - First calls `_extract_core_logic`.
  - Injects the resulting skeleton string into the main prompt under a new `【核心叙事逻辑】` (Core Narrative Logic) section.
  - Adjusts the main prompt to enforce alignment with the provided skeleton.

## Edge Cases & Considerations
- **Extremely short text**: The two-step process might be slight overkill, but standardizing the pipeline ensures consistency. The skeleton extraction will just be very concise.
- **Token Limits**: Step 1 adds another LLM call with the full context. This increases token usage (and cost/latency) slightly, but the logic improvement is worth the trade-off.
- **Model Choice**: `gemini-3-pro-preview` is used for both steps as it requires strong reasoning capabilities to build the skeleton.
