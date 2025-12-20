# EngCon 2025: The Engineer's Craft in The Age of AI

This repository contains the demo code and prompts for the "The Engineer's Craft in The Age of AI" talk at EngCon 2025.

## Overview

The demo shows how to build a Model Context Protocol (MCP) server from scratch using the official Go SDK.

## Contents

- **`main.go`**: The source code for the MCP server.
- **`PROMPTS.md`**: The sequence of prompts used during the live coding session to generate the server and its tools.

## Tools Implemented

- **`godoctor`**: A basic tool skeleton.
- **`godoc`**: A tool that wraps the `go doc` command to retrieve documentation.

## Running the Demo

1.  Initialize the module:
    ```bash
    go mod init engcon
    go get github.com/modelcontextprotocol/go-sdk@latest
    ```
2.  Run the server:
    ```bash
    go run main.go
    ```
