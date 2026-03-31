# Nano Banana Pic: AI Image Text Extraction and Replacement Feature Design

## 1. Overview
The goal of this feature is to add an interactive text editing layer to the image generation process within the `nano-banana-pic` tool. It solves a core user pain point: when an AI generates a great poster or image but gets the text wrong (e.g., spelling errors, formatting issues, or hallucinations), the user should be able to simply correct the text without losing the original image's composition, style, and specifically provided input assets (like guest avatars).

This design acts similar to a "Smart Text Layer" for AI-generated images, where the user edits a Markdown file containing the text, and the AI redraws the image based on the original structure and provided reference assets.

## 2. Core Workflow & Components

The feature will be implemented by adding two new independent scripts to the `tools/nano_banana_pic/` directory:

### Component A: Text Extraction (`extract_text.py`)
**Purpose**: To extract textual content from an already generated image and package it alongside the original generation metadata (prompts, reference images) into a user-editable Markdown file.

**Inputs**:
- `--image`: The path to the generated image (e.g., `output/images/OpenClaw_Live_Poster_1.png`).
- `--original-prompt` (Optional): The original prompt used to generate the image.
- `--reference-images` (Optional): The original input assets used (e.g., avatar images).

**Process**:
1. Call the Gemini multimodal model (e.g., `gemini-1.5-pro` or similar vision model) to perform OCR and layout understanding on the provided image.
2. Structure the extracted text logically (e.g., Main Title, Subtitle, Guest Info, Time/Location).
3. Generate a Markdown (`.md`) file with the exact same base name as the image.

**Output Structure (`Poster_1.md`)**:
```markdown
---
base_image: "output/images/Poster_1.png"
original_prompt: "A 3:4 vertical live stream event poster..."
reference_images:
  - "/Users/Joe_1/.../avatar_1.png"
  - "/Users/Joe_1/.../avatar_2.png"
---
# Image Text Content (Edit the text below)

[Main Title]
养虾夜话

[Subtitle]
人人值得拥有自己的一群agent！

[Guest Information]
吴畏：非凡产研创始人 & CEO
宁辽原：深耕 AI 与协作平台...
```
*Note: The YAML frontmatter safely stores the crucial context needed for the redraw phase without cluttering the user's editing space.*

### Component B: Image Text Replacement (`replace_text.py`)
**Purpose**: To take the user-edited Markdown file and use it to drive a highly-constrained "image-to-image" edit generation, forcing the model to update the text while anchoring tightly to the original image and reference assets.

**Inputs**:
- `--md-file`: The path to the edited Markdown file (e.g., `output/images/Poster_1.md`).
- `--resolution` (Optional): Output resolution (default: 2K or 4K).

**Process**:
1. **Parse Markdown**: Read the `.md` file to extract:
   - The user's updated text content.
   - The `base_image` path.
   - The `original_prompt`.
   - The `reference_images` paths.
2. **Construct Constraint Prompt**: Build a strict editing prompt.
   *Example*: "Edit the provided base image. You MUST keep the overall layout, style, background, and visual elements exactly as they are in the base image. You MUST use the provided reference images exactly as they are for the character avatars. ONLY change the text content to exactly match the following:\n\n[User's Updated Text]"
3. **Execute Generation**: Call the Gemini API (multimodal generation) passing:
   - The strong constraint prompt.
   - The `base_image` (as an Image object).
   - All `reference_images` (as Image objects).
4. **Save Output**: Save the newly generated image with a modified filename (e.g., `Poster_1_text_edited.png`).

## 3. Key Technical Considerations

- **Model Selection**: For `extract_text.py`, a strong vision model like `gemini-1.5-pro` is required for accurate OCR and layout comprehension. For `replace_text.py`, we will leverage the same generation model logic used in the main tool, relying on multi-image inputs (base + references) and strong prompting.
- **Handling Metadata**: By storing the `base_image`, `original_prompt`, and `reference_images` in the Markdown frontmatter, we achieve a stateless, decoupled workflow. The user only interacts with the text.
- **Tolerance for Minor Variations**: As discussed, while the model is instructed to keep the base image identical, minor artifacts or shifts in the background (e.g., the shape of an abstract shrimp) are acceptable, provided the core text is updated and the strictly referenced assets (avatars) are preserved.
- **Dependency Reuse**: These scripts will reuse the existing API authentication and GenAI client setup already present in `generate_image.py`.

## 4. User Experience Journey
1. User generates a poster using `generate_image.py` with 2 avatar reference images.
2. User notices a typo in the generated text.
3. User runs: `python3 tools/nano_banana_pic/extract_text.py --image Poster_1.png --reference-images avatar1.png avatar2.png`
4. Tool creates `Poster_1.md`.
5. User opens `Poster_1.md`, fixes the typo, and saves the file.
6. User runs: `python3 tools/nano_banana_pic/replace_text.py --md-file Poster_1.md`
7. Tool outputs `Poster_1_text_edited.png` with the corrected text, identical avatars, and nearly identical background.
