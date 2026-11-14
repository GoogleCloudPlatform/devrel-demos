# Root Makefile for Hackathon Judge

.PHONY: all test build lint setup clean \
	test-backend test-frontend test-agent test-sandbox \
	build-backend build-frontend \
	lint-backend lint-frontend lint-agent lint-sandbox \
	setup-agent setup-sandbox

all: build-all test-all

# Orchestration
test-all: test-backend test-frontend test-agent test-sandbox
build-all: build-backend build-frontend
lint-all: lint-backend lint-frontend lint-agent lint-sandbox
setup-all: setup-agent setup-sandbox
clean-all:
	$(MAKE) -C backend clean
	$(MAKE) -C frontend clean
	$(MAKE) -C agent clean
	$(MAKE) -C agent-sandbox clean

# Backend
test-backend:
	$(MAKE) -C backend test

build-backend:
	$(MAKE) -C backend build

lint-backend:
	$(MAKE) -C backend lint

# Frontend
test-frontend:
	$(MAKE) -C frontend test

build-frontend:
	$(MAKE) -C frontend build

lint-frontend:
	$(MAKE) -C frontend lint

# Agent
test-agent:
	$(MAKE) -C agent test

setup-agent:
	$(MAKE) -C agent setup

lint-agent:
	$(MAKE) -C agent lint

# Agent Sandbox
test-sandbox:
	$(MAKE) -C agent-sandbox test

setup-sandbox:
	$(MAKE) -C agent-sandbox setup

lint-sandbox:
	$(MAKE) -C agent-sandbox lint
