---
name: Tech-Forward Management
colors:
  surface: '#f8f9ff'
  surface-dim: '#cbdbf5'
  surface-bright: '#f8f9ff'
  surface-container-lowest: '#ffffff'
  surface-container-low: '#eff4ff'
  surface-container: '#e5eeff'
  surface-container-high: '#dce9ff'
  surface-container-highest: '#d3e4fe'
  on-surface: '#0b1c30'
  on-surface-variant: '#45464d'
  inverse-surface: '#213145'
  inverse-on-surface: '#eaf1ff'
  outline: '#76777d'
  outline-variant: '#c6c6cd'
  surface-tint: '#565e74'
  primary: '#000000'
  on-primary: '#ffffff'
  primary-container: '#131b2e'
  on-primary-container: '#7c839b'
  inverse-primary: '#bec6e0'
  secondary: '#0058be'
  on-secondary: '#ffffff'
  secondary-container: '#2170e4'
  on-secondary-container: '#fefcff'
  tertiary: '#000000'
  on-tertiary: '#ffffff'
  tertiary-container: '#002113'
  on-tertiary-container: '#009668'
  error: '#ba1a1a'
  on-error: '#ffffff'
  error-container: '#ffdad6'
  on-error-container: '#93000a'
  primary-fixed: '#dae2fd'
  primary-fixed-dim: '#bec6e0'
  on-primary-fixed: '#131b2e'
  on-primary-fixed-variant: '#3f465c'
  secondary-fixed: '#d8e2ff'
  secondary-fixed-dim: '#adc6ff'
  on-secondary-fixed: '#001a42'
  on-secondary-fixed-variant: '#004395'
  tertiary-fixed: '#6ffbbe'
  tertiary-fixed-dim: '#4edea3'
  on-tertiary-fixed: '#002113'
  on-tertiary-fixed-variant: '#005236'
  background: '#f8f9ff'
  on-background: '#0b1c30'
  surface-variant: '#d3e4fe'
typography:
  h1:
    fontFamily: Inter
    fontSize: 36px
    fontWeight: '700'
    lineHeight: '1.2'
    letterSpacing: -0.02em
  h2:
    fontFamily: Inter
    fontSize: 24px
    fontWeight: '600'
    lineHeight: '1.3'
    letterSpacing: -0.01em
  h3:
    fontFamily: Inter
    fontSize: 18px
    fontWeight: '600'
    lineHeight: '1.4'
    letterSpacing: '0'
  body-md:
    fontFamily: Inter
    fontSize: 16px
    fontWeight: '400'
    lineHeight: '1.6'
    letterSpacing: '0'
  body-sm:
    fontFamily: Inter
    fontSize: 14px
    fontWeight: '400'
    lineHeight: '1.5'
    letterSpacing: '0'
  label-caps:
    fontFamily: Inter
    fontSize: 12px
    fontWeight: '700'
    lineHeight: '1'
    letterSpacing: 0.05em
  button:
    fontFamily: Inter
    fontSize: 14px
    fontWeight: '600'
    lineHeight: '1'
    letterSpacing: 0.01em
rounded:
  sm: 0.125rem
  DEFAULT: 0.25rem
  md: 0.375rem
  lg: 0.5rem
  xl: 0.75rem
  full: 9999px
spacing:
  base: 4px
  xs: 4px
  sm: 8px
  md: 16px
  lg: 24px
  xl: 40px
  container-max: 1280px
  gutter: 24px
---

## Brand & Style
The design system is engineered for high-stakes hackathon environments where clarity, speed of interaction, and institutional reliability are paramount. The brand personality is **Corporate Modern with a Tech-Forward Edge**—balancing the gravity of enterprise software with the kinetic energy of a coding competition. 

