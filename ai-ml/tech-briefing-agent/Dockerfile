FROM python:3.11-slim

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    DATA_DIR=/data \
    PORT=8080

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user and directories
RUN useradd -u 1000 -m appuser && \
    mkdir -p /data/state /data/digests /app && \
    chown -R appuser:appuser /data /app

# Copy project definition and source code
COPY pyproject.toml README.md ./
COPY digest_agent/ ./digest_agent/

# Install dependencies
RUN pip install --no-cache-dir .

# Switch to non-root user
USER appuser

# Expose HTTP port
EXPOSE 8080

# Run FastAPI server via uvicorn
ENTRYPOINT ["uvicorn", "digest_agent.server:app", "--host", "0.0.0.0", "--port", "8080"]
