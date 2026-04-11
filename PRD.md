# Nano Banana PPT v3 — Product Requirements Document

> Version: 0.1 | Date: 2026-04-05 | Author: Joe + Claude
> Status: Draft

## 1. Executive Summary

**The Vision**: Transform Nano Banana PPT from a one-way black-box pipeline into an interactive, multi-agent collaborative workspace. It elevates the visual output quality to handle complex text-and-image layouts (图文混排) flawlessly, breaking free from the constraints of simple bullet-point slides.

**The Analogy**: The user is the client. The PM Agent is the Account Manager who uncovers the true narrative. The Visual Director Agent is the Design Lead who crafts the aesthetic and layouts. The user reviews and approves at key milestones before any rendering compute is spent.

## 2. Core Upgrades from v2 to v3

### 2.1 Interactive Agent Collaboration (The Team Model)
Currently, Nano Banana PPT runs as a fire-and-forget pipeline (`plan` -> `execute`). In v3, we adopt the successful multi-agent interaction model from `nano_banana_pic`.

- **PM Agent (The Narrative Lead)**: Interacts with the user, gathers the raw content, understands the presentation's goal, and structures the narrative (SCQA, Hero's Journey, etc.).
- **Visual Director Agent (The Design Lead)**: Takes the narrative outline, proposes visual styles, allocates layouts (especially complex text/image grids), and generates the final Gemini prompts.
- **Milestone Approvals**: The user explicitly approves the narrative outline and the visual style proposal *before* the heavy execution phase begins.

### 2.2 High Visual Output Quality (Complex Text/Image Layouts)
Gemini 3.1 Flash Image excels at visual generation, but historically struggles with dense text and complex multi-element layouts. v3 introduces a paradigm shift in how we instruct the model for PPT slides.

- **VLM Semantic Layout 2.0**: Instead of just parsing text, we use explicit layout directives (e.g., "Left: 40% Text Column, Right: 60% Image Canvas") to force Gemini to create clean negative space for typography.
- **"Chaotic" Typography Rules (混沌排版法则)**: Strict prompt engineering borrowed from `nano_banana_pic` (e.g., "细体正文、粗体标题、2x行高", "High negative space — every section breathes").
- **Complex Text/Image Integration (图文混排)**: Native support for multi-column layouts, floating cards over background, and semantic locking of image placeholders alongside dense text blocks. We move away from "bullet points on a background" to "editorial magazine layouts".

## 3. The Multi-Agent Workflow

### Phase 1: Intake & Narrative Structuring (PM Agent)
1. **Trigger**: User invokes the tool with a topic, a raw document, or a rough outline.
2. **Dialogue**: PM Agent asks clarifying questions (Target audience? Desired tone? Key takeaway?).
3. **Drafting**: PM Agent generates the `plan_for_review.md` (The Narrative Outline).
4. **Approval**: User reviews, requests changes, and ultimately approves the outline.

### Phase 2: Visual Concepting (Visual Director Agent)
1. **Handoff**: PM Agent passes the approved outline to the Visual Director.
2. **Proposals**: Visual Director analyzes the content density and proposes 2-3 visual themes (e.g., "A. Minimalist Apple Keynote", "B. Dark Mode Cyberpunk", "C. Editorial Magazine").
3. **Layout Strategy**: For dense slides, the Visual Director explicitly defines the grid (e.g., "Slide 4 is too dense; splitting into a 3-card layout with distinct icons").
4. **Approval**: User selects a theme and approves the visual strategy.

### Phase 3: Execution & Assembly (The Engine)
1. **Prompt Generation**: Visual Director compiles the final, highly-constrained Gemini prompts for each slide, incorporating the "Chaotic Typography Rules".
2. **Generation**: The `core/executor.py` handles the parallel generation of images via DeerAPI (handling 16:9, 4K resolution).
3. **Assembly**: The generated images (which now have baked-in layouts and text areas) and any native user images are composited.

## 4. Technical Architecture Updates

### 4.1 New Directory Structure (aligned with nano_banana_pic)
```text
nano-banana-ppt/
├── .claude/
│   └── agents/
│       ├── ppt-pm.md                  # PM Agent definition
│       └── ppt-creative-director.md   # Visual Director definition
├── core/
│   ├── generator.py                   # Updated to handle complex layouts
│   ├── executor.py                    # Generation engine
│   └── layout_engine.py               # NEW: Handles complex grid logic
```

### 4.2 The Layout Engine (The Secret Sauce)
To achieve true "图文混排" (Complex Text/Image Layout), we cannot rely solely on Gemini's zero-shot understanding of text placement.
- We will define a set of **Layout Archetypes** (e.g., `Split-Left`, `Split-Right`, `Three-Card-Row`, `Hero-Center`, `Grid-2x2`).
- The Visual Director assigns an archetype to each slide based on content density.
- The prompt sent to Gemini explicitly defines the negative space required by the archetype (e.g., "LEAVE THE ENTIRE LEFT 50% OF THE CANVAS COMPLETELY EMPTY AND PURE BLACK for typography overlay").

### 4.3 Typography Rules (Inherited from Pic)
The Visual Director will append strict typography rules to every slide prompt:
- Title text: EXTRA BOLD, large size
- Body text: MEDIUM weight (NOT bold)
- Line height: 1.8x to 2.0x
- Paragraph spacing: 40% more than line height
- High negative space — minimalist, breathable layout

## 5. Success Metrics
- **Zero-Shot Usability**: User can provide a raw 5-page document and get a highly structured, visually stunning 10-slide deck without writing a single prompt.
- **Layout Fidelity**: Dense text slides look like editorial magazines, not walls of text. No text overlaps with critical image subjects.
- **Agent Smoothness**: The transition from PM to Visual Director feels natural and additive, not robotic.

## 6. Project Setup Instructions
Adopt the Team mode setup.
- Create an agent team using the .claude/agents definitions.

## 7. Migration Plan

### Step 1: Agent Definitions
- Create `ppt-pm.md` and `ppt-creative-director.md` in `.claude/agents/`.
- Port the interactive dialogue behaviors from `nano_banana_pic`'s PM and Creative Director.

### Step 2: Extract Core Prompt Engineering
- Analyze the `nano_banana_pic` "混沌排版" rules.
- Adapt the prompt rules for 16:9 presentation dimensions.

### Step 3: Implement Layout Engine & Refactor Prompts
- Create `core/layout_engine.py` with predefined grid patterns.
- Modify the existing `VisualAgent` (or the script the new Claude Agent will invoke) to use these patterns and generate prompts with the new typography rules.

### Step 4: Hook up Execution
- Modify `main.py` to support step-by-step execution guided by the new Agents, moving away from the rigid `plan-content` / `plan-visual` one-shot CLI commands.
