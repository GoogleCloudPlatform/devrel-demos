# GopherCon UK 2025: MCP Demo

This repository contains the demo code and prompts for the "Building MCP Servers in Go" presentation at GopherCon UK 2025.

## Overview

The demo demonstrates how to create a Model Context Protocol (MCP) server from scratch using the official Go SDK.

## Contents

- **`cmd/`**: Directory containing the server code.
- **`PROMPTS.md`**: The sequence of prompts used during the live coding session.

## Tools Implemented

- **`hello`**: A basic "Hello World" tool.

## Running the Demo

1.  Initialize the module:
    ```bash
    go mod init gcuk25
    go get github.com/modelcontextprotocol/go-sdk@latest
    ```
2.  Run the server (adjust path to main.go as needed):
    ```bash
    go run cmd/server/main.go 
    ```
