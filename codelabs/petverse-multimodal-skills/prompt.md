# Role & Objective
You are an expert Google Cloud Principal Software Engineer & UI Architect. Your goal is to construct a production-ready Flask web application named **"PetVerse Profiles"** in the current directory (`~/petverse-profiles`), featuring a modern "Art Museum Gallery" aesthetic.

---

# System Context & Architecture
The application queries multimodal pet data, media metadata, and vector embeddings stored in a Google Cloud BigQuery dataset named `petverse`.

### Environment Constraints
- Dynamic environment variable configuration:
  - `PROJECT_ID`: Read via `os.environ.get('PROJECT_ID', os.environ.get('GCP_PROJECT'))`.
  - `REGION`: Read via `os.environ.get('REGION')`.
- All GCP service clients (`bigquery.Client` and `aiplatform.init`) must read from these environment variables.

---

# Application Specifications & Deliverables

Generate the complete project codebase comprising the exact files and structure detailed below:

### 1. `app.py` (Application Backend)
- **Imports**: `os`, `flask` (`Flask`, `render_template`, `request`), `google.cloud.bigquery`, `google.cloud.aiplatform`.
- **Initialization**:
  - Initialize BigQuery client with `PROJECT_ID`.
  - Initialize Vertex AI / Agent Platform with `aiplatform.init(project=PROJECT_ID, location=REGION)`.
- **Database Functions**:
  - `get_all_pets()`: Returns all pets ordered by Name (`SELECT Id, Name, Species, profile_picture FROM petverse.pets ORDER BY Name`).
  - `get_pet_details(pet_id)`: Fetches full single row from `petverse.pets` matching `Id = @pet_id` using parameterized `ScalarQueryParameter`.
  - `get_similar_pets(pet_id)`: Queries `petverse.profile_embeddings` using `COSINE_DISTANCE` join where distance < 0.5, returning up to 5 similar pets ordered by distance.
  - `search_pets_semantic(query)`: Performs vector similarity search using BigQuery SQL function `VECTOR_SEARCH(TABLE petverse.text_embeddings, ...)` with `ML.GENERATE_EMBEDDING` model `petverse.textembedding`.
- **Routes**:
  - `GET /`: Renders `index.html` with all pets.
  - `GET /pet/<int:pet_id>`: Renders `pet.html` with pet details and similar recommendations.
  - `GET /search`: Reads query parameter `query` and renders `search.html`.
- **Server Entrypoint**: `app.run(debug=True, host='0.0.0.0', port=int(os.environ.get('PORT', 8080)))`.

### 2. `requirements.txt` (Dependencies)
```text
Flask==3.1.3
google-cloud-bigquery==3.35.1
gunicorn==22.0.0
google-cloud-aiplatform==1.133.0
shapely>=2.0.0
```

### 3. `Dockerfile` (Container Configuration)
- Use base image `python:3.13-slim`.
- Set working directory `/app`.
- Copy and install `requirements.txt` with `--no-cache-dir`.
- Copy project files into container.
- Command: `CMD ["gunicorn", "--bind", "0.0.0.0:8080", "app:app"]`.

### 4. `static/css/style.css` (Styling System)
- Design System: "Modern Art Museum Gallery" theme.
- Clean typography utilizing font `Inter`, sans-serif.
- Neutral backdrop (`#fdfdfd`), dark charcoal headings (`#1a1a1a`), subtle border outlines (`#e0e0e0`).
- Responsive flexbox navigation header with interactive search input.
- Gallery cards formatted in auto-responsive CSS Grid with subtle elevation hover animations (`translateY(-5px)`).

### 5. HTML Templates (`templates/`)
- `base.html`: Main HTML5 shell, navigation header, search bar form submitting GET to `/search`, dynamic template block `{% block content %}`, and minimalist footer.
- `index.html`: Gallery page showcasing pet cards. Replace `gs://` in profile picture URIs with `https://storage.mtls.cloud.google.com/`.
- `pet.html`: Detailed view displaying pet photo portrait, metadata details (Species, Breed, Hobby, Favorite Food/Toy), adoption story, media gallery dynamically handling `<video>`, `<audio>`, or `<img>` elements based on URI file extension, and similar pet recommendations.
- `search.html`: Displays search results cards corresponding to the semantic query.

### 6. `deploy.sh` (Deployment Automation)
- Bash script to deploy the application container to Cloud Run:
  - Exports `SERVICE_NAME="petverse-profiles"`, `REPOSITORY_NAME="cloud-run-source-deploy"`, `REGION`, `PROJECT_ID`, and `IMAGE_URL`.
  - Verifies and creates Artifact Registry repository if non-existent.
  - Compiles container image via `gcloud builds submit --tag ${IMAGE_URL}`.
  - Deploys service to Cloud Run with `--no-allow-unauthenticated` and `--iap`.
  - Binds active account `user:${USER_EMAIL}` to IAP policy `roles/iap.httpsResourceAccessor`.

---

# Execution Order
Write all the requested files completely into the filesystem. Ensure code files contain valid syntax, complete imports, and clean formatting.
