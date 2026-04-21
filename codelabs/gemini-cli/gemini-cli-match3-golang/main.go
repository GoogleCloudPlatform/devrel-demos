package main

import (
	"fmt"
	"image"
	"image/color"
	_ "image/jpeg"
	_ "image/png"
	"log"
	"math"
	"math/rand"
	"time"

	"github.com/hajimehoshi/ebiten/v2"
	"github.com/hajimehoshi/ebiten/v2/audio"
	"github.com/hajimehoshi/ebiten/v2/audio/mp3"
	"github.com/hajimehoshi/ebiten/v2/ebitenutil"
	"github.com/hajimehoshi/ebiten/v2/inpututil"
	"github.com/hajimehoshi/ebiten/v2/text"
	"golang.org/x/image/font"
	"golang.org/x/image/font/gofont/gomono"
	"golang.org/x/image/font/opentype"
)

const (
	screenWidth  = 1024
	screenHeight = 768
	gridSize     = 8
	gemSize      = 64
	gridOffsetX  = 80
	gridOffsetY  = (screenHeight - 512) / 2
	sidePanelX   = 650
	sidePanelY   = gridOffsetY
	sidePanelW   = 320
	sidePanelH   = 512
	geminiType   = 6 // Special Gemini gem
)

type GameState int

const (
	StateIntro GameState = iota
	StateTitle
	StateNameEntry
	StatePlaying
	StateAnimating
	StateGameOver
	StateLeaderboard
	StateAbout
	StateDemo
)

type ScoreEntry struct {
	Name  string
	Score int
}

type FloatingText struct {
	Text  string
	X, Y  float64
	Alpha float64
	Timer float64
	Color color.Color
}

type Gem struct {
	Type int
	X, Y float64 // Current drawing position
	TargetX, TargetY float64 // Target position for animation
	IsMatched bool
	Alpha float64 // For fade out animation
}

type Game struct {
	grid [gridSize][gridSize]*Gem
	sprites []*ebiten.Image
	geminiSprite *ebiten.Image
	background *ebiten.Image
	qrcode *ebiten.Image
	logo *ebiten.Image
	score int
	highScore int
	timer float64
	state GameState
	lastState GameState
	
	playerName string
	leaderboard []ScoreEntry
	
	comboMultiplier int
	floatingTexts []FloatingText
	
	// Intro Animation
	introTimer   float64
	introBgAlpha float64
	logoY        float64
	logoFinalY   float64

	// Demo Mode
	demoMoveCount     int
	demoNextMoveTimer float64
	demoRand          *rand.Rand
	
	// Leaderboard animation
	lbVisibleEntries int
	lbEntryAlpha float64
	lbTimer float64
	
	// Virtual Keyboard
	vkCurrentRow int
	vkCurrentCol int
	vkKeys [][]string
	
	cursorX, cursorY int
	selectedX, selectedY int
	isGemSelected bool
	
	fontTitle font.Face
	fontNormal font.Face
	fontBold font.Face
	fontBigBold font.Face
	
	showQRCode        bool
	accessibilityMode bool
	highContrastColors []color.RGBA
	
	audioContext *audio.Context
	matchSound   []byte
	
	titleMusic      *audio.Player
	nameEntryMusic  *audio.Player
	gameplayMusic   *audio.Player
	gameOverMusic   *audio.Player
	currentMusic    *audio.Player
	
	ticks int
	lastUpdate time.Time
}

func (g *Game) init() {
	g.score = 0
	g.timer = 60
	g.isGemSelected = false
	g.cursorX = 0
	g.cursorY = 0
	g.playerName = ""
	g.comboMultiplier = 1
	
	// Calculate logoFinalY once
	if g.logo != nil {
		lw, lh := g.logo.Bounds().Dx(), g.logo.Bounds().Dy()
		// Target logo area is top 2/3. +50% from 1.5 -> 2.25.
		scale := 2.25 * 0.75 * float64(screenWidth) / float64(lw)
		// Ensure it fits within 95% of the top 2/3 height
		maxH := 0.95 * float64(screenHeight*2/3)
		if float64(lh)*scale > maxH {
			scale = maxH / float64(lh)
		}
		// Center vertically within the top 2/3
		g.logoFinalY = (float64(screenHeight*2/3) - float64(lh)*scale) / 2
	} else {
		g.logoFinalY = 100
	}
	
	g.logoY = -600
	g.introTimer = 0
	g.introBgAlpha = 0
	g.showQRCode = true
	
	if g.vkKeys == nil {
		g.vkKeys = [][]string{
			{"1", "2", "3", "4", "5", "6", "7", "8", "9", "0"},
			{"Q", "W", "E", "R", "T", "Y", "U", "I", "O", "P"},
			{"A", "S", "D", "F", "G", "H", "J", "K", "L", "-"},
			{"Z", "X", "C", "V", "B", "N", "M", "_", "DEL", "OK"},
		}
	}
	
	// Initialize grid with random standard gems, ensuring no matches at start
	for y := 0; y < gridSize; y++ {
		for x := 0; x < gridSize; x++ {
			for {
				t := rand.Intn(6) // Only 0-5 are standard gems
				if (x >= 2 && g.grid[y][x-1].Type == t && g.grid[y][x-2].Type == t) ||
				   (y >= 2 && g.grid[y-1][x].Type == t && g.grid[y-2][x].Type == t) {
					continue
				}
				g.grid[y][x] = &Gem{
					Type: t,
					X: float64(x * gemSize),
					Y: float64(y * gemSize),
					TargetX: float64(x * gemSize),
					TargetY: float64(y * gemSize),
					Alpha: 1.0,
				}
				break
			}
		}
	}
}

