# 📸 AI Selfie Souvenir

An interactive web application powered by **FastAPI** and **Google Gemini AI** that transforms user selfies into personalized event souvenirs and location photos.

---

## 🚀 Features

- **AI Souvenir Generation**: Combines user selfies with target locations and themes using Google's Gemini (Nano Banana 🍌) image generation capabilities.
- **Lightweight Frontend**: Pure HTML5, CSS3, and JavaScript interface—fast, responsive, and easy to customize.
- **FastAPI Backend**: Asynchronous Python backend serving REST APIs, location lookups, rate limiting, and static files.
- **Flexible Configuration**: Driven by environment configuration files (`.env` / `config/*.env`) allowing dynamic event branding, model IDs, and UI themes.
- **Cloud Run Ready**: Automated deployment scripts (`.sh` and `.ps1`) for Google Cloud Run serverless deployment.
- **Security & Rate Limiting**: Built-in IP rate limiting and origin validation middleware to protect against misuse.

---

## 🛠️ Project Structure

```text
ai-selfie-souvenir/
├── config/                  # Event-specific environment configuration files
│   └── europython2026.env
├── deploy/                  # Cloud Run deployment scripts
│   ├── europython2026.sh    # Bash deployment script
│   └── europython2026.ps1   # PowerShell deployment script
├── src/
│   ├── backend/             # FastAPI application
│   │   ├── main.py          # API endpoints & middleware
│   │   ├── config.py        # Configuration manager
│   │   └── locations.py     # Location details & presets
│   ├── frontend/            # Web interface assets (HTML, CSS, JS)
│   ├── .env.local           # Local configuration override
│   ├── .gcloudignore        # Cloud Run deployment exclusions
│   ├── Procfile             # Production entry point (Uvicorn)
│   └── requirements.txt     # Python dependencies
├── tests/                   # Pytest suite
│   └── test_backend.py
├── .gitignore
└── README.md
```

---

## 📋 Prerequisites

- **Python 3.12+**
- **Google Cloud Account** with Agent Platform API access (GCP credentials configured).

---

## ⚙️ Local Development Setup

### 1. Create and activate a Virtual Environment

**Linux / macOS:**

```bash
python -m venv venv
source venv/bin/activate
```

**Windows:**

```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
```

### 2. Install Dependencies

```bash
pip install -r src/requirements.txt
```

### 3. Authenticate with Google Cloud

Configure Application Default Credentials (ADC) for local Gemini API access:

```bash
gcloud auth application-default login
gcloud auth application-default set-quota-project YOUR_PROJECT_ID
```

### 4. Configure Environment Variables

Edit the `src/.env.local` file to point to your desired configuration:

```ini
CONFIG_FILE=../config/europython2026.env
```

### 5. Run the Server

Start the development server using Uvicorn:

```bash
uvicorn src.backend.main:app --reload --port 8080
```

Open your browser and navigate to `http://localhost:8080` to access the application.

---

## 🧪 Running Tests

Ensure your virtual environment is activated, then run the test suite using `pytest`:

```bash
python -m pytest tests/
```

---

## ☁️ Deployment

Deploy to **Google Cloud Run** using the provided deployment scripts:

### Linux / macOS:

```bash
chmod +x deploy/europython2026.sh
./deploy/europython2026.sh
```

### Windows (PowerShell):

```powershell
.\deploy\europython2026.ps1
```
