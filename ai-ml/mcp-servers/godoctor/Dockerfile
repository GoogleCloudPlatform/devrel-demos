FROM golang:1.24-alpine as builder
WORKDIR /app
COPY go.mod go.sum ./
RUN go mod download
COPY . .
RUN CGO_ENABLED=0 GOOS=linux go build -o /godoctor ./cmd/godoctor

FROM golang:1.24-alpine
RUN apk add --no-cache git
WORKDIR /app
COPY --from=builder /godoctor /usr/local/bin/godoctor
ENV PORT=8080
CMD ["sh", "-c", "godoctor -listen :$PORT"]
