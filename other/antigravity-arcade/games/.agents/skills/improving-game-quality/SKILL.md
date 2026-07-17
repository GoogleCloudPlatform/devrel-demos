---
name: improving-game-quality
description: Ensures games created have a good quality user experience and follow best practices. Use when creating or modifying a game.
---

# Game Quality

Follow these steps when creating or modifying a game:

1. **UI placement:**
   Ensure the UI (text, score, lives, etc) is always rendered with a margin within the view port of the game screen – not flush to the edges.

2. **Game loop:**
   - Ensure the game loop is always running and that the game is always in a state where it can be played.
   - Ensure the game loop always contains a reachable "lose" condition.

3. **Background visuals:**
   Ensure the game always has some kind of background particle that makes sense for the game world (e.g. stars in space, rain in a city, wind in a forest, etc.)

4. **Game feel:**
   Ensure the game always has some kind of screen shake when things happen (e.g. explosions, collisions, etc.)

5. **Apply particle effects:**
   - Whenever enemies are destroyed, explosions should occur. Use the particle emitter to spawn particles at the location of the explosion. Limit the number of particles to 5-10.
   - Use smaller particles for less significant events (e.g. bullet hitting a wall, or character landing on the ground in a platformer).
   - Use larger particles for more significant events (e.g. enemies being destroyed, or character dying).

6. **Update Game config.json:**
The game's config.json, found in the game's root folder (e.g. `<game-folder>/config.json`) contains a `controls` section that defines the labels for buttons `A`, `B`, `X`, and `Y`. These arew the only 4 buttons allowed in the config.

When the game is created or modified, this `config.json` file should be updated to reflect the correct labels for each button. For example, if a code edit adds business logic so that the `B` enables the player to jump, set the label to "Jump". Labels must be short and limited to one word, or two words at most and MUST be an action (e.g. "Jump", "Run", "Fire", "Crawl", "Climb", etc.). There is limited space where the label will render in the UI so it must remain short.

If useful to explain the game's objective, the objective may be improved to include the new behavior.

**Example:**

```json
{
  "title": "Space Pilot",
  "objective": "Navigate your spaceship while evading obstacles. Destroy them for points.",
  "controls": {
    "A": "Shoot",
    "B": "Evade",
    "X": "Roll Ship",
    "Y": ""
  }
}
```

## Verification

- [ ] Game has UI layer with score and lives
- [ ] Game has a valid game loop
- [ ] Game has background particles (e.g. stars, rain, etc.)
- [ ] Game has a screen shake effect
- [ ] Game emits particles for effects (e.g. collisions, explosions, etc.)
- [ ] Updated config.json if necessary