func (g *Game) Update() error {
	if inpututil.IsKeyJustPressed(ebiten.KeyF) {
		ebiten.SetFullscreen(!ebiten.IsFullscreen())
	}
	if inpututil.IsKeyJustPressed(ebiten.KeyQ) {
		g.showQRCode = !g.showQRCode
	}
	// Only toggle accessibility in Playing or Animating states
	if (g.state == StatePlaying || g.state == StateAnimating) && inpututil.IsKeyJustPressed(ebiten.KeyA) {
		g.accessibilityMode = !g.accessibilityMode
	}
	g.ticks++
	
	g.updateMusic()

	switch g.state {
	case StateIntro:
		g.updateIntro()
	case StateTitle:
		g.updateTitle()
	case StateNameEntry:
		g.updateNameEntry()
	case StatePlaying:
		g.updatePlaying()
	case StateAnimating:
		g.updateAnimating()
	case StateGameOver:
		g.updateGameOver()
	case StateLeaderboard:
		g.updateLeaderboard()
	case StateAbout:
		g.updateAbout()
	case StateDemo:
		g.updateDemo()
	}
	
	if g.state == StatePlaying || g.state == StateAnimating {
		g.timer -= 1.0 / 60.0
		if g.timer <= 0 {
			g.timer = 0
			g.state = StateGameOver
		}
	}

	// Update floating texts
	newFT := []FloatingText{}
	for i := range g.floatingTexts {
		g.floatingTexts[i].Y -= 1.0 // Rise up
		g.floatingTexts[i].Alpha -= 0.02
		g.floatingTexts[i].Timer -= 1.0 / 60.0
		if g.floatingTexts[i].Alpha > 0 {
			newFT = append(newFT, g.floatingTexts[i])
		}
	}
	g.floatingTexts = newFT

	return nil
}

func (g *Game) addFloatingText(txt string, x, y float64, clr color.Color) {
	g.floatingTexts = append(g.floatingTexts, FloatingText{
		Text:  txt,
		X:     x,
		Y:     y,
		Alpha: 1.0,
		Timer: 1.0,
		Color: clr,
	})
}

func (g *Game) generateWoosh() {
	const sampleRate = 44100
	const duration = 0.2
	const numSamples = int(sampleRate * duration)
	g.matchSound = make([]byte, numSamples*4) // 16-bit stereo = 4 bytes per sample

	for i := 0; i < numSamples; i++ {
		t := float64(i) / sampleRate
		// Frequency sweep from 880Hz down to 220Hz
		freq := 880.0 - (660.0 * (float64(i) / float64(numSamples)))
		// Fade out envelope
		amp := 0.2 * (1.0 - float64(i)/float64(numSamples))
		v := math.Sin(2.0 * math.Pi * freq * t) * amp
		
		sample := int16(v * 32767)
		// Left channel
		g.matchSound[i*4] = byte(sample)
		g.matchSound[i*4+1] = byte(sample >> 8)
		// Right channel
		g.matchSound[i*4+2] = byte(sample)
		g.matchSound[i*4+3] = byte(sample >> 8)
	}
}

func (g *Game) playMatchSound() {
	if g.audioContext == nil || g.matchSound == nil {
		return
	}
	p := g.audioContext.NewPlayerFromBytes(g.matchSound)
	p.Play()
}

func (g *Game) updateMusic() {
	var targetMusic *audio.Player
	switch g.state {
	case StateTitle, StateIntro:
		targetMusic = g.titleMusic
	case StateNameEntry:
		targetMusic = g.nameEntryMusic
	case StatePlaying, StateAnimating:
		targetMusic = g.gameplayMusic
	case StateGameOver, StateLeaderboard:
		targetMusic = g.gameOverMusic
	}

	if g.currentMusic != targetMusic {
		if g.currentMusic != nil {
			g.currentMusic.Pause()
		}
		g.currentMusic = targetMusic
		if g.currentMusic != nil {
			g.currentMusic.Rewind()
			g.currentMusic.Play()
		}
	}
}

func (g *Game) updateIntro() {
	g.introTimer += 1.0 / 60.0
	
	if g.introTimer > 5.0 && g.introTimer <= 7.2 {
		// Stage 2: Bg fade in (10% slower = 2.2s)
		g.introBgAlpha = (g.introTimer - 5.0) / 2.2
		
		// Logo drop with bouncy effect
		t := (g.introTimer - 5.0) / 2.2
		startYS := -600.0 // Start well off-screen
		g.logoY = startYS + (g.logoFinalY - startYS)*g.easeOutElastic(t)
	} else if g.introTimer > 7.2 {
		g.introBgAlpha = 1.0
		g.logoY = g.logoFinalY
		
		// Wait 2s after bounce is done before showing title (7.2 + 2.0 = 9.2)
		if g.introTimer > 9.2 {
			g.state = StateTitle
		}
	}
}

func (g *Game) startDemo() {
	g.state = StateDemo
	g.demoMoveCount = 0
	g.demoNextMoveTimer = 1.0
	// Fixed seed for deterministic demo
	g.demoRand = rand.New(rand.NewSource(42))
	g.initDemoGrid()
}

func (g *Game) initDemoGrid() {
	// Initialize grid with the demo seed's RNG
	for y := 0; y < gridSize; y++ {
		for x := 0; x < gridSize; x++ {
			for {
				t := g.demoRand.Intn(6)
				if (x >= 2 && g.grid[y][x-1].Type == t && g.grid[y][x-2].Type == t) ||
				   (y >= 2 && g.grid[y-1][x].Type == t && g.grid[y-2][x].Type == t) {
					continue
				}
				g.grid[y][x] = &Gem{
					Type: t,
					X: float64(x * gemSize),
					Y: float64(y * gemSize),
					TargetX: float64(x * gemSize),
					TargetY: float64(y * gemSize),
					Alpha: 1.0,
				}
				break
			}
		}
	}
}

func (g *Game) updateTitle() {
	if inpututil.IsKeyJustPressed(ebiten.KeySpace) || g.justClicked() {
		g.state = StateNameEntry
		return
	}

	// Intro timer continues while in Title state to trigger Demo
	g.introTimer += 1.0 / 60.0
	// 9.2 (start of title) + 10.0 (demo timer) = 19.2
	if g.introTimer > 19.2 {
		g.startDemo()
	}
}

