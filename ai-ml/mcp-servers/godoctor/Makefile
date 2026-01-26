# Makefile for GoDoctor

# Go parameters
GOCMD=go
GOBUILD=$(GOCMD) build
GOCLEAN=$(GOCMD) clean
GOTEST=$(GOCMD) test
GOGET=$(GOCMD) get
BINARY_DIR=bin
SERVER_BINARY_NAME=godoctor
SERVER_BINARY=$(BINARY_DIR)/$(SERVER_BINARY_NAME)

# Version
VERSION := 0.11.0
LDFLAGS=-ldflags "-X main.version=$(VERSION)"


all: build

build:
	@mkdir -p $(BINARY_DIR)
	$(GOBUILD) $(LDFLAGS) -o $(SERVER_BINARY) ./cmd/godoctor

install:
	$(GOCMD) install $(LDFLAGS) ./...

clean:
	@rm -rf $(BINARY_DIR)

test:
	$(GOTEST) -v ./...

test-cov:
	$(GOTEST) -v -coverprofile=coverage.out ./...
	@echo "to view the coverage report, run: go tool cover -html=coverage.out"

.PHONY: all build install clean test test-cov