FROM python:3.12-slim

# Install Node.js and npm for MCP tools (like reddit-mcp)
RUN apt-get update && apt-get install -y \
    curl \
    && curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
    && apt-get install -y nodejs \
    && npm install -g reddit-mcp \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir uv==0.8.13

WORKDIR /code

COPY ./pyproject.toml ./README.md ./uv.lock* ./
COPY ./dev_signal_agent ./dev_signal_agent

RUN uv sync --frozen

EXPOSE 8080

CMD ["uv", "run", "uvicorn", "dev_signal_agent.fast_api_app:app", "--host", "0.0.0.0", "--port", "8080"]

