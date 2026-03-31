# Nano Banana PPT Refinement Design

## 1. Native Image Validation (VLM/OCR)
- **Problem**: The system previously blindly trusted that any image found in the source document was relevant, leading to QR codes or unrelated course posters being included.
- **Solution**: Implement a multimodal image validation step in `NarrativeAgent`. 
  - For each extracted local image, we will encode it in base64 and send it to `gemini-3.1-pro-preview` along with a prompt to analyze it.
  - The VLM will determine if the image is a QR code, an advertisement, or unrelated filler, and reject it. If it is relevant (e.g., data chart, news screenshot, relevant diagram), the VLM will provide a short semantic description.
  - Only validated images and their VLM-generated descriptions will be passed to the main narrative generation prompt.

## 2. Language Drift Prevention
- **Problem**: The model occasionally drifts into English due to temperature randomness, even when the source and context are in Chinese.
- **Solution**: 
  - We will not forcefully hardcode "MUST BE IN SIMPLIFIED CHINESE" because we want to support other languages and English quotes.
  - Instead, we will add a dynamic instruction in the `generate_narrative_outline` system prompt: "Ensure the output language matches the primary language of the source document and the target audience. Do not randomly switch languages unless it is for a specific quote, terminology, or explicitly requested."

## 3. Breaking the Bullet-Point Habit
- **Problem**: The model defaults to rigid "Term: Explanation" bullet points, making the presentation feel disjointed.
- **Solution**: 
  - Update the "Content Refinement" rules in the `generate_narrative_outline` prompt.
  - Emphasize that `body` text can be full sentences, short paragraphs, or single powerful phrases, not just colon-separated lists.
  - Remove the legacy rigid bullet-point enforcement.
  - Encourage the use of natural, flowing text where appropriate, reserving rigid bullets only for actual lists of parallel items.