The aesthetic leans into a refined **Minimalism** with subtle **Tonal Layering**. It prioritizes a "Data-First" philosophy, ensuring that organizers and judges can navigate complex project listings and scoring matrices without cognitive overload. The UI should evoke a sense of precision, efficiency, and professional prestige, moving away from "playful" tropes in favor of a sophisticated, utility-driven workspace.

## Colors
The palette is anchored by **Deep Navy (Slate 950)** to provide a professional, authoritative foundation. This is contrasted against a crisp **Slate White** background to maintain a high-contrast environment for long-form reading and data entry.

- **Primary:** Deep Blue is used for persistent structural elements like sidebars and primary headings.
- **Accent:** Electric Blue is reserved for primary actions and interactive states, signaling "path to completion."
- **Success/Vibrant:** Emerald Green is utilized for "Finalized" or "Winner" statuses, providing a high-visibility celebratory cue.
- **Neutrals:** A range of Slate Greys (50-700) handles borders, secondary text, and inactive states, ensuring the hierarchy remains flat until an action is required.

## Typography
This design system utilizes **Inter** for its exceptional legibility on digital screens and its neutral, systematic character. The typographic scale is designed to create a clear vertical rhythm.

- **Headlines:** Use tighter tracking and heavier weights to anchor pages.
- **Body Text:** Generous line height (1.6) is applied to project descriptions and judging criteria to prevent eye fatigue.
- **Labels:** Uppercase styles with increased letter spacing are used for metadata, such as "JUDGING STATUS" or "TECH STACK," to differentiate data points from narrative content.

## Layout & Spacing
The layout follows a **12-column fixed grid** centered within the viewport for maximum readability on desktop displays. 

- **Hierarchy through Whitespace:** Use large `xl` (40px) gaps between major sections (e.g., Project Header vs. Judging Form).
- **Component Padding:** Use a consistent `md` (16px) or `lg` (24px) internal padding for cards and modals to maintain a "breathable" feel.
- **Grouping:** Use the `sm` (8px) unit to group related elements, such as an input field and its helper text.

## Elevation & Depth
Depth in this design system is achieved through **Tonal Layers** and **Low-Contrast Outlines** rather than heavy shadows. This reinforces the professional, flat aesthetic.

- **Level 0 (Background):** Slate 50 (#F8FAFC).
- **Level 1 (Cards/Surface):** Pure White with a 1px border in Slate 200. No shadow.
- **Level 2 (Dropdowns/Modals):** Pure White with a 1px border and a subtle, diffused ambient shadow (0px 10px 15px -3px rgba(15, 23, 42, 0.05)) to suggest interaction.
- **Interaction:** On hover, interactive cards should transition their border color to Primary Blue rather than increasing shadow depth.

## Shapes
The shape language is **Soft and Precise**. A consistent 0.25rem (4px) base radius is used across most components to maintain a disciplined, corporate appearance.

- **Standard Radius:** 4px for buttons, input fields, and small cards.
- **Large Radius:** 8px for main content containers or modals.
- **Pill Shape:** Reserved exclusively for status badges (e.g., "In Progress," "Submitted") to distinguish them from actionable buttons.

## Components
- **Action Buttons:** Primary buttons use a solid Electric Blue background with white text. Secondary buttons use a Slate 200 ghost style. Action buttons for judging (e.g., "Submit Score") should be prominent, using a 48px height for high clickability.
- **Project Cards:** Feature a 1px border, a crisp H3 title, and a bottom utility row for "Judging State" badges.
- **Status Badges:** Use a "Soft Fill" approach—light tinted background with high-contrast text (e.g., Emerald 100 background with Emerald 700 text).
- **Input Fields:** Use a Slate 100 fill with a subtle Slate 200 border. Focus states must shift the border to Primary Blue with a 2px outer glow.
- **Judging Matrix:** A specialized table component with sticky headers and highlighted "Active Row" states to assist judges in tracking their progress through large sets of participants.
- **Progress Steppers:** Horizontal, thin-line indicators at the top of judging flows to provide context and reduce "form fatigue."