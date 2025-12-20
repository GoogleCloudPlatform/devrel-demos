# Hello MCP World

This directory contains resources and a guide for building a simple Model Context Protocol (MCP) server in Go.

**Slides:** [Hello, MCP World!](https://speakerdeck.com/danicat/hello-mcp-world-a490bdb2-daf6-4758-a7a9-3e8c829ad195)

## Contents

- **[PROMPTS.md](PROMPTS.md)**: A step-by-step script/guide for the demo. It covers:
    - Project setup.
    - Demonstrating MCP tools using the `godoctor` server.
    - Demonstrating MCP prompts using the `speedgrapher` server (utilizing `DRAFT.md`).
    - Building a "Hello World" MCP server from scratch using the Go SDK.
- **[DRAFT.md](DRAFT.md)**: A draft article titled "How to Build an Offline Agent with ADK, Ollama and SQLite". This file is used as input for the prompts demonstration.
- **.gemini/**: Configuration directory for the Gemini CLI, including `settings.json` for defining the [`godoctor`](https://github.com/danicat/godoctor) and [`speedgrapher`](https://github.com/danicat/speedgrapher) MCP servers.

## Getting Started

Follow the instructions in `PROMPTS.md` to initialize the project and build the MCP server. The guide assumes you are using the Gemini CLI and have Go installed.