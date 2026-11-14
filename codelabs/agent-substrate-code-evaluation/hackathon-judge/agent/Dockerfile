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

FROM ghcr.io/astral-sh/uv:python3.12-alpine AS builder
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy
WORKDIR /app
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-install-project --no-dev
COPY . .
RUN uv sync --frozen --no-dev

FROM python:3.12-alpine
RUN apk add --no-cache curl ca-certificates libc6-compat gcompat && \
    curl -fsSL "https://dl.k8s.io/release/v1.32.0/bin/linux/amd64/kubectl" -o /usr/local/bin/kubectl && \
    curl -fsSL "https://github.com/agent-substrate/substrate/releases/download/v1.0.0/kubectl-ate-linux-amd64" -o /usr/local/bin/kubectl-ate && \
    chmod +x /usr/local/bin/kubectl /usr/local/bin/kubectl-ate
WORKDIR /app
ENV PATH="/app/.venv/bin:$PATH"
ENV PYTHONPATH="/app"
COPY --from=builder /app /app
EXPOSE 8000
ENTRYPOINT ["python", "-m", "src.main"]