func (g *Game) easeOutElastic(t float64) float64 {
	const c4 = (2 * math.Pi) / 3
	if t == 0 { return 0 }
	if t == 1 { return 1 }
	return math.Pow(2, -10*t)*math.Sin((t*10-0.75)*c4) + 1
}

func (g *Game) justClicked() bool {
	if inpututil.IsMouseButtonJustPressed(ebiten.MouseButtonLeft) {
		return true
	}
	touchIDs := inpututil.AppendJustPressedTouchIDs(nil)
	return len(touchIDs) > 0
}

func (g *Game) updateNameEntry() {
	// Virtual Keyboard Mouse/Touch
	if clicked, mx, my := g.getClickPos(); clicked {
		// Calculate key from mx, my
		kbW := 800
		kbH := 320
		kbX := (screenWidth - kbW) / 2
		kbY := screenHeight - kbH - 50
		
		if mx >= kbX && mx < kbX+kbW && my >= kbY && my < kbY+kbH {
			col := (mx - kbX) / (kbW / 10)
			row := (my - kbY) / (kbH / 4)
			if row >= 0 && row < 4 && col >= 0 && col < 10 {
				g.handleKey(g.vkKeys[row][col])
			}
		}
	}

	// Keyboard input
	for _, k := range inpututil.AppendJustPressedKeys(nil) {
		if k >= ebiten.KeyA && k <= ebiten.KeyZ {
			g.handleKey(string('A' + (k - ebiten.KeyA)))
		} else if k >= ebiten.Key0 && k <= ebiten.Key9 {
			g.handleKey(string('0' + (k - ebiten.Key0)))
		} else if k == ebiten.KeyBackspace {
			g.handleKey("DEL")
		} else if k == ebiten.KeyEnter {
			g.handleKey("OK")
		}
	}
}

func (g *Game) handleKey(key string) {
	if key == "DEL" {
		if len(g.playerName) > 0 {
			g.playerName = g.playerName[:len(g.playerName)-1]
		}
	} else if key == "OK" {
		if len(g.playerName) > 0 {
			g.state = StatePlaying
		}
	} else {
		if len(g.playerName) < 10 {
			g.playerName += key
		}
	}
}

func (g *Game) getClickPos() (bool, int, int) {
	if inpututil.IsMouseButtonJustPressed(ebiten.MouseButtonLeft) {
		x, y := ebiten.CursorPosition()
		return true, x, y
	}
	touchIDs := inpututil.AppendJustPressedTouchIDs(nil)
	if len(touchIDs) > 0 {
		x, y := ebiten.TouchPosition(touchIDs[0])
		return true, x, y
	}
	return false, 0, 0
}

func (g *Game) updateDemo() {
	if g.justClicked() || inpututil.IsKeyJustPressed(ebiten.KeySpace) {
		g.state = StateIntro
		g.introTimer = 0
		g.init()
		return
	}

	if g.demoMoveCount >= 10 {
		g.state = StateIntro
		g.introTimer = 0
		g.init()
		return
	}

	g.demoNextMoveTimer -= 1.0 / 60.0
	if g.demoNextMoveTimer <= 0 {
		g.performDemoMove()
		g.demoNextMoveTimer = 1.5
	}
}

func (g *Game) performDemoMove() {
	type move struct{ x1, y1, x2, y2 int }
	var moves []move

	for y := 0; y < gridSize; y++ {
		for x := 0; x < gridSize; x++ {
			// Try right
			if x < gridSize-1 {
				g.grid[y][x], g.grid[y][x+1] = g.grid[y][x+1], g.grid[y][x]
				if g.hasMatches() { moves = append(moves, move{x, y, x + 1, y}) }
				g.grid[y][x], g.grid[y][x+1] = g.grid[y][x+1], g.grid[y][x]
			}
			// Try down
			if y < gridSize-1 {
				g.grid[y][x], g.grid[y+1][x] = g.grid[y+1][x], g.grid[y][x]
				if g.hasMatches() { moves = append(moves, move{x, y, x, y + 1}) }
				g.grid[y][x], g.grid[y+1][x] = g.grid[y+1][x], g.grid[y][x]
			}
		}
	}

	if len(moves) > 0 {
		m := moves[g.demoRand.Intn(len(moves))]
		g.selectedX, g.selectedY = m.x1, m.y1
		g.trySwap(m.x2, m.y2)
		g.demoMoveCount++
	}
}

func (g *Game) updateAbout() {
	if g.justClicked() || inpututil.IsKeyJustPressed(ebiten.KeySpace) || inpututil.IsKeyJustPressed(ebiten.KeyEnter) {
		g.state = g.lastState
	}
}

