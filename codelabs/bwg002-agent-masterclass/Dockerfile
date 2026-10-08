# /**
#  * @file Dockerfile
#  * @description Container image definition for the Agentic Pitch Generator on Cloud Run.
#  *
#  * Why:
#  * 1. python:3.11-slim minimizes image surface area and cold-start latency on Cloud Run.
#  * 2. Running as a dedicated non-root user (appuser) enforces the Principle of Least Privilege.
#  * 3. Bundling both pitch_generator/ and frontend/ allows a single Cloud Run service to
#  *    serve the plain HTML/CSS/JS UI, REST API, and A2A protocol endpoints on PORT 8080.
#  */
FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=8080 \
    GOOGLE_GENAI_USE_ENTERPRISE=TRUE

WORKDIR /app

# /**
#  * Why: Creating a non-root system user before copying application assets prevents
#  * container processes from executing with root privileges in production.
#  */
RUN groupadd --system appgroup && useradd --system --gid appgroup --create-home appuser

COPY pyproject.toml README.md call_agent.py ./
COPY pitch_generator ./pitch_generator
COPY frontend ./frontend
COPY scripts ./scripts

RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -e . && \
    chown -R appuser:appgroup /app

USER appuser

EXPOSE 8080

CMD ["sh", "-c", "uvicorn pitch_generator.fast_api_app:app --host 0.0.0.0 --port ${PORT:-8080}"]
