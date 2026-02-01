# Makefile for Tenkai

# Go parameters
GOCMD=go
GOBUILD=$(GOCMD) build
GOCLEAN=$(GOCMD) clean
GOTEST=$(GOCMD) test
GOINSTALL=$(GOCMD) install
BINARY_SERVER=bin/server
BINARY_RUNNER=bin/runner

# Version
VERSION := 0.2.0
LDFLAGS=-ldflags "-X main.version=$(VERSION)"

all: build

build: server runner

server:
	$(GOBUILD) $(LDFLAGS) -o $(BINARY_SERVER) ./cmd/server

runner:
	$(GOBUILD) $(LDFLAGS) -o $(BINARY_RUNNER) ./cmd/runner

install:
	$(GOINSTALL) $(LDFLAGS) ./cmd/server
	$(GOINSTALL) $(LDFLAGS) ./cmd/runner

clean:
	@rm -rf bin/

test:
	$(GOTEST) -v ./...

.PHONY: all build server runner install clean test