FROM python:3.12-slim
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

RUN apt-get update && \
    apt-get install -y --no-install-recommends git && \
    apt-get purge -y --auto-remove && \
    rm -rf /var/lib/apt/lists/*

EXPOSE 8080
WORKDIR /app/music_ed_agent
COPY . ./

RUN uv sync

ENTRYPOINT ["uv", "run", "adk", "web", "--host", "0.0.0.0", "--port", "8080", "/app"]