func (g *Game) updatePlaying() {
	// Mouse/Touch input
	clicked, mx, my := g.getClickPos()

	if clicked {
		// Check for ABOUT button
		if mx >= sidePanelX && mx < sidePanelX+sidePanelW && my >= sidePanelY+sidePanelH-50 && my < sidePanelY+sidePanelH {
			g.lastState = g.state
			g.state = StateAbout
			return
		}

		gx := (mx - gridOffsetX) / gemSize
		gy := (my - gridOffsetY) / gemSize
		
		if gx >= 0 && gx < gridSize && gy >= 0 && gy < gridSize {
			if g.isGemSelected {
				dx := int(math.Abs(float64(gx - g.selectedX)))
				dy := int(math.Abs(float64(gy - g.selectedY)))
				if (dx == 1 && dy == 0) || (dx == 0 && dy == 1) {
					g.trySwap(gx, gy)
				} else {
					g.selectedX = gx
					g.selectedY = gy
					g.cursorX = gx
					g.cursorY = gy
				}
			} else {
				g.isGemSelected = true
				g.selectedX = gx
				g.selectedY = gy
				g.cursorX = gx
				g.cursorY = gy
			}
		} else {
			g.isGemSelected = false
		}
	}

	// Cursor movement (Keyboard)
	if inpututil.IsKeyJustPressed(ebiten.KeyUp) {
		if g.isGemSelected {
			g.trySwap(g.cursorX, g.cursorY-1)
		} else {
			g.cursorY = (g.cursorY - 1 + gridSize) % gridSize
		}
	}
	if inpututil.IsKeyJustPressed(ebiten.KeyDown) {
		if g.isGemSelected {
			g.trySwap(g.cursorX, g.cursorY+1)
		} else {
			g.cursorY = (g.cursorY + 1) % gridSize
		}
	}
	if inpututil.IsKeyJustPressed(ebiten.KeyLeft) {
		if g.isGemSelected {
			g.trySwap(g.cursorX-1, g.cursorY)
		} else {
			g.cursorX = (g.cursorX - 1 + gridSize) % gridSize
		}
	}
	if inpututil.IsKeyJustPressed(ebiten.KeyRight) {
		if g.isGemSelected {
			g.trySwap(g.cursorX+1, g.cursorY)
		} else {
			g.cursorX = (g.cursorX + 1) % gridSize
		}
	}

	if inpututil.IsKeyJustPressed(ebiten.KeySpace) {
		g.isGemSelected = true
		g.selectedX = g.cursorX
		g.selectedY = g.cursorY
	}
}

func (g *Game) updateGameOver() {
	if inpututil.IsKeyJustPressed(ebiten.KeySpace) || g.justClicked() {
		// Save score to leaderboard
		g.leaderboard = append(g.leaderboard, ScoreEntry{Name: g.playerName, Score: g.score})
		// Sort and keep top 10
		for i := 0; i < len(g.leaderboard); i++ {
			for j := i + 1; j < len(g.leaderboard); j++ {
				if g.leaderboard[j].Score > g.leaderboard[i].Score {
					g.leaderboard[i], g.leaderboard[j] = g.leaderboard[j], g.leaderboard[i]
				}
			}
		}
		if len(g.leaderboard) > 10 {
			g.leaderboard = g.leaderboard[:10]
		}
		
		g.state = StateLeaderboard
		g.lbVisibleEntries = 0
		g.lbEntryAlpha = 0
		g.lbTimer = 0
	}
}

func (g *Game) updateLeaderboard() {
	g.lbTimer += 1.0 / 60.0
	
	if g.lbVisibleEntries < len(g.leaderboard) {
		g.lbEntryAlpha += 0.05
		if g.lbEntryAlpha >= 1.0 {
			g.lbEntryAlpha = 0
			g.lbVisibleEntries++
		}
	}
	
	if g.lbTimer >= 15.0 || g.justClicked() || inpututil.IsKeyJustPressed(ebiten.KeySpace) || inpututil.IsKeyJustPressed(ebiten.KeyEnter) {
		g.state = StateTitle
		g.init()
	}
}


func (g *Game) trySwap(nx, ny int) {
	if nx < 0 || nx >= gridSize || ny < 0 || ny >= gridSize {
		g.isGemSelected = false
		return
	}
	
	x1, y1 := g.selectedX, g.selectedY
	x2, y2 := nx, ny
	
	// Perform swap
	g.grid[y1][x1], g.grid[y2][x2] = g.grid[y2][x2], g.grid[y1][x1]
	
	if g.hasMatches() {
		g.state = StateAnimating
		g.grid[y1][x1].TargetX = float64(x1 * gemSize)
		g.grid[y1][x1].TargetY = float64(y1 * gemSize)
		g.grid[y2][x2].TargetX = float64(x2 * gemSize)
		g.grid[y2][x2].TargetY = float64(y2 * gemSize)
		g.isGemSelected = false
		g.cursorX = nx
		g.cursorY = ny
	} else {
		// Rollback swap
		g.grid[y1][x1], g.grid[y2][x2] = g.grid[y2][x2], g.grid[y1][x1]
		g.isGemSelected = false
	}
}

func (g *Game) hasMatches() bool {
	for y := 0; y < gridSize; y++ {
		for x := 0; x < gridSize; x++ {
			if g.checkMatch(x, y) {
				return true
			}
		}
	}
	return false
}

func (g *Game) checkMatch(x, y int) bool {
	t := g.grid[y][x].Type
	// Horizontal
	count := 1
	for i := x + 1; i < gridSize && g.grid[y][i].Type == t; i++ { count++ }
	for i := x - 1; i >= 0 && g.grid[y][i].Type == t; i-- { count++ }
	if count >= 3 { return true }
	
	// Vertical
	count = 1
	for i := y + 1; i < gridSize && g.grid[i][x].Type == t; i++ { count++ }
	for i := y - 1; i >= 0 && g.grid[i][x].Type == t; i-- { count++ }
	if count >= 3 { return true }
	
	return false
}

func (g *Game) updateAnimating() {
	moving := false
	const speed = 12.0
	for y := 0; y < gridSize; y++ {
		for x := 0; x < gridSize; x++ {
			gem := g.grid[y][x]
			if gem == nil { continue }
			
			dx := gem.TargetX - gem.X
			dy := gem.TargetY - gem.Y
			if math.Abs(dx) > speed {
				gem.X += math.Copysign(speed, dx)
				moving = true
			} else {
				gem.X = gem.TargetX
			}
			if math.Abs(dy) > speed {
				gem.Y += math.Copysign(speed, dy)
				moving = true
			} else {
				gem.Y = gem.TargetY
			}
		}
	}
	
	if !moving {
		if g.processMatches() {
			g.comboMultiplier++
			g.applyGravity()
		} else {
			g.comboMultiplier = 1
			g.state = StatePlaying
		}
	}
}

