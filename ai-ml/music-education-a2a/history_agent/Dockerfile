FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim

WORKDIR /app

# Copy the root pyproject.toml
COPY pyproject.toml .
COPY uv.lock .

# Copy the history_agent specific files
COPY history_agent/ ./history_agent/

ENV UV_LINK_MODE=copy
ENV PYTHONUNBUFFERED=1

# Install dependencies
RUN uv sync --locked --no-install-project --no-dev

# Set the working directory to the agent subdirectory
WORKDIR /app/history_agent

ENV PATH="/app/.venv/bin:$PATH"

EXPOSE 8080

ENTRYPOINT ["uvicorn", "agent:a2a_app", "--host", "0.0.0.0", "--port", "8080"]
