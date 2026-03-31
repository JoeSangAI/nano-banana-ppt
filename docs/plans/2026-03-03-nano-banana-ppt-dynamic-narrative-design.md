# Nano Banana PPT: Dynamic Narrative Density Design

## Overview
The current PPT generation forces a rigid "bullet point" style (e.g., "Keyword: Short description") for almost every page, which makes the presentation feel mechanical and interrupts complete thoughts or storytelling. 

The goal is to allow the AI to dynamically adjust the narrative density based on the content—sometimes using a few bullets, sometimes a full evocative paragraph, sometimes a single word, or just an image.

## Approach
Combine relaxed prompt constraints (Approach 1) with specific narrative format guidance (Approach 2).

### 1. Update NarrativeAgent Prompt (`tools/nano_banana_ppt/agents/narrative.py`)
- **Relax Length Constraints**: Remove the strict "10-30 words" limit for all bullets.
- **Dynamic Content Formatting**: Explicitly instruct the AI to use different formats based on the page's role:
  - Structured points (bullets) for facts/data.
  - Medium/long paragraphs (`paragraph`) for stories, complete thoughts, or historical context.
  - Single evocative sentences or words for high-impact pages.
  - Zero text (empty body) if a visual speaks for itself.
- **Prompt Phrasing**: Add instructions like "因地制宜：对 ppt 的叙事，有些时候是几点，有些时候是一句很有韵味的话，有些时候可能要讲个故事，有些时候可能一个词足矣，甚至有些时候，一个字都不要，只要放一幅画就可以了。不要机械地全部使用 'XXX：XXXX' 的短句分点结构。"

### 2. Update SKILL.md (`.cursor/skills/nano-banana-ppt/SKILL.md`)
- **Narrative Principles**: Emphasize dynamic text density in the "叙事与版面设计原则" section.
- Explicitly mention that not all pages need to be lists; stories, full sentences, and visual-only pages are encouraged where appropriate.

## Success Criteria
- The generated `plan_for_review.md` shows a natural mix of formats.
- The AI correctly chooses when to use paragraphs vs bullets vs minimal text based on the narrative flow.