func (g *Game) processMatches() bool {
	type matchInfo struct {
		x, y, count, t int
		horizontal bool
	}
	matches := []matchInfo{}
	
	// Detect horizontal matches
	for y := 0; y < gridSize; y++ {
		for x := 0; x < gridSize-2; {
			t := g.grid[y][x].Type
			count := 1
			for i := x + 1; i < gridSize && g.grid[y][i].Type == t; i++ {
				count++
			}
			if count >= 3 {
				matches = append(matches, matchInfo{x, y, count, t, true})
				x += count
			} else {
				x++
			}
		}
	}
	
	// Detect vertical matches
	for x := 0; x < gridSize; x++ {
		for y := 0; y < gridSize-2; {
			t := g.grid[y][x].Type
			count := 1
			for i := y + 1; i < gridSize && g.grid[i][x].Type == t; i++ {
				count++
			}
			if count >= 3 {
				matches = append(matches, matchInfo{x, y, count, t, false})
				y += count
			} else {
				y++
			}
		}
	}
	
	if len(matches) == 0 { return false }
	
	g.playMatchSound()
	toRemove := make(map[[2]int]bool)
	spawnGemini := make(map[[2]int]bool)
	
	for _, m := range matches {
		// Gemini time bonus
		if m.t == geminiType {
			bonus := 0.0
			switch m.count {
			case 3: bonus = 5.0
			case 4: bonus = 10.0
			default: if m.count >= 5 { bonus = 15.0 }
			}
			g.timer += bonus
			g.addFloatingText(fmt.Sprintf("+%.0fs TIME!", bonus), float64(gridOffsetX + m.x*gemSize), float64(gridOffsetY + m.y*gemSize), color.RGBA{0, 255, 255, 255})
		}
		
		// Gemini spawning for non-Gemini matches of 4+
		if m.t != geminiType && m.count >= 4 {
			spawnGemini[[2]int{m.x, m.y}] = true
			g.addFloatingText("GEMINI SPAWN!", float64(gridOffsetX + m.x*gemSize), float64(gridOffsetY + m.y*gemSize), color.RGBA{255, 215, 0, 255})
		}
		
		for i := 0; i < m.count; i++ {
			if m.horizontal {
				toRemove[[2]int{m.x + i, m.y}] = true
			} else {
				toRemove[[2]int{m.x, m.y + i}] = true
			}
		}
	}
	
	if g.comboMultiplier > 1 {
		// Add combo text near one of the matches
		m := matches[0]
		g.addFloatingText(fmt.Sprintf("COMBO x%d!", g.comboMultiplier), float64(gridOffsetX + m.x*gemSize), float64(gridOffsetY + m.y*gemSize - 20), color.RGBA{255, 255, 0, 255})
	}
	
	for pos := range toRemove {
		g.grid[pos[1]][pos[0]] = nil
		g.score += 10 * g.comboMultiplier
	}
	
	// Spawn the Gemini gems
	for pos := range spawnGemini {
		g.grid[pos[1]][pos[0]] = &Gem{
			Type: geminiType,
			X: float64(pos[0] * gemSize),
			Y: float64(pos[1] * gemSize),
			TargetX: float64(pos[0] * gemSize),
			TargetY: float64(pos[1] * gemSize),
			Alpha: 1.0,
		}
	}
	
	return true
}

func (g *Game) applyGravity() {
	for x := 0; x < gridSize; x++ {
		emptySlots := 0
		for y := gridSize - 1; y >= 0; y-- {
			if g.grid[y][x] == nil {
				emptySlots++
			} else if emptySlots > 0 {
				g.grid[y+emptySlots][x] = g.grid[y][x]
				g.grid[y+emptySlots][x].TargetY = float64((y + emptySlots) * gemSize)
				g.grid[y][x] = nil
			}
		}
		for i := 0; i < emptySlots; i++ {
			y := emptySlots - 1 - i
			var t int
			if g.state == StateDemo {
				t = g.demoRand.Intn(6)
			} else {
				t = rand.Intn(6)
			}
			g.grid[y][x] = &Gem{
				Type: t,
				X: float64(x * gemSize),
				Y: float64(- (i + 1) * gemSize),
				TargetX: float64(x * gemSize),
				TargetY: float64(y * gemSize),
				Alpha: 1.0,
			}
		}
	}
}

func (g *Game) Draw(screen *ebiten.Image) {
	switch g.state {
	case StateIntro:
		g.drawIntro(screen)
		return
	}

	// Draw background scaled to screen
	op := &ebiten.DrawImageOptions{}
	bw, bh := g.background.Bounds().Dx(), g.background.Bounds().Dy()
	op.GeoM.Scale(float64(screenWidth)/float64(bw), float64(screenHeight)/float64(bh))
	screen.DrawImage(g.background, op)
	
	switch g.state {
	case StateTitle:
		g.drawTitle(screen)
	case StateNameEntry:
		g.drawNameEntry(screen)
	case StatePlaying, StateAnimating:
		g.drawGame(screen)
	case StateGameOver:
		g.drawGame(screen)
		g.drawGameOver(screen)
	case StateLeaderboard:
		g.drawLeaderboard(screen)
	case StateAbout:
		g.drawAbout(screen)
	case StateDemo:
		g.drawDemo(screen)
	}
}

func (g *Game) drawDemo(screen *ebiten.Image) {
	// Draw background
	op := &ebiten.DrawImageOptions{}
	bw, bh := g.background.Bounds().Dx(), g.background.Bounds().Dy()
	op.GeoM.Scale(float64(screenWidth)/float64(bw), float64(screenHeight)/float64(bh))
	screen.DrawImage(g.background, op)

	g.drawGame(screen)

	// Flashing "DEMO MODE"
	if (g.ticks/20)%2 == 0 {
		g.centerText(screen, "DEMO MODE", g.fontBigBold, screenWidth/2, 50, color.RGBA{255, 0, 0, 255})
	}
	g.centerText(screen, "TAP OR PRESS SPACE TO SKIP", g.fontNormal, screenWidth/2, screenHeight-50, color.White)
}

