---
name: handling-user-input
description: Game will always use the same control scheme/buttons and mapping of the gamepad and keyboard. Use when creating or modifying a game.
---

# Input Mechanism

When creating or modifying a game:

## Gamepad

- [ ] Use the Web Gamepad API to detect and use gamepads
- [ ] Use the gamepad to control the player
- [ ] Allow either the left stick or D-pad to move the player
- [ ] Use the face buttons for actions (Button 1, Button 2, Button 3, Button 4)
- [ ] **Physical Hardware Wiring Quirk:** On the physical arcade cabinets, buttons were wired non-standardly:
  - B = 0
  - A = 1
  - Y = 2
  - X = 3
  - Home = 8
  - Restart = 9
- [ ] **Gamepad Adapter Wrapper:** When polling the gamepad in `update()`, implement the virtual gamepad adapter wrapper to remap the inputs transparently so game logic and tutorial text can refer to semantic buttons (e.g. `pad.A`) correctly:


```javascript
create() {

    // rest of function

    this.initGamePad();
}
```

```javascript
initGamePad() {
    this.input.gamepad.start();
    this.activeGamepad = null;

    // 1. Check for gamepads ALREADY connected before the game booted
    if (this.input.gamepad.total > 0) {
        // Grab the first available valid gamepad from Phaser's manager
        this.activeGamepad = this.input.gamepad.gamepads.find(pad => pad !== null);
        if (this.activeGamepad) {
            console.log(`Found pre-connected gamepad: ${this.activeGamepad.id}`);
        }
    }

    // 2. Fallback listener for gamepads plugged in AFTER the game started
    this.input.gamepad.on('connected', (pad) => {
        // Only assign it if we don't already have an active gamepad
        if (!this.activeGamepad) {
            this.activeGamepad = pad;
            console.log(`Gamepad plugged in mid-game: ${pad.id}`);
        }
    });
}
```

```javascript
update() {
  const rawPad = this.activeGamepad;

  // Remap hardware wiring inversion where physical face buttons are swapped:
  // Physical wiring: B=0, A=1, Y=2, X=3, Home=8, Restart=9
  // Standard Web Gamepad API: A=0, B=1, X=2, Y=3
  const pad = rawPad ? {
      ...rawPad,
      A: rawPad.B,
      B: rawPad.A,
      X: rawPad.Y,
      Y: rawPad.X,
      isButtonDown: (index) => {
          if (index === 0) return rawPad.isButtonDown(1);
          if (index === 1) return rawPad.isButtonDown(0);
          if (index === 2) return rawPad.isButtonDown(3);
          if (index === 3) return rawPad.isButtonDown(2);
          return rawPad.isButtonDown(index);
      },
      left: rawPad.left,
      right: rawPad.right,
      up: rawPad.up,
      down: rawPad.down,
      axes: rawPad.axes,
      buttons: rawPad.buttons
  } : null;

  // rest of function

}
```

## Keyboard

- [ ] Use the keyboard to control the player
- [ ] Use the Arrow Keys to move the player
- [ ] Use the A, S, Z, X keys for actions (matching Button 1, 2, 3, 4)
- [ ] **Hardware Keyboard Encoder Quirk:** On cabinets using USB keyboard encoders, because buttons A and B are mounted inversely, physical Button A sends key `X` and physical Button B sends key `Z`. When polling primary fire actions for Button A in keyboard environments, check `this.keys.x` instead of `this.keys.z`.

## Control tutorial / explainer

- [ ] Add a simple controls diagram / explainer to the game's start/intro screen to explain the controls.
- [ ] Ensure it explains both the keyboard controls AND the gamepad controls.
- [ ] For the visual diagram of the controls:
   - [ ] Show arrow keys for directional movement (left, right, up, down)
   - [ ] Prioritise the layout to match the gamepad inputs
- [ ] IMPORTANT: Display control diagram and ensure game DOES NOT start until player input.

## Update game config.json

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

- [ ] Implemented Gamepad
- [ ] Implemented Keyboard
- [ ] Implemented Control tutorial
- [ ] Updated config.json if necessary

