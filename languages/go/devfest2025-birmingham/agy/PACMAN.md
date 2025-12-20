Create a Pac-Man clone in Go using the Ebitengine game library (`github.com/hajimehoshi/ebiten/v2`) and its vector package (`github.com/hajimehoshi/ebiten/v2/vector`) for graphics. The game should be a single-file implementation (`main.go`) that is ready to run.

### Core Requirements

1.  **Dependencies:**
    *   Use `github.com/hajimehoshi/ebiten/v2` (v2.9.4 or later).
    *   Use `github.com/hajimehoshi/ebiten/v2/vector` for all rendering (no external sprites/images).
    *   Use `github.com/hajimehoshi/ebiten/v2/ebitenutil` for debug text.
    *   Use standard libraries `math`, `math/rand`, `image/color`, `fmt`, `log`, and `time`.

2.  **Game Configuration:**
    *   **Screen Size:** 800x600 pixels.
    *   **Tile Size:** 20x20 pixels.
    *   **Speed:** 2.0 pixels per frame (must be an integer divisor of Tile Size to ensure alignment).
    *   **Start Positions:**
        *   Pac-Man: Center of a tile in the upper-left quadrant (e.g., grid coordinates 1, 1).
        *   Ghosts: Center of tiles in the middle/lower area (e.g., grid coordinates 13-16, 11). Ensure spawn points are not walls.

3.  **Map System:**
    *   Use a 2D integer array (`[][]int`) to represent the grid.
    *   **0:** Path (empty space).
    *   **1:** Wall (blue filled rectangle).
    *   **2:** Dot (small white filled circle, turns to 0 when eaten).
    *   The map should define a classic-style maze with walls, paths, and enclosed areas.

4.  **Entities:**
    *   **Pac-Man:** A yellow circle with an animated mouth (wedge) that opens and closes.
    *   **Ghosts:** 4 ghosts, each with a unique color (Red, Pink, Cyan, Orange).
        *   Shape: A colored circle on top of a colored rectangle (bell shape).
        *   Eyes: White circles with smaller black pupils.

5.  **Game Logic (Crucial for Smooth Movement):**
    *   **State Tracking:** Maintain `pacmanX`, `pacmanY`, `currentDirection`, `nextDirection` (buffered input), and `gameOver`.
    *   **Input:** Arrow keys buffer the `nextDirection`.
    *   **Collision & Movement Algorithm:**
        *   Distinguish between "at tile center" and "in transit".
        *   **At Center:**
            *   Check if `nextDirection` is valid (not a wall). If so, update `currentDirection`.
            *   Check if `currentDirection` is valid. If so, move. If not (wall ahead), stop.
            *   Handle interactions (eat dots, change ghost direction).
        *   **In Transit (Not at Center):**
            *   Allow immediate 180-degree turns (reversing direction).
            *   Otherwise, **force move** in `currentDirection` until the next center is reached. Do *not* check for walls while moving between tiles to prevent getting stuck at edges.
    *   **Ghost AI:**
        *   Ghosts move continuously.
        *   At every tile intersection (center), check valid exit directions.
        *   Randomly select a valid new direction (excluding 180-degree reverses if possible, though simple random valid neighbor is acceptable).
    *   **Win/Loss:**
        *   **Score:** +10 points per dot. Display in the corner.
        *   **Game Over:** Collision between Pac-Man and any Ghost sets `gameOver = true`, stops updates, and displays "GAME OVER!" text.

6.  **Rendering (`Draw` method):**
    *   Clear screen.
    *   Iterate map: Draw walls (`vector.FillRect`) and dots (`vector.FillCircle`).
    *   Draw Pac-Man: Use `vector.Path` with `Arc`, `LineTo`, and `Close`. Use `vector.FillPath` with `DrawPathOptions` containing `ColorScale` to set the yellow color.
    *   Draw Ghosts: Use `vector.FillCircle` and `vector.FillRect` for bodies and eyes.
    *   Draw UI: Score and Game Over text using `ebitenutil.DebugPrint` / `DebugPrintAt`.

Ensure the final code is bug-free, compiles immediately, and provides smooth, non-sticky grid-based movement.