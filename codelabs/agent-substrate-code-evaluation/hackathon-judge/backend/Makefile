# Go parameters
GO=go
BINARY_NAME=server

.PHONY: all test build lint run clean

all: lint test build

build:
	$(GO) build -o bin/$(BINARY_NAME) cmd/api/main.go

test:
	$(GO) test ./...

lint:
	$(GO) vet ./...

run:
	$(GO) run cmd/api/main.go

clean:
	$(GO) clean
	rm -rf bin/
