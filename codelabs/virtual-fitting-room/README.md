# Virtual Fitting Room & AI Stylist

A Flutter shopping app augmented with two Gemini-powered features:

1. **Virtual Try-On** — upload a photo, pick a clothing item, see an AI-generated image of yourself wearing it.
2. **AI Stylist** — describe a location and occasion, get three complete outfit suggestions (with try-on images) curated from a product catalog. Supports multi-turn refinement: "make it more casual" → three new outfits in the same conversation.

The backend is a multi-agent system built with the [Agent Development Kit for Go](https://github.com/google/adk-go). The frontend is Flutter. Everything runs locally in Cloud Shell or deploys to a single Cloud Run service.

## Architecture

```
Flutter Web App  ──── HTTP/REST (same origin) ────▶  ADK Go Backend (port 8080)
                                                            │
                                              ┌─────────────┼─────────────┐
                                              ▼             ▼             ▼
                                        Fitting Room   Catalog        Stylist
                                          Agent        Agent          Agent
                                                            │
                                                Vertex AI (Gemini) + Cloud Storage
```

| Component | Technology |
|---|---|
| Frontend | Flutter (Dart) — web build served by the Go backend on the same port |
| Agent framework | ADK for Go — multi-agent orchestration, sessions, artifacts |
| Reasoning models | `gemini-3.1-pro-preview` (fitting room, stylist), `gemini-3-flash-preview` (root, catalog) |
| Image generation | `gemini-2.5-flash-image` (try-on composition) |
| Storage | Google Cloud Storage (product catalog images + generated try-ons) |
| Hosting | Cloud Run (single service serves API + UI) |
| Auth | Application Default Credentials — one credential covers Vertex AI + GCS, no API keys |

## Repository layout

```
codelabs/virtual-fitting-room/
├── adk_backend/                  # Go backend (ADK agents + REST server)
│   ├── main.go                   # Entry point: wires agents, serves /api/ + /
│   ├── catalog/                  # Product catalog agent
│   ├── fittingroom/              # Virtual try-on agent + fitting_tool
│   ├── stylist/                  # Outfit-curation agent with multi-turn state
│   ├── rootagent/                # Routes requests to the right specialist
│   └── tools/                    # Shared tools (product image loader, CORS, etc.)
└── flutter_frontend/             # Flutter app (web/iOS/Android sources)
    └── lib/
        ├── core_app/             # Pre-built shopping app (browse, cart, etc.)
        └── workshop_tasks/       # AI feature code
            ├── step_1_try_it_on/   # Virtual try-on flow
            └── step_2_style_me/    # Stylist + feedback flow
```

## Running locally (Cloud Shell)

The backend serves both the API and the compiled Flutter web app on port 8080, so everything works through a single Cloud Shell Web Preview URL — no cross-origin headaches.

1. **Set up Google Cloud project + APIs**
   ```bash
   gcloud projects create YOUR_PROJECT_ID --name="Virtual Fitting Room"
   gcloud config set project YOUR_PROJECT_ID
   gcloud services enable \
     aiplatform.googleapis.com \
     storage.googleapis.com \
     run.googleapis.com \
     cloudbuild.googleapis.com \
     artifactregistry.googleapis.com
   ```

2. **Create a GCS bucket and upload product images**
   ```bash
   gcloud storage buckets create gs://fashion-app-$(gcloud config get-value project) \
     --location=us-central1 --uniform-bucket-level-access
   gcloud storage cp flutter_frontend/assets/images/*.png \
     gs://fashion-app-$(gcloud config get-value project)/catalog-assets/images/
   ```

3. **Configure `.env`**
   ```bash
   cd adk_backend
   cat > .env << EOF
   GOOGLE_CLOUD_PROJECT=$(gcloud config get-value project)
   GCS_BUCKET=fashion-app-$(gcloud config get-value project)
   EOF
   ```

4. **Set up Application Default Credentials**
   ```bash
   gcloud auth application-default login
   gcloud auth application-default set-quota-project $(gcloud config get-value project)
   ```

5. **Build the Flutter web bundle** (in a separate terminal)
   ```bash
   cd flutter_frontend
   flutter pub get
   flutter build web
   ```

6. **Run the backend**
   ```bash
   cd adk_backend
   ./run.sh
   ```

7. **Open** Cloud Shell Web Preview → **Preview on port 8080**. The Flutter shopping app loads, API calls go to `/api/` on the same host.

## Deploying to Cloud Run

```bash
# Bundle the Flutter web build into the backend's container source
cd flutter_frontend && flutter build web && cd ..
rm -rf adk_backend/flutter_web
cp -r flutter_frontend/build/web adk_backend/flutter_web

# Deploy (no API key passed — service account uses ADC)
cd adk_backend
PROJECT_ID=$(gcloud config get-value project)
gcloud run deploy fashion-app-backend \
  --source . \
  --region us-central1 \
  --allow-unauthenticated \
  --set-env-vars "GOOGLE_CLOUD_PROJECT=$PROJECT_ID,GCS_BUCKET=fashion-app-$PROJECT_ID" \
  --memory 1Gi --cpu 2 --timeout 300s
```

The deployed service URL serves both the Flutter UI (at `/`) and the API (at `/api/`). The default Compute Engine service account needs `roles/aiplatform.user` and `roles/storage.objectUser` on the project — usually covered by the default `Editor` role on new projects.

## Notable implementation details

- **Identity preservation across multiple parallel generations** — when the stylist generates three outfit try-ons in parallel, all three share the same SHA-256-derived seed (computed from the user image identifier) so the model's sampling collapses to the same face. The reference photo is placed at the *end* of the prompt with an explicit `=== IDENTITY ANCHOR ===` header for maximum attention.
- **Session-pinned user image** — a `BeforeAgentCallback` on the stylist captures the user's uploaded artifact name on first turn and pins it to session state. A `BeforeModelCallback` re-injects it on every subsequent model call, with explicit text forbidding the use of previously-generated `generated_fitting_*` artifacts as the identity source.
- **No API keys** — Vertex AI and Cloud Storage both authenticate via ADC. The `.env` file holds only the project ID and bucket name.
- **Same-origin Flutter** — `flutter_frontend/lib/app_config.dart` uses the relative URL `/api`, so the same build works locally, in Cloud Shell, and on Cloud Run without config edits.

## License

Apache License 2.0 — see the [LICENSE](../../LICENSE) at the repository root.
