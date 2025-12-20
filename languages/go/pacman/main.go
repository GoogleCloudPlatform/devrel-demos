package main

import (
	"fmt"
	"image/color"
	"log"
	"math"
	"math/rand"
	"os"
	"time"

	"github.com/hajimehoshi/ebiten/v2"
	"github.com/hajimehoshi/ebiten/v2/ebitenutil"
	"github.com/hajimehoshi/ebiten/v2/inpututil"
	"github.com/hajimehoshi/ebiten/v2/vector"
)

const (
	TileSize     = 24
	MapWidth     = 28
	MapHeight    = 31
	ScreenWidth  = MapWidth * TileSize
	ScreenHeight = MapHeight * TileSize
	Speed        = 3
)

type TileType int

const (
	TileEmpty TileType = iota
	TileWall
	TileDot
	TileGate // Ghost house gate
)

type Direction int

const (
	DirNone Direction = iota
	DirUp
	DirDown
	DirLeft
	DirRight
)

// Map layout (1=Wall, .=Dot, space=Empty, -=Gate)
// 28x31 grid
const mapLayout = `
1111111111111111111111111111
1............11............1
1.1111.11111.11.11111.1111.1
1.1111.11111.11.11111.1111.1
1.1111.11111.11.11111.1111.1
1..........................1
1.1111.11.11111111.11.1111.1
1.1111.11.11111111.11.1111.1
1......11....11....11......1
111111.11111 11 11111.111111
     1.11111 11 11111.1     
     1.11          11.1     
     1.11 111--111 11.1     
111111.11 1      1 11.111111
      .   1      1   .      
111111.11 1      1 11.111111
     1.11 11111111 11.1     
     1.11          11.1     
     1.11 11111111 11.1     
111111.11 11111111 11.111111
1............11............1
1.1111.11111.11.11111.1111.1
1.1111.11111.11.11111.1111.1
1...11................11...1
111.11.11.11111111.11.11.111
111.11.11.11111111.11.11.111
1......11....11....11......1
1.1111111111.11.1111111111.1
1.1111111111.11.1111111111.1
1..........................1
1111111111111111111111111111
`

type Entity struct {
	x, y      float64
	dir       Direction
	nextDir   Direction
	color     color.RGBA
	isPacman  bool
	mouthOpen float64
	mouthDir  float64 // 1 for opening, -1 for closing
}

type Game struct {
	grid     [][]TileType
	pacman   *Entity
	ghosts   []*Entity
	score    int
	gameOver bool
	paused   bool
	rand     *rand.Rand
}

func NewGame() *Game {
	g := &Game{
		grid: make([][]TileType, MapHeight),
		rand: rand.New(rand.NewSource(time.Now().UnixNano())),
	}

	// Parse map
	rows := 0
	cols := 0
	for _, r := range mapLayout {
		if r == '\n' {
			if cols > 0 {
				rows++
				cols = 0
			}
			continue
		}
		if rows >= MapHeight {
			break
		}
		if g.grid[rows] == nil {
			g.grid[rows] = make([]TileType, MapWidth)
		}

		switch r {
		case '1':
			g.grid[rows][cols] = TileWall
		case '.':
			g.grid[rows][cols] = TileDot
		case '-':
			g.grid[rows][cols] = TileGate
		default:
			g.grid[rows][cols] = TileEmpty
		}
		cols++
	}

	// Initialize entities
	// Pacman starts at (14, 23) approx (based on classic map) -> 13.5 * TileSize?
	// Requirement: Initial positions MUST be exact multiples of TileSize.
	// Let's place Pacman at 14, 23 (1-indexed in map usually, let's check grid)
	// Row 23, Col 13/14.
	// Let's use (13, 23) (0-indexed) which is a dot in the map above.
	g.pacman = &Entity{
		x:         13 * TileSize,
		y:         23 * TileSize,
		dir:       DirNone,
		nextDir:   DirNone,
		color:     color.RGBA{255, 255, 0, 255},
		isPacman:  true,
		mouthDir:  0.1,
		mouthOpen: 0.0,
	}

	// Ghosts
	ghostColors := []color.RGBA{
		{255, 0, 0, 255},     // Red
		{255, 184, 255, 255}, // Pink
		{0, 255, 255, 255},   // Cyan
		{255, 184, 82, 255},  // Orange
	}

	// Ghost house center is around 13, 14
	startPositions := [][2]float64{
		{13, 11}, // Red (Outside)
		{13, 14}, // Pink (Inside)
		{11, 14}, // Cyan (Inside)
		{15, 14}, // Orange (Inside)
	}

	for i, c := range ghostColors {
		g.ghosts = append(g.ghosts, &Entity{
			x:     startPositions[i][0] * TileSize,
			y:     startPositions[i][1] * TileSize,
			dir:   DirLeft, // Start moving
			color: c,
		})
		if i == 0 {
			g.ghosts[i].dir = DirLeft // Red starts moving left
		} else {
			// Others start moving up/down/randomly to get out
			if g.rand.Intn(2) == 0 {
				g.ghosts[i].dir = DirUp
			} else {
				g.ghosts[i].dir = DirDown
			}
		}
	}

	return g
}

