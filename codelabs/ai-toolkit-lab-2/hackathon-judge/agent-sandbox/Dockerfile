# Copyright 2026 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

# Stage 1: Builder for Go and binaries
FROM debian:bookworm-slim AS builder

RUN apt-get update && apt-get install -y curl tar gnupg

# Install Go 1.26.2
RUN curl -fsSL https://go.dev/dl/go1.26.2.linux-amd64.tar.gz | tar -xzC /usr/local

# Stage 2: Final Image
FROM debian:bookworm-slim

# Set environment variables for versions and paths
ENV NODE_VERSION=24.15.0
ENV PYTHON_VERSION=3.14.4
ENV GO_PATH=/usr/local/go
ENV SANDBOX_DIR=/home/sandbox/app
ENV GEMINI_CLI_TRUST_WORKSPACE=true
ENV PATH=$PATH:$GO_PATH/bin:/home/sandbox/.local/bin
ENV PLAYWRIGHT_BROWSERS_PATH=/usr/lib/playwright

# Install system dependencies and tools
RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    python3 \
    python3-pip \
    python3-venv \
    curl \
    ca-certificates \
    build-essential \
    jq \
    ripgrep \
    procps \
    zip \
    unzip \
    vim-tiny \
    tree \
    file \
    cloc \
    shellcheck \
    gnupg \
    libcap2-bin \
    # Playwright dependencies
    libgpg-error0 \
    libnss3 \
    libnspr4 \
    libatk1.0-0 \
    libatk-bridge2.0-0 \
    libcups2 \
    libdrm2 \
    libxkbcommon0 \
    libxcomposite1 \
    libxdamage1 \
    libxext6 \
    libxfixes3 \
    libxrandr2 \
    libgbm1 \
    libpango-1.0-0 \
    libcairo2 \
    libasound2 \
    && ln -s /usr/bin/rg /usr/bin/ripgrep \
    && rm -rf /var/lib/apt/lists/*

# Hardening: Remove SUID/SGID bits from all files
RUN find / -xdev -perm /6000 -type f -exec chmod a-s {} + || true

# Install GitHub CLI (gh)
RUN curl -fsSL https://cli.github.com/packages/githubcli-archive-keyring.gpg | dd of=/usr/share/keyrings/githubcli-archive-keyring.gpg \
    && chmod go+r /usr/share/keyrings/githubcli-archive-keyring.gpg \
    && echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/githubcli-archive-keyring.gpg] https://cli.github.com/packages stable main" | tee /etc/apt/sources.list.d/github-cli.list > /dev/null \
    && apt-get update \
    && apt-get install -y gh \
    && rm -rf /var/lib/apt/lists/*

# Install Node.js (LTS v24.x) and Node package managers
RUN curl -fsSL https://deb.nodesource.com/setup_24.x | bash - \
    && apt-get install -y nodejs \
    && npm install -g npm@latest yarn pnpm playwright \
    && rm -rf /var/lib/apt/lists/*

# Install Playwright Chromium
RUN npx playwright install chromium

# Copy Go from builder
COPY --from=builder /usr/local/go /usr/local/go

# Install Gemini CLI
RUN npm install -g @google/gemini-cli

# Copy uv binary from official image
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# Setup User Permissions
RUN useradd -m -u 1000 -s /bin/bash sandbox

# Create workspace and sandbox app directory
RUN mkdir -p /home/sandbox/app && \
    chown -R sandbox:sandbox /home/sandbox

# Switch to non-root user
USER sandbox
WORKDIR /home/sandbox/app

# Copy project files
COPY --chown=sandbox:sandbox pyproject.toml README.md ./
COPY --chown=sandbox:sandbox app/ ./app/

# Sync dependencies using uv (creates .venv)
RUN uv sync

# Verify installations
RUN node --version && \
    npm --version && \
    go version && \
    python3 --version && \
    gh --version && \
    tree --version && \
    uv --version && \
    npx playwright --version && \
    gemini --version

# Default command: Start the FastAPI server using uv run
CMD ["uv", "run", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8888"]
