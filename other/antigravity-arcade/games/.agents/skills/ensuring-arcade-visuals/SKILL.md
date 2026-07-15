---
name: ensuring-arcade-visuals
description: Arcade game must have a retro asthetic. Use when creating or modifying a game to ensure that the game looks retro and maintains a consistent look and feel with all games.
---

# Arcade Visuals

All arcade games will have the same retro asthetic which is achieved though executing all of the following steps.

1. [ ] The game's background color is black.
2. [ ] The game's shaders directory includes CRTShader.js.
3. [ ] The game's main camera has the CRTShader applied.
   -   IMPORTANT: If the game has a HUD (Heads Up Display), the CRT effect MUST not be applied to it. Instead, create a separate camera for the HUD and apply the CRTShader to the main camera only. Keep the UI and HUD on a separate layer so they are not affected by the CRTShader.
4. [ ] The font `public/assets/fonts/Pixelate-Regular.ttf` is used for all game text and the default size is 24px unless specified otherwise.