func (g *Game) Update() error {
	if inpututil.IsKeyJustPressed(ebiten.KeyQ) {
		os.Exit(0)
	}
	if inpututil.IsKeyJustPressed(ebiten.KeyF) {
		ebiten.SetFullscreen(!ebiten.IsFullscreen())
	}
	if inpututil.IsKeyJustPressed(ebiten.KeyEnter) && g.gameOver {
		*g = *NewGame() // Restart
		return nil
	}
	if inpututil.IsKeyJustPressed(ebiten.KeyP) {
		g.paused = !g.paused
	}

	if g.gameOver || g.paused {
		return nil
	}

	// Pacman Input
	if ebiten.IsKeyPressed(ebiten.KeyArrowUp) {
		g.pacman.nextDir = DirUp
	} else if ebiten.IsKeyPressed(ebiten.KeyArrowDown) {
		g.pacman.nextDir = DirDown
	} else if ebiten.IsKeyPressed(ebiten.KeyArrowLeft) {
		g.pacman.nextDir = DirLeft
	} else if ebiten.IsKeyPressed(ebiten.KeyArrowRight) {
		g.pacman.nextDir = DirRight
	}

	// Update Pacman
	g.updateEntity(g.pacman)

	// Check Dot Collision
	cx, cy := g.pacman.x+TileSize/2, g.pacman.y+TileSize/2
	col, row := int(cx/TileSize), int(cy/TileSize)
	if row >= 0 && row < MapHeight && col >= 0 && col < MapWidth {
		if g.grid[row][col] == TileDot {
			g.grid[row][col] = TileEmpty
			g.score += 10
		}
	}

	// Update Ghosts
	for _, ghost := range g.ghosts {
		g.updateGhostAI(ghost)
		g.updateEntity(ghost)

		// Collision with Pacman
		// Simple AABB or distance check. Since they are same size, distance < size works.
		dist := math.Hypot(g.pacman.x-ghost.x, g.pacman.y-ghost.y)
		if dist < TileSize-4 { // slightly forgiving
			g.gameOver = true
		}
	}

	// Animate Mouth
	g.pacman.mouthOpen += g.pacman.mouthDir
	if g.pacman.mouthOpen > 0.8 || g.pacman.mouthOpen < 0 {
		g.pacman.mouthDir *= -1
	}

	return nil
}

