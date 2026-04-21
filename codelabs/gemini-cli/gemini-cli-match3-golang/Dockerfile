# Build stage 1: Compile the Go server and WASM
FROM golang:1.26.2-alpine AS builder

WORKDIR /app

# Install dependencies
COPY go.mod go.sum ./
RUN go mod download

# Copy source
COPY . .

# Build WASM
RUN GOOS=js GOARCH=wasm go build -o public/cloud-crush.wasm .
# Move web assets to public
RUN mkdir -p public/assets && cp index.html public/ && cp wasm_exec.js public/ && cp -r assets/* public/assets/

# Build Server
RUN go build -o server-bin server/main.go

# Build stage 2: Final minimal image
FROM alpine:latest

WORKDIR /root/

# Copy binaries and public assets
COPY --from=builder /app/server-bin .
COPY --from=builder /app/public ./public/

EXPOSE 8080

CMD ["./server-bin"]
