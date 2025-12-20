# GoLab 2025: MCP Demo

This repository contains the demo code and prompts for the "Building MCP Servers in Go" presentation at GoLab 2025.

## Overview

The demo demonstrates how to create a Model Context Protocol (MCP) server from scratch using the official Go SDK.

## Contents

- **`main.go`**: The source code for the MCP server.
- **`PROMPTS.md`**: The sequence of prompts used during the live coding session.

## Tools Implemented

- **`godoctor`**: A basic tool skeleton.
- **`godoc`**: A tool that wraps the `go doc` command to retrieve documentation.

## Running the Demo

1.  Initialize the module:
    ```bash
    go mod init golab2025
    go get github.com/modelcontextprotocol/go-sdk@latest
    ```
2.  Run the server:
    ```bash
    go run main.go
    ```
