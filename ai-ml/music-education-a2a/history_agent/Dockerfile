FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim

WORKDIR /app

# Copy the root pyproject.toml
COPY pyproject.toml .
COPY uv.lock .

COPY history_agent/ history_agent/

ENV UV_LINK_MODE=copy
ENV PYTHONUNBUFFERED=1

# Install dependencies AND install the current directory as a package
RUN uv sync --locked --no-dev && \
    uv pip install -e .

ENV PATH="/app/.venv/bin:$PATH"

EXPOSE 8080
ENV PYTHONPATH=/app:$PYTHONPATH

ENTRYPOINT ["uvicorn", "history_agent.agent:a2a_app", "--host", "0.0.0.0", "--port", "8080"]
