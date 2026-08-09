---
name: generating-mock-images
description: >
  Generates mock flower and plant images for an e-commerce website, presenting
  them for user review. Use when generating mock product images for flower and
  plant stores or managing generated mock image assets.
---

# Generating Mock Images for Flower & Plant E-Commerce

Generates high-quality mock product photography for flower and plant e-commerce stores, displays the resulting image in chat for review, and handles user feedback (regenerate, delete, or save to workspace).

---

## Workflow Steps

### 1. Synthesize Prompt & Call `generate_image`

> **CRITICAL TOOL RULE**: You MUST execute the native `generate_image` tool to generate studio product images. Do NOT write Python scripts (e.g. PIL, matplotlib, byte packing), HTML/Canvas, SVG, or code to render images.

**Default Pre-baked Subject Options**:
- **Option A (Houseplants)**: "Lush potted plant with healthy leaves in a minimalist ceramic pot"
- **Option B (Floral Arrangements)**: "Elegant floral arrangement of fresh seasonal blooms in a clear glass vase filled with crystal-clear water"

**Prompt Synthesis Strategy**:
When composing the `Prompt` argument for `generate_image`, integrate the scene, camera, and lighting parameters:
> "Professional studio product photograph of [SUBJECT]. [SCENE: smooth matte light gray surface, seamless background curve with soft infinite horizon, visible water line in vase]. [CAMERA: macro lens photography, sharp focus from front to back, f/11 aperture, crisp details, zero digital noise]. [LIGHTING: three-point soft-diffuse lighting, 48-inch octagonal softbox key light at 45 degrees, gentle fill light, backlit soft ambient glow, no harsh glare or unwanted reflections, premium e-commerce product catalog style]."

Invoke `generate_image` tool:
- `Prompt`: Synthesized prompt combining Subject + Scene + Camera + Lighting specs.
- `ImageName`: `mock_flower_plant` (or uniquely named based on selection).
- `AspectRatio`: Default to `"1:1"`. If the user explicitly specifies a different aspect ratio in their prompt or request (e.g., `"16:9"`, `"3:2"`, `"4:3"`, `"9:16"`), use that specified aspect ratio instead.

---

### 2. Display Image in Chat
Upon receiving the output path from `generate_image`, render the image directly in the chat response using standard markdown image syntax:

`![Mock Flower/Plant Product](file://<GENERATED_IMAGE_PATH>)`

---

### 3. Prompt User for Action (`ask_question`)
Invoke `ask_question` tool to ask the user how to handle the generated asset:

- **Question**: "What would you like to do with this generated mock image?"
- **Options**:
  - "Keep"
  - "Regenerate"
  - "Exit"

---

### 4. Process User Choice

#### Action: Keep (`<workspace>/public/images/`)
- [ ] Ensure the destination directory exists at `<workspace>/public/images/`.
- [ ] Copy image file from `<GENERATED_IMAGE_PATH>` to `<workspace>/public/images/<image_filename>`.
- [ ] Display a confirmation message.

#### Action: Regenerate Image
- [ ] Re-run **Step 1**.
- [ ] Render the updated image in chat (**Step 2**).
- [ ] Re-prompt the user with `ask_question` (**Step 3**).

#### Action: Exit
- [ ] Exit workflow without saving to workspace
