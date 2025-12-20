# Simplified Pac-Man Clone Prompt

**Objective:**
Create a complete, single-file Pac-Man clone in Go using the Ebitengine (v2) library. The game must be contained entirely within `main.go` and use procedural graphics (no external assets).

**Configuration:**
*   **Tile Size:** 24 pixels.
*   **Map:** 28x31 tiles (Classic layout).
*   **Screen:** 672x744 pixels.
*   **Speed:** 3 pixels per frame (Crucial: 3 divides 24 evenly, ensuring clean grid alignment).

**Critical Guardrails (Strict Adherence Required):**
To prevent movement bugs and visual misalignment, you must follow these rules:
1.  **Logical vs. Visual:** Entity `x, y` coordinates MUST represent the **top-left corner** of the tile. Do NOT store center coordinates in the struct.
2.  **Rendering Offset:** Only apply the "center offset" (e.g., `+ TileSize/2`) inside the `Draw` method when rendering circles or shapes.
3.  **Grid Alignment:** Initial positions must be exact multiples of `TileSize`.
4.  **Turning Logic:** Only allow direction changes when the entity is exactly centered on a tile. Check this using `math.Mod(x, TileSize) == 0 && math.Mod(y, TileSize) == 0`.
5.  **Input Buffering:** Store a `nextDir`. When the entity reaches a tile center, check if `nextDir` is valid (no wall). If so, update the actual direction.

**Graphics (Vector Package):**
*   Use `github.com/hajimehoshi/ebiten/v2/vector` for all rendering.
*   **Pac-Man:** Yellow circle with an animated mouth (opening/closing) using `vector.Path`.
*   **Ghosts:** Colored bodies (Red, Pink, Cyan, Orange) with eyes that look in the direction of movement.
*   **Map:** Blue walls and white dots.

**Game Logic:**
*   **Map Layout:** Implement a 28x31 grid using a hardcoded string map (Walls, Dots, Ghost House, Empty Space).
*   **Tunnel:** Implement wrap-around logic: if an entity leaves the screen horizontally, they reappear on the opposite side.
*   **Ghost AI:** Ghosts move continuously. At every intersection (or wall hit), choose a random valid direction. Prefer not to reverse direction unless necessary.
*   **Collision:**
    *   **Walls:** Look ahead one tile. If blocked, stop.
    *   **Dots:** If center of Pac-Man hits a dot tile, remove dot and add score.
    *   **Ghosts:** If Pac-Man touches a ghost, Game Over.

**Controls:**
*   **Arrows:** Move.
*   **P:** Pause.
*   **Q:** Quit.
*   **F:** Toggle Fullscreen.
*   **Enter:** Restart.