func (g *Game) drawIntro(screen *ebiten.Image) {
	if g.introTimer <= 5.0 {
		// Stage 1: Black screen with text
		screen.Fill(color.Black)
		g.centerText(screen, "Cloud Developer Relations Presents", g.fontBold, screenWidth/2, screenHeight/2, color.White)
		
		// Small prompt to ensure interaction for audio
		if (g.ticks/30)%2 == 0 {
			g.centerText(screen, "CLICK ANYWHERE TO START", g.fontNormal, screenWidth/2, screenHeight-50, color.RGBA{150, 150, 150, 255})
		}
	} else {
		// Stage 2: Bg fade in
		op := &ebiten.DrawImageOptions{}
		bw, bh := g.background.Bounds().Dx(), g.background.Bounds().Dy()
		op.GeoM.Scale(float64(screenWidth)/float64(bw), float64(screenHeight)/float64(bh))
		op.ColorM.Scale(1, 1, 1, g.introBgAlpha)
		screen.DrawImage(g.background, op)
		
		// Draw Logo
		lw, lh := g.logo.Bounds().Dx(), g.logo.Bounds().Dy()
		// Target logo area is top 2/3. +50% size.
		scale := 2.25 * 0.75 * float64(screenWidth) / float64(lw)
		maxH := 0.95 * float64(screenHeight*2/3)
		if float64(lh)*scale > maxH {
			scale = maxH / float64(lh)
		}
		
		lop := &ebiten.DrawImageOptions{}
		lop.GeoM.Scale(scale, scale)
		lop.GeoM.Translate(float64(screenWidth-int(float64(lw)*scale))/2, g.logoY)
		lop.ColorM.Scale(1, 1, 1, g.introBgAlpha)
		screen.DrawImage(g.logo, lop)
	}
}

func (g *Game) drawTitle(screen *ebiten.Image) {
	// Draw Logo (+50% size)
	lw, lh := g.logo.Bounds().Dx(), g.logo.Bounds().Dy()
	// Target logo area is top 2/3
	scale := 2.25 * 0.75 * float64(screenWidth) / float64(lw)
	maxH := 0.95 * float64(screenHeight*2/3)
	if float64(lh)*scale > maxH {
		scale = maxH / float64(lh)
	}
	
	lop := &ebiten.DrawImageOptions{}
	lop.GeoM.Scale(scale, scale)
	// Center in top 2/3 using precalculated final Y
	lop.GeoM.Translate(float64(screenWidth-int(float64(lw)*scale))/2, g.logoFinalY)
	screen.DrawImage(g.logo, lop)
	
	// Wavy text (Center of Bottom 1/3)
	prompt := "PRESS SPACE TO START"
	charW := 35 
	startX := (screenWidth - len(prompt)*charW) / 2
	// Bottom 1/3 starts at 512, center is at 512 + 128 = 640
	baseY := 640.0 
	
	for i, r := range prompt {
		char := string(r)
		offset := math.Cos(float64(g.ticks)*0.1 + float64(i)*0.5) * 10
		text.Draw(screen, char, g.fontBold, startX + i*charW, int(baseY) + int(offset), color.White)
	}
}

func (g *Game) drawNameEntry(screen *ebiten.Image) {
	ebitenutil.DrawRect(screen, 0, 0, screenWidth, screenHeight, color.RGBA{0, 0, 0, 150})
	
	g.centerText(screen, "ENTER YOUR NAME", g.fontTitle, screenWidth/2, 150, color.White)
	
	// Display current name
	nameDisp := g.playerName
	if (g.ticks/30)%2 == 0 {
		nameDisp += "_"
	}
	g.centerText(screen, nameDisp, g.fontTitle, screenWidth/2, 250, color.RGBA{255, 215, 0, 255})
	
	// Draw virtual keyboard
	kbW := 800
	kbH := 320
	kbX := (screenWidth - kbW) / 2
	kbY := screenHeight - kbH - 50
	
	keyW := kbW / 10
	keyH := kbH / 4
	
	for r, row := range g.vkKeys {
		for c, key := range row {
			kx := kbX + c*keyW
			ky := kbY + r*keyH
			
			// Highlight key if mouse is over
			clr := color.RGBA{60, 60, 60, 200}
			mx, my := ebiten.CursorPosition()
			if mx >= kx && mx < kx+keyW && my >= ky && my < ky+keyH {
				clr = color.RGBA{100, 100, 100, 255}
			}
			
			ebitenutil.DrawRect(screen, float64(kx+2), float64(ky+2), float64(keyW-4), float64(keyH-4), clr)
			g.centerText(screen, key, g.fontNormal, kx + keyW/2, ky + keyH/2, color.White)
		}
	}
}