func (g *Game) updateEntity(e *Entity) {
	// Check if centered
	centeredX := math.Mod(e.x, TileSize) == 0
	centeredY := math.Mod(e.y, TileSize) == 0
	centered := centeredX && centeredY

	if centered {
		// Try to change direction if buffered
		if e.nextDir != DirNone {
			if !g.isWall(e.x, e.y, e.nextDir) {
				e.dir = e.nextDir
				e.nextDir = DirNone
			}
		}

		// Check if current direction hits a wall
		if g.isWall(e.x, e.y, e.dir) {
			e.dir = DirNone // Stop
		}
	}

	// Move
	switch e.dir {
	case DirUp:
		e.y -= Speed
	case DirDown:
		e.y += Speed
	case DirLeft:
		e.x -= Speed
	case DirRight:
		e.x += Speed
	}

	// Wrap around
	if e.x < -TileSize {
		e.x = ScreenWidth
	} else if e.x > ScreenWidth {
		e.x = -TileSize
	}

	// Re-align if we overshot center and stopped/turned (simple correction for high speeds, though 3 divides 24 perfectly so we should be fine)
	// With Speed=3 and TileSize=24, we always land on multiples of 3. 24 is multiple of 3.
	// So we will hit exact center.
}

func (g *Game) updateGhostAI(e *Entity) {
	centeredX := math.Mod(e.x, TileSize) == 0
	centeredY := math.Mod(e.y, TileSize) == 0
	centered := centeredX && centeredY

	if centered {
		// Get valid directions
		opts := []Direction{}
		if !g.isWall(e.x, e.y, DirUp) {
			opts = append(opts, DirUp)
		}
		if !g.isWall(e.x, e.y, DirDown) {
			opts = append(opts, DirDown)
		}
		if !g.isWall(e.x, e.y, DirLeft) {
			opts = append(opts, DirLeft)
		}
		if !g.isWall(e.x, e.y, DirRight) {
			opts = append(opts, DirRight)
		}

		// Filter out reverse direction unless it's the only option
		reverse := DirNone
		switch e.dir {
		case DirUp:
			reverse = DirDown
		case DirDown:
			reverse = DirUp
		case DirLeft:
			reverse = DirRight
		case DirRight:
			reverse = DirLeft
		}

		validOpts := []Direction{}
		for _, d := range opts {
			if d != reverse {
				validOpts = append(validOpts, d)
			}
		}

		if len(validOpts) > 0 {
			// If we are at an intersection (more than 1 valid option) OR we hit a wall (current dir not in opts), pick random
			isIntersection := len(validOpts) > 1
			hitWall := g.isWall(e.x, e.y, e.dir)

			if isIntersection || hitWall {
				e.dir = validOpts[g.rand.Intn(len(validOpts))]
			}
			// Else keep going straight
		} else if len(opts) > 0 {
			// Only reverse is available (dead end)
			e.dir = opts[0]
		} else {
			// Stuck? Should not happen in this map
			e.dir = DirNone
		}
	}
}

func (g *Game) isWall(x, y float64, dir Direction) bool {
	nextX, nextY := x, y
	switch dir {
	case DirUp:
		nextY -= TileSize
	case DirDown:
		nextY += TileSize
	case DirLeft:
		nextX -= TileSize
	case DirRight:
		nextX += TileSize
	}

	// Center of the next tile
	cx, cy := nextX+TileSize/2, nextY+TileSize/2
	col, row := int(cx/TileSize), int(cy/TileSize)

	// Bounds check (allow wrapping logic to handle out of bounds x, but here we check grid)
	if col < 0 || col >= MapWidth {
		// If out of bounds X, it's the tunnel, so NOT a wall.
		return false
	}
	if row < 0 || row >= MapHeight {
		return true
	}

	tile := g.grid[row][col]
	return tile == TileWall
}

func (g *Game) Draw(screen *ebiten.Image) {
	// Draw Map
	for r := 0; r < MapHeight; r++ {
		for c := 0; c < MapWidth; c++ {
			x, y := float32(c*TileSize), float32(r*TileSize)
			switch g.grid[r][c] {
			case TileWall:
				vector.FillRect(screen, x, y, TileSize, TileSize, color.RGBA{0, 0, 150, 255}, false)
				// Draw inner line for detail? Keep it simple as requested.
				vector.StrokeRect(screen, x+4, y+4, TileSize-8, TileSize-8, 2, color.RGBA{0, 0, 255, 255}, false)
			case TileDot:
				vector.FillCircle(screen, x+TileSize/2, y+TileSize/2, 3, color.White, true)
			case TileGate:
				vector.FillRect(screen, x, y+TileSize/2-2, TileSize, 4, color.RGBA{255, 182, 255, 255}, false)
			}
		}
	}

	// Draw Pacman
	g.drawPacman(screen)

	// Draw Ghosts
	for _, ghost := range g.ghosts {
		g.drawGhost(screen, ghost)
	}

	// Draw UI
	ebitenutil.DebugPrint(screen, fmt.Sprintf("Score: %d  FPS: %.2f", g.score, ebiten.ActualFPS()))
	if g.gameOver {
		ebitenutil.DebugPrintAt(screen, "GAME OVER\nPress Enter to Restart", ScreenWidth/2-60, ScreenHeight/2)
	}
	if g.paused {
		ebitenutil.DebugPrintAt(screen, "PAUSED", ScreenWidth/2-20, ScreenHeight/2+20)
	}
}

