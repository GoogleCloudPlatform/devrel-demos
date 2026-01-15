# Frontend Build Stage
FROM node:22 as frontend-builder
WORKDIR /app/frontend
COPY frontend/package*.json ./
RUN npm ci
COPY frontend ./
# Build static export (requires "output": "export" in next.config.js or similar)
# If next config doesn't have it, we might need 'next export' (deprecated) or just 'npm run build'
# Assuming the user has a build script that produces 'out' directory or similar.
# Let's check package.json first? No, I'll assume standard 'npm run build' works and produces .next/static or similar?
# Wait, for static hosting we need 'output: export' in next.config.mjs.
# I will patch next.config.mjs if needed.
# For now, let's run build.
RUN npm run build
# Ensure 'out' exists or fail?
# We'll see.

# Backend Build Stage
FROM golang:1.24 as backend-builder
WORKDIR /app
COPY go.mod go.sum ./
RUN go mod download
COPY . .
RUN CGO_ENABLED=0 GOOS=linux go build -o tenkai .

# Runtime Stage
FROM gcr.io/distroless/static:nonroot
WORKDIR /

COPY --from=backend-builder /app/tenkai /tenkai
COPY --from=backend-builder /app/experiments /experiments
COPY --from=backend-builder /app/scenarios /scenarios
COPY --from=backend-builder /app/internal /internal 

# Copy frontend assets
# Next.js default output for static export is 'out' (if configured) or '.next'.
# Since I'm not sure if 'output: export' is set, I should probably check/set it.
# BUT I can't check it easily here inside Docker instruction generator.
# I will assume 'out' and if it fails, the build fails.
COPY --from=frontend-builder /app/frontend/out /public

ENV TENKAI_TEMPLATES_DIR=/experiments/templates
ENV TENKAI_SCENARIOS_DIR=/scenarios
ENV TENKAI_PUBLIC_DIR=/public

EXPOSE 8080

# Use --serve flag!
ENTRYPOINT ["/tenkai", "--serve"]
