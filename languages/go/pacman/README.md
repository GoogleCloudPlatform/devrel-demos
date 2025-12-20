# Pac-Man Clone (Go + Ebitengine)

A complete, single-file Pac-Man clone written in Go using the [Ebitengine](https://ebitengine.org/) (v2) library.

## Overview

This project demonstrates how to build a 2D game in Go with:
- **Procedural Graphics**: All assets (Pac-Man, ghosts, map) are drawn at runtime using vector graphics. No external PNG/JPG files are required.
- **Single File**: The entire game logic is contained in `main.go`.
- **Classic Mechanics**: Includes ghost AI, tunnel wrapping, score tracking, and strict grid-based movement.

## Prerequisites

- Go 1.24 or later

## Running the Game

```bash
go run main.go
```

## Controls

- **Arrow Keys**: Move
- **P**: Pause
- **Q**: Quit
- **F**: Toggle Fullscreen
- **Enter**: Restart

## Implementation Details

This implementation was generated based on `simplified_prompt.md`, focusing on:
- Strict grid alignment (24px tiles).
- Vector rendering for all sprites.
- Basic ghost AI with collision detection.
