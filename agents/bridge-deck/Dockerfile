FROM python:3.11-slim

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application source code (exclusions defined in .dockerignore)
COPY . .

# Provision container root /workspaces directory for autonomous agent project sandboxes
RUN mkdir -p /workspaces && if [ -d "/app/workspaces" ]; then cp -r /app/workspaces/* /workspaces/ 2>/dev/null || true; fi

# Cloud Run defaults
ENV PYTHONUNBUFFERED=1
ENV PORT=8080
ENV HOST=0.0.0.0

EXPOSE 8080

ENTRYPOINT ["python", "bridge_runner.py"]
CMD []
