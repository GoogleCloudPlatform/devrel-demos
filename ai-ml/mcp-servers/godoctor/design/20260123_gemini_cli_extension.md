# Godoctor Gemini CLI Extension Design (Revised)

**Date:** 2026-01-23
**Status:** Draft v2

## 1. Objective

Create a production-ready Gemini CLI extension for `godoctor`. The extension will enable Gemini to utilize `godoctor`'s MCP capabilities (code navigation, editing, analysis) directly.

## 2. Distribution & Installation Strategy

### Philosophy
- **Target Audience:** Go developers.
- **Assumption:** Go is installed and configured on the user's machine.
- **Mechanism:**
    - The `godoctor` binary will be installed via the standard Go toolchain: `go install github.com/danicat/godoctor@latest`.
    - This places the binary in `$GOPATH/bin` (or `$HOME/go/bin`), which is expected to be in the user's system `PATH`.
    - The extension itself (manifest + context) will be lightweight and assume the binary is available in the `PATH`.

### Architecture
`Gemini CLI` -> `extension.json` -> `godoctor` (resolved from PATH)

## 3. Extension Configuration (`gemini-extension.json`)

The configuration will be simplified to rely on the system PATH, removing local path assumptions and unnecessary environment variables.

```json
{
  "name": "godoctor",
  "version": "0.9.0", 
  "description": "AI-powered Go development assistant. Requires 'godoctor' to be installed via 'go install github.com/danicat/godoctor@latest'.",
  "contextFileName": "GEMINI.md",
  "mcpServers": {
    "godoctor": {
      "command": "godoctor",
      "args": [],
      "env": {} 
    }
  }
}
```

*Note: Version matches the current `Makefile` version.*

## 4. Documentation Updates

Since the extension relies on an external binary, the `README.md` (and `GEMINI.md` if visible to the user during setup) must clearly state the installation requirement.

**Installation Instructions to be added:**
1.  Install the binary: `go install github.com/danicat/godoctor@latest`
2.  Install/Link the extension: `gemini extensions install .` (or link for dev).

## 5. Development vs. Production

- **Local Development:** Developers working *on* godoctor can simply run `go install` in the repo to update their global binary, or use `gemini extensions link` to point to their local repo which uses the global binary.
- **Production:** Users will consume the extension manifest which points to their global install.

## 6. Implementation Plan

1.  **Create `gemini-extension.json`**:
    - Set `command` to `"godoctor"`.
    - Ensure `version` is synced with `Makefile`.
    - Remove `env` variables.
2.  **Verify `GEMINI.md`**: Ensure it is suitable for providing context to the model about *using* the tools.
3.  **Validation**:
    - Verify `godoctor` is reachable in the current environment (via `which godoctor` or `go install`).
    - Link the extension and verify the CLI can verify the server.