func (g *Game) drawPacman(screen *ebiten.Image) {
	cx, cy := float32(g.pacman.x+TileSize/2), float32(g.pacman.y+TileSize/2)
	radius := float32(TileSize/2 - 2)

	var path vector.Path

	// Calculate angles for mouth
	angle := float32(0)
	switch g.pacman.dir {
	case DirRight:
		angle = 0
	case DirDown:
		angle = 90
	case DirLeft:
		angle = 180
	case DirUp:
		angle = 270
	}

	// Convert degrees to radians
	startAngle := (angle + float32(g.pacman.mouthOpen)*45) * math.Pi / 180
	endAngle := (angle + 360 - float32(g.pacman.mouthOpen)*45) * math.Pi / 180

	path.MoveTo(cx, cy)
	path.Arc(cx, cy, radius, startAngle, endAngle, vector.Clockwise)
	path.Close()

	// Actually FillPath uses FillOptions.
	fillOp := &vector.FillOptions{}

	drawOp := &vector.DrawPathOptions{}
	drawOp.ColorScale.ScaleWithColor(g.pacman.color)

	vector.FillPath(screen, &path, fillOp, drawOp)
}

func (g *Game) drawGhost(screen *ebiten.Image, e *Entity) {
	cx, cy := float32(e.x+TileSize/2), float32(e.y+TileSize/2)
	r := float32(TileSize/2 - 2)

	// Body (Circle top, Rect bottom)
	vector.FillCircle(screen, cx, cy-2, r, e.color, true)
	vector.FillRect(screen, float32(e.x)+2, float32(e.y)+TileSize/2, float32(TileSize)-4, float32(TileSize)/2, e.color, true)

	// Eyes
	eyeColor := color.White
	pupilColor := color.RGBA{0, 0, 50, 255}

	eyeOffsetX, eyeOffsetY := float32(4), float32(-4)

	// Look direction
	pupilOffsetX, pupilOffsetY := float32(0), float32(0)
	switch e.dir {
	case DirUp:
		pupilOffsetY = -2
	case DirDown:
		pupilOffsetY = 2
	case DirLeft:
		pupilOffsetX = -2
	case DirRight:
		pupilOffsetX = 2
	}

	// Left Eye
	vector.FillCircle(screen, cx-eyeOffsetX, cy+eyeOffsetY, 3, eyeColor, true)
	vector.FillCircle(screen, cx-eyeOffsetX+pupilOffsetX, cy+eyeOffsetY+pupilOffsetY, 1.5, pupilColor, true)

	// Right Eye
	vector.FillCircle(screen, cx+eyeOffsetX, cy+eyeOffsetY, 3, eyeColor, true)
	vector.FillCircle(screen, cx+eyeOffsetX+pupilOffsetX, cy+eyeOffsetY+pupilOffsetY, 1.5, pupilColor, true)
}

func (g *Game) Layout(outsideWidth, outsideHeight int) (int, int) {
	return ScreenWidth, ScreenHeight
}

func main() {
	ebiten.SetWindowSize(ScreenWidth, ScreenHeight)
	ebiten.SetWindowTitle("Pac-Man Go")

	game := NewGame()

	if err := ebiten.RunGame(game); err != nil {
		log.Fatal(err)
	}
}
