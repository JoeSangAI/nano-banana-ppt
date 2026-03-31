# Nano Banana PPT Logo Enhancement Design

## Overview
This document outlines the design for enhancing the Nano Banana PPT skill to better utilize user-uploaded logos. The enhancements include extracting color palettes from the logo to inform the AI-generated aesthetic and improving the logo's scaling and placement logic within the generated slides.

## Feature 1: Logo-based Color Extraction (AI Aesthetic Reconstruction)
**Objective**: When a user uploads a logo but no template, use the logo's colors to inspire the AI-generated presentation style, ensuring the presentation aligns with the brand's aesthetics without strictly forcing 100% color matching.

**Approach**:
1. **Color Extraction**:
   - Create a utility function (e.g., `extract_logo_colors`) in `utils/analyzer.py` or a new image utility module.
   - Use `Pillow` to read the logo image, convert it to RGB/RGBA, and extract the dominant colors (e.g., top 2-3 most frequent non-transparent colors).
2. **Integration into Style Definition**:
   - In `main.py`, when a logo is provided but no template is provided, call the color extraction utility.
   - Pass the extracted brand colors to `VisualAgent.define_style()` via the `constraints` dictionary.
3. **Prompt Update**:
   - Update the prompt in `VisualAgent.define_style()` to explicitly instruct the AI to use the provided "Brand Colors" as inspiration.
   - The prompt will direct the AI to incorporate these colors harmoniously into the presentation's palette, balancing brand identity with overall presentation aesthetics (e.g., ensuring high contrast for readability).

## Feature 2: Logo Scaling and Unified Sizing
**Objective**: Increase the default size of the logo on the slides, ensure it adapts gracefully to different aspect ratios, and maintain strict consistency across all slides.

**Approach**:
1. **Dynamic Scaling Logic**:
   - In `core/generator.py`, update the logo insertion logic.
   - Instead of a fixed small height (e.g., 0.45 inches), implement a bounding box approach (e.g., max_width = 1.5 inches, max_height = 0.8 inches).
   - Calculate the logo's aspect ratio and scale it proportionally to fit within the bounding box without distortion.
2. **Consistency Guarantee**:
   - Calculate the final `logo_w` and `logo_h` once based on the logo's original dimensions and the bounding box.
   - Use these calculated, unified dimensions when inserting the logo on every slide, ensuring identical sizing throughout the presentation.
3. **Placement Adjustments**:
   - Ensure the `lx` (left x) and `ly` (top y) coordinates account for the newly calculated width and height to maintain proper margins from the edges (e.g., `Top-Right` placement correctly aligns to the right edge).

## Next Steps
Proceed to the implementation phase by generating a detailed task plan.