func (g *Game) drawGame(screen *ebiten.Image) {
	// Draw play area background
	ebitenutil.DrawRect(screen, gridOffsetX, gridOffsetY, gridSize*gemSize, gridSize*gemSize, color.White)
	
	// Draw gems
	for y := 0; y < gridSize; y++ {
		for x := 0; x < gridSize; x++ {
			gem := g.grid[y][x]
			if gem == nil { continue }
			
			gop := &ebiten.DrawImageOptions{}
			
			if gem.Type == geminiType {
				// Scale Gemini gem (1024x1024 to gemSize)
				sw, sh := g.geminiSprite.Bounds().Dx(), g.geminiSprite.Bounds().Dy()
				gop.GeoM.Scale(float64(gemSize)/float64(sw), float64(gemSize)/float64(sh))
				gop.GeoM.Translate(gridOffsetX + gem.X, gridOffsetY + gem.Y)
			} else {
				gop.GeoM.Translate(gridOffsetX + gem.X, gridOffsetY + gem.Y)
			}
			
			if g.accessibilityMode {
				c := g.highContrastColors[gem.Type]
				ebitenutil.DrawRect(screen, gridOffsetX + gem.X + 2, gridOffsetY + gem.Y + 2, gemSize - 4, gemSize - 4, c)
			} else {
				if gem.Type == geminiType {
					screen.DrawImage(g.geminiSprite, gop)
				} else {
					screen.DrawImage(g.sprites[gem.Type], gop)
				}
			}
		}
	}
	
	// Draw cursor (Golden pulsing square)
	pulse := math.Sin(float64(g.ticks)*0.1) * 2 // Pulse offset between -2 and 2
	cx, cy := float64(gridOffsetX + g.cursorX*gemSize) - pulse, float64(gridOffsetY + g.cursorY*gemSize) - pulse
	cw, ch := float64(gemSize) + pulse*2, float64(gemSize) + pulse*2
	
	gold := color.RGBA{255, 215, 0, 255}
	border := float64(4)
	
	// Top
	ebitenutil.DrawRect(screen, cx, cy, cw, border, gold)
	// Bottom
	ebitenutil.DrawRect(screen, cx, cy + ch - border, cw, border, gold)
	// Left
	ebitenutil.DrawRect(screen, cx, cy, border, ch, gold)
	// Right
	ebitenutil.DrawRect(screen, cx + cw - border, cy, border, ch, gold)
	
	if g.isGemSelected {
		sx, sy := float64(gridOffsetX + g.selectedX*gemSize), float64(gridOffsetY + g.selectedY*gemSize)
		ebitenutil.DrawRect(screen, sx, sy, gemSize, gemSize, color.RGBA{255, 255, 0, 100})
	}
	
	// Draw side panel
	ebitenutil.DrawRect(screen, sidePanelX, sidePanelY, sidePanelW, sidePanelH, color.RGBA{0, 0, 0, 180})
	
	// Draw UI text
	g.drawText(screen)

	// Draw floating texts
	for _, ft := range g.floatingTexts {
		clr := ft.Color.(color.RGBA)
		clr.A = uint8(ft.Alpha * 255)
		text.Draw(screen, ft.Text, g.fontBigBold, int(ft.X), int(ft.Y), clr)
	}
}

func (g *Game) drawGameOver(screen *ebiten.Image) {
	ebitenutil.DrawRect(screen, 0, 0, screenWidth, screenHeight, color.RGBA{0, 0, 0, 150})
	g.centerText(screen, "GAME OVER", g.fontTitle, screenWidth/2, screenHeight/2 - 50, color.White)
	g.centerText(screen, "Space to Save Score", g.fontNormal, screenWidth/2, screenHeight/2 + 20, color.White)
}

func (g *Game) drawAbout(screen *ebiten.Image) {
	ebitenutil.DrawRect(screen, 0, 0, screenWidth, screenHeight, color.RGBA{0, 0, 0, 220})
	g.centerText(screen, "ABOUT CLOUD CRUSH", g.fontTitle, screenWidth/2, 100, color.RGBA{255, 215, 0, 255})
	
	lines := []string{
		"This game was autonomously generated",
		"using Gemini CLI and Go with Ebitengine v2.",
		"",
		"Every asset, animation, and logic line",
		"was crafted through an interactive",
		"AI-driven development session.",
		"",
		"Built for Google Developer Relations",
		"to showcase modern Go game development.",
		"",
		"Press any key or click to return",
	}
	
	for i, line := range lines {
		g.centerText(screen, line, g.fontNormal, screenWidth/2, 200 + i*40, color.White)
	}
}

func (g *Game) drawLeaderboard(screen *ebiten.Image) {
	ebitenutil.DrawRect(screen, 0, 0, screenWidth, screenHeight, color.RGBA{0, 0, 0, 200})
	g.centerText(screen, "TOP CLOUD CRUSHERS", g.fontTitle, screenWidth/2, 100, color.RGBA{255, 215, 0, 255})
	
	for i := 0; i < g.lbVisibleEntries + 1 && i < len(g.leaderboard); i++ {
		alpha := uint8(255)
		if i == g.lbVisibleEntries {
			alpha = uint8(g.lbEntryAlpha * 255)
		}
		
		clr := color.RGBA{255, 255, 255, alpha}
		entry := g.leaderboard[i]
		txt := fmt.Sprintf("%2d. %-10s %d", i+1, entry.Name, entry.Score)
		g.centerText(screen, txt, g.fontNormal, screenWidth/2, 200 + i*40, clr)
	}
}


func (g *Game) drawText(screen *ebiten.Image) {
	title := "CLOUD CRUSH"
	scoreStr := fmt.Sprintf("Score: %d", g.score)
	highScoreStr := fmt.Sprintf("High: %d", g.highScore)
	timerStr := fmt.Sprintf("Time: %d", int(g.timer))
	
	g.centerText(screen, title, g.fontTitle, sidePanelX + sidePanelW/2, sidePanelY + 40, color.White)
	g.centerText(screen, scoreStr, g.fontNormal, sidePanelX + sidePanelW/2, sidePanelY + 100, color.White)
	g.centerText(screen, highScoreStr, g.fontNormal, sidePanelX + sidePanelW/2, sidePanelY + 140, color.White)
	g.centerText(screen, timerStr, g.fontNormal, sidePanelX + sidePanelW/2, sidePanelY + 180, color.RGBA{255, 200, 200, 255})
	
	if g.comboMultiplier > 1 {
		comboStr := fmt.Sprintf("COMBO x%d!", g.comboMultiplier)
		g.centerText(screen, comboStr, g.fontBold, sidePanelX + sidePanelW/2, sidePanelY + 220, color.RGBA{255, 255, 0, 255})
	}
	
	instructions := []string{
		"Arrows: Move",
		"Space: Select",
		"F: Fullscreen",
		"A: Accessibility",
		"Q: Toggle QR",
	}
	for i, line := range instructions {
		g.centerText(screen, line, g.fontNormal, sidePanelX + sidePanelW/2, sidePanelY + 240 + i*30, color.RGBA{200, 200, 200, 255})
	}
	
	if g.showQRCode && g.qrcode != nil {
		qop := &ebiten.DrawImageOptions{}
		// QR code reduced by 20% (300x0.8 = 240)
		qop.GeoM.Scale(0.8, 0.8)
		qop.GeoM.Translate(float64(sidePanelX + (sidePanelW-240)/2), float64(sidePanelY + sidePanelH - 300))
		screen.DrawImage(g.qrcode, qop)
	}

	// ABOUT button
	ebitenutil.DrawRect(screen, float64(sidePanelX+10), float64(sidePanelY+sidePanelH-50), float64(sidePanelW-20), 40, color.RGBA{100, 100, 100, 255})
	g.centerText(screen, "ABOUT", g.fontNormal, sidePanelX+sidePanelW/2, sidePanelY+sidePanelH-30, color.White)

	if g.state == StateGameOver {
		ebitenutil.DrawRect(screen, 0, 0, screenWidth, screenHeight, color.RGBA{0, 0, 0, 150})
		g.centerText(screen, "GAME OVER", g.fontTitle, screenWidth/2, screenHeight/2 - 50, color.White)
		g.centerText(screen, "Space to Save Score", g.fontNormal, screenWidth/2, screenHeight/2 + 20, color.White)
	}
}

