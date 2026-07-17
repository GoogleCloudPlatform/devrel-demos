---
name: building-platformer-games
description: Ensures platformer games have polished movement, responsive controls, and balanced jump mechanics. Use ONLY when the game type is "platformer".
---

# Platformer Games Skill

When creating or refining platformer games, use this skill to ensure movement feels responsive, jumps are satisfying, and physics align perfectly with level design.

## Core Mechanics & Best Practices

### 1. Jump Mechanics & Level Alignment
- **Jump Height & Distance Calibration:** Ensure the jump strength allows the player to reach intended platforms. Test that the player can comfortably clear gaps and reach vertical platforms according to the level design.
- **Jump Calculations:**
  - In Phaser Arcade Physics, gravity (`gravity.y`) and jump velocity (`setVelocityY(-speed)`) must be balanced.
  - Keep platforms at heights that correlate to exact multiples of the player's maximum jump height.

### 2. Extra Jumping Options
- **Wall Jumping:** Clarify with the user whether the game should include wall jumping. If included, implement it by checking collision with walls and applying an upward and outward force away from the wall.
- **Double Jumping:** Clarify with the user if double jumping should be supported.
- **Precise Double Jump Logic:**
  - The player should have a maximum of two jumps.
  - Jumping from the ground consumes the first jump, leaving one extra jump.
  - Walking off a cliff/platform without jumping leaves the player with exactly one jump remaining (the second/extra jump).
  - Reset the jump count upon hitting the floor (`player.body.blocked.down` or `player.body.touching.down`).

### 3. Advanced Feel & Polishing (Game Feel)
- **Coyote Time:** Allow a small grace period (e.g., 100-150 milliseconds) after a player walks off a ledge during which they can still jump. This prevents the player from feeling cheated by a missed jump input.
- **Jump Buffering:** Register a jump input slightly before the player hits the ground (e.g., within 100ms of landing). If the player hits the jump button just before touching the ground, trigger the jump immediately upon collision with the floor.
- **Variable Jump Height:** Allow players to control the height of their jump based on how long the jump key is held down. If they release the jump button early, reduce their vertical velocity to start falling immediately.
- **Responsive Acceleration & Deceleration:** Instead of instantly moving at full speed, introduce slight friction and acceleration. This makes turning and stopping feel more natural without making the character feel too slippery.
- **Accurate Collision Boxes:** Make the character's collision box slightly narrower than the visual sprite. This prevents the player from getting stuck on the edges of overhead tiles when jumping up near a corner.

## Advanced Movement Options

When implementing advanced platformer movement, be aware of the following patterns:

- **Slide:** Allow players to **slide** under gaps. This is achieved by reducing the player's height (scaling the sprite) while maintaining their horizontal velocity. This is commonly implemented with a dedicated slide key (e.g., `Space` or `Down` on a gamepad).
- **Charge Jump:** Implement a charge jump system where holding the jump button for a short duration increases the player's jump height. This typically involves:
  - Detecting a "jump press" and holding the jump in a ready state.
  - Applying a proportional vertical velocity boost based on the charge duration.
  - Ensuring the charge resets upon landing or after performing the jump.
- **Wall Jump:** Allow players to jump off walls. This is implemented by:
  - Detecting a wall collision from the side (`player.body.blocked.left` or `player.body.blocked.right`).
  - Applying an upward and outward force away from the wall.
  - Preventing further wall jumps until the player touches the ground or air.
