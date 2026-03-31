# Design Doc: DataVisualizer Upgrade

**Author**: Agent
**Date**: 2026-02-22
**Status**: Implementation

## Goal
Upgrade the `DataVisualizer` module to improve aesthetics and support background integration for generated charts and tables in Nano Banana PPT.

## Requirements
1.  **Aesthetics**: Modern "card" style for tables and clean, minimal charts.
2.  **Background Integration**: Support `background_image` (resized/cropped) as the base layer.
3.  **Readability**: Ensure text is readable against complex backgrounds (using semi-transparent overlays).
4.  **Fonts**: Support CJK fonts (preserve existing logic).

## Implementation Plan

### 1. `render_table_image` Refactor
-   **Signature**: Add `background_image: Optional[Image.Image] = None`.
-   **Background Preparation**:
    -   If `background_image`: Resize/crop to `output_size` (1920x1080).
    -   If none: Solid color `palette[0]`.
-   **Table Logic**:
    -   Create figure with `facecolor='none'` (transparent).
    -   Create axes covering the central area (e.g., [0.1, 0.1, 0.8, 0.8]).
    -   Use `ax.table` to draw table.
    -   **Styling**:
        -   Iterate over cells `(row, col)`.
        -   Header (row 0): `facecolor=palette[2]` (accent), `text_props={'weight': 'bold', 'color': 'white'}`.
        -   Body rows: Alternating `facecolor` (white / #f8f9fa).
        -   Borders: `cell.set_edgecolor('#e0e0e0')`. Remove vertical borders (set `linewidth=0` for left/right edges? Or just rely on row banding).
        -   Fonts: Increase size (Body: 18-24pt, Header: 24-28pt).
    -   **Overlay**: The table cells themselves act as the overlay (white/colored bg). The gaps/margins will show the background image.

### 2. `render_chart_image` Refactor
-   **Signature**: Add `background_image: Optional[Image.Image] = None`.
-   **Background Preparation**: Same as table.
-   **Chart Logic**:
    -   Create figure with `facecolor='none'`.
    -   Create axes with `facecolor='white'` (or palette bg) and `alpha=0.9` (semi-transparent card).
    -   Draw plot inside axes.
    -   **Styling**:
        -   `ax.spines['top'].set_visible(False)`, `ax.spines['right'].set_visible(False)`.
        -   `ax.grid(True, axis='y', linestyle='--', alpha=0.3)`.
        -   Legend: `frameon=False`, placed logically (top/bottom).
        -   Colors: Use `palette` (skipping `palette[0]` if used for bg).

### 3. `executor.py` Update
-   In `_generate_single_slide`:
    -   Pass `master_slide_image` (if available) to `render_table_image` / `render_chart_image` as `background_image`.

## Verification
-   Check table readability on dark/light backgrounds.
-   Check chart style consistency.
-   Verify CJK font rendering remains intact.
