# Cloud Crush - Match-3 Game in Go

Cloud Crush is a high-performance Match-3 game built with the [Ebitengine](https://ebitengine.org/) (v2) game engine. It features GCP-themed icons, smooth animations, procedural audio, and was autonomously generated using Gemini CLI.

## Features

- **GCP Themed**: Standard icons represent GCP products (Compute Engine, Cloud Storage, etc.).
- **Special Gemini Gem**: Matching 4+ gems spawns a Gemini gem that grants time bonuses.
- **Dynamic Intro**: Animated title sequence with bouncy logo physics.
- **Cross-Platform**: Runs natively and in modern web browsers via WebAssembly.
- **Mobile Friendly**: Supports touch/tap inputs and responsive scaling.
- **Side Panel**: Real-time scoring, high-score tracking, and integrated QR code for easy mobile sharing.
- **Leaderboard**: Top 10 high-score persistence with arcade-style fade animations.

## Local Development

### Prerequisites

- [Go](https://go.dev/dl/) 1.24 or later.
- Desktop audio drivers (ALSA on Linux, standard drivers on macOS/Windows).

### Run Locally

```bash
go run .
```

## WebAssembly Build

To compile the game for the browser:

1. Ensure `wasm_exec.js` is present in your project root (it's part of the Go distribution).
2. Build the WASM binary:

```bash
GOOS=js GOARCH=wasm go build -o public/cloud-crush.wasm .
```

3. Run the local Go server to serve the assets:

```bash
go run server/main.go
```

The game will be available at `http://localhost:8080`.

## Cloud Run Deployment

The project includes a multi-stage `Dockerfile` that compiles the WASM binary and the Go web server into a minimal production image.

### Deploy using gcloud

Navigate to the project directory and run:

```bash
gcloud run deploy cloud-crush \
  --source . \
  --project YOUR_PROJECT_ID \
  --region YOUR_REGION \
  --allow-unauthenticated
```

### Manual Container Build

If you prefer to build the image manually:

```bash
# Build the image
docker build -t gcr.io/YOUR_PROJECT_ID/cloud-crush .

# Push to Artifact Registry
docker push gcr.io/YOUR_PROJECT_ID/cloud-crush

# Deploy to Cloud Run
gcloud run deploy cloud-crush \
  --image gcr.io/YOUR_PROJECT_ID/cloud-crush \
  --platform managed
```

## Project Structure

- `main.go`: Primary game logic, rendering, and input handling.
- `server/main.go`: Minimal static file server for WASM deployment.
- `public/`: Assets served to the browser (WASM, HTML, JS, Images).
- `assets/`: Source game assets (Background, Sprites, MP3 music).
- `Dockerfile`: Multi-stage production build configuration.