func (g *Game) centerText(screen *ebiten.Image, str string, face font.Face, x, y int, clr color.Color) {
	bound, _ := font.BoundString(face, str)
	w := (bound.Max.X - bound.Min.X).Ceil()
	h := (bound.Max.Y - bound.Min.Y).Ceil()
	text.Draw(screen, str, face, x - w/2, y + h/2, clr)
}

func (g *Game) Layout(outsideWidth, outsideHeight int) (int, int) {
	return screenWidth, screenHeight
}

func main() {
	rand.Seed(time.Now().UnixNano())
	ebiten.SetWindowSize(screenWidth, screenHeight)
	ebiten.SetWindowTitle("Cloud Crush")
	
	g := &Game{}
	
	// Initialize Audio
	g.audioContext = audio.NewContext(44100)
	g.generateWoosh()
	
	// Load Music
	loadMusic := func(path string) *audio.Player {
		f, err := ebitenutil.OpenFile(path)
		if err != nil { log.Printf("failed to open music %s: %v", path, err); return nil }
		d, err := mp3.DecodeWithSampleRate(44100, f)
		if err != nil { log.Printf("failed to decode music %s: %v", path, err); return nil }
		s := audio.NewInfiniteLoop(d, d.Length())
		p, err := g.audioContext.NewPlayer(s)
		if err != nil { log.Printf("failed to create player for %s: %v", path, err); return nil }
		p.SetVolume(0.5)
		return p
	}

	g.titleMusic = loadMusic("assets/The_Winning_Sequence.mp3")
	g.nameEntryMusic = loadMusic("assets/Button_Masher_s_Dawn.mp3")
	g.gameplayMusic = loadMusic("assets/Insert_Three_Tokens.mp3")
	g.gameOverMusic = loadMusic("assets/Credit_Expired.mp3")
	
	// Load assets
	bgImg, _, err := ebitenutil.NewImageFromFile("assets/background.jpg")
	if err != nil { log.Fatal(err) }
	g.background = bgImg
	
	logoImg, _, err := ebitenutil.NewImageFromFile("assets/logo.png")
	if err != nil { log.Fatal(err) }
	g.logo = logoImg
	
	spriteSheet, _, err := ebitenutil.NewImageFromFile("assets/gcp_sprites.png")
	if err != nil { log.Fatal(err) }
	
	for i := 0; i < 6; i++ {
		g.sprites = append(g.sprites, spriteSheet.SubImage(image.Rect(i*64, 0, (i+1)*64, 64)).(*ebiten.Image))
	}

	geminiImg, _, err := ebitenutil.NewImageFromFile("assets/gemini.png")
	if err != nil { log.Fatal(err) }
	g.geminiSprite = geminiImg

	// Load QR code
	qrImg, _, err := ebitenutil.NewImageFromFile("public/qrcode.png")
	if err == nil {
		g.qrcode = qrImg
	} else {
		// Try without public/ prefix (for WASM)
		qrImg, _, err = ebitenutil.NewImageFromFile("qrcode.png")
		if err == nil {
			g.qrcode = qrImg
		}
	}
	
	// Load fonts
	tt, err := opentype.Parse(gomono.TTF)
	if err != nil { log.Fatal(err) }
	
	g.fontTitle, err = opentype.NewFace(tt, &opentype.FaceOptions{
		Size:    53,
		DPI:     72,
		Hinting: font.HintingFull,
	})
	if err != nil { log.Fatal(err) }
	
	g.fontNormal, err = opentype.NewFace(tt, &opentype.FaceOptions{
		Size:    26,
		DPI:     72,
		Hinting: font.HintingFull,
	})
	if err != nil { log.Fatal(err) }

	g.fontBold, err = opentype.NewFace(tt, &opentype.FaceOptions{
		Size:    26,
		DPI:     72,
		Hinting: font.HintingFull,
	})
	if err != nil { log.Fatal(err) }

	g.fontBigBold, err = opentype.NewFace(tt, &opentype.FaceOptions{
		Size:    40,
		DPI:     72,
		Hinting: font.HintingFull,
	})
	if err != nil { log.Fatal(err) }
	
	g.highContrastColors = []color.RGBA{
		{255, 0, 0, 255},   // Red
		{0, 255, 0, 255},   // Green
		{0, 0, 255, 255},   // Blue
		{255, 255, 0, 255}, // Yellow
		{255, 0, 255, 255}, // Magenta
		{0, 255, 255, 255}, // Cyan
		{255, 255, 255, 255}, // White (Gemini)
	}
	
	g.init()
	g.state = StateIntro
	
	ebiten.SetScreenClearedEveryFrame(true)
	if err := ebiten.RunGame(g); err != nil {
		log.Fatal(err)
	}
}
