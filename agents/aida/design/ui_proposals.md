# UI Improvement Proposals for AIDA

Based on the current UI state, here are 5 distinct proposals to improve the interface, ranging from aesthetic polish to functional restructuring:

### Proposal 1: High-Fidelity Retro Polish (Aesthetic Focus)
Enhance the PC-98/Cyberpunk vibe with more advanced visual effects.
*   **CRT Effects:** Add a subtle CSS-based scanline overlay, slight screen curvature, and a faint flicker animation to mimic an old monitor.
*   **Neon Glow:** Apply a slight text-shadow glow to the green and cyan text elements to make them "pop" like real phosphor displays.
*   **Custom Borders:** Replace the standard CSS double borders with custom pixel-art border images (using `border-image`) that have distinct corner designs, making the windows look more like hardware components.
*   **Animated Background:** Replace the static gradient background with a very slow-moving, low-contrast scrolling grid or starfield animation.

### Proposal 2: Layout Rebalancing (Structural Focus)
Optimize the use of space and improve alignment.
*   **Integrate Header:** Shrink the large main header and embed it into the top border of the chat container (like a `<fieldset>` legend) to reclaim vertical space.
*   **Collapsible Log:** Move the system log into a collapsible drawer at the bottom or a tab in the right sidebar. It currently takes up a lot of prime real estate for secondary information.
*   **Alignment Fixes:** Precisely align the `AIDA>` prompt and input line with the left edge of the chat messages box. Currently, it's slightly offset.
*   **Compact Sidebar:** Reduce the vertical padding in the sidebar panels. The "MEMORY" and "MODEL" panels have a lot of internal empty space.

### Proposal 3: "Cockpit" Dashboard (Thematic Focus)
Make the interface feel more like an integrated control console rather than separate web `div`s.
*   **Integrated Frames:** Connect the separate panels (chat, sidebar, log) with connecting "pipes" or tech-line graphics so they feel like one cohesive unit.
*   **Live Decorators:** Add small, animated "dummy" readouts in the sidebar (e.g., a fake CPU load graph, scrolling hex code, or blinking network LEDs) to make the interface feel alive even when idle.
*   **Avatar Integration:** Change the avatar frame from a simple box to a more integrated shape (e.g., chamfered corners) with a "live feed" label overlaying the image itself.
*   **Unified Command Bar:** Move the input field to the very bottom of the screen, spanning the full width, acting as a master command console for the entire dashboard.

### Proposal 4: Enhanced UX & Interactivity (Functional Focus)
Improve usability and discoverability of features.
*   **Quick Action Buttons:** Add a row of programmable quick-command buttons below the model selector (e.g., "Clear Memory", "Run Diagnostics", "Help") for one-click access.
*   **Interactive Memory Bar:** Make the memory bar interactive. Hovering over it could show a tooltip with the exact token breakdown (prompt vs. completion tokens).
*   **Rich Status Indicators:** Replace the simple "STATUS: ONLINE" text with a more detailed status cluster (e.g., connection latency ping, current model icon, error rate indicator).
*   **Model Tooltips:** Add hover tooltips to the model buttons explaining their best use case (e.g., "Gemini: Complex reasoning", "Qwen: Speed/Local").

### Proposal 5: Minimalist Terminal (Simplification Focus)
Reduce visual noise to focus on the content.
*   **Remove Outer Borders:** Remove the outermost container borders, letting the black background bleed to the edge, creating a more immersive, full-screen terminal feel.
*   **Typography Hierarchy:** Use a bolder, blockier pixel font for headers and buttons, and keep the current font for body text to create better visual separation.
*   **Distinct Message Styling:** Give user messages and agent responses slightly different background shades (very dark blocks) to make the chat history easier to scan.
*   **Simplified Color Palette:** Reduce the number of colors. Stick strictly to monochrome green for the interface structure, using cyan only for user input and amber only for alerts.
