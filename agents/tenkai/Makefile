# Makefile for Tenkai

# Go parameters
GOCMD=go
GOBUILD=$(GOCMD) build
GOCLEAN=$(GOCMD) clean
GOTEST=$(GOCMD) test
GOINSTALL=$(GOCMD) install
BINARY_NAME=tenkai

# Version
VERSION := 0.1.0
LDFLAGS=-ldflags "-X main.version=$(VERSION)"

all: build

build:
	$(GOBUILD) $(LDFLAGS) -o $(BINARY_NAME) .

install:
	$(GOINSTALL) $(LDFLAGS) .

clean:
	@rm -f $(BINARY_NAME)

test:
	$(GOTEST) -v ./...

.PHONY: all build install clean test