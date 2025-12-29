FROM python:3.12-slim
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

RUN apt-get update && \
    apt-get install -y --no-install-recommends git && \
    apt-get purge -y --auto-remove && \
    rm -rf /var/lib/apt/lists/*

EXPOSE 8080
WORKDIR /app
COPY . ./

RUN uv sync

ENTRYPOINT ["uv", "run", "uvicorn", "agent:a2a_app", "--host", "0.0.0.0", "--port", "8080"]
