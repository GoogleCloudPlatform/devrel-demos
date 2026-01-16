Your task is to create a Model Context Protocol (MCP) server to expose a “hello_world” tool. For the MCP implementation, you should use the official Go SDK for MCP and use the stdio transport. When called, this tool should return the string "Hello from Tenkai!"

Read these references to understand the protocol and the desired module layout:
- https://modelcontexprotocol.io
- https://go.dev/doc/modules/layout

To test the server, you can use shell commands like these:
```sh
(
  echo '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2025-06-18"}}';
  echo '{"jsonrpc":"2.0","method":"notifications/initialized","params":{}}';
  echo '{"jsonrpc":"2.0","id":2,"method":"tools/list","params":{}}';
  sleep 1;
) | ./hello
```
TODO:
- Get package github.com/modelcontextprotocol/go-sdk/mcp to create the mcp server (official SDK)
- Read the package documentation to discover the API (it is not trivial)
- Create the server with stdio transport
- Create one tool "hello_world" that returns the message "Hello from Tenkai!"

## Acceptance Criteria
- Command `go build -o hello .` must succeed (exit code 0).
- Linter `./...` must pass with max 5 issues.
- Command `(   echo '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2025-06-18"}}';   echo '{"jsonrpc":"2.0","method":"notifications/initialized","params":{}}';   echo '{"jsonrpc":"2.0","id":2,"method":"tools/list","params":{}}';   sleep 1; ) | ./hello` must succeed (exit code 0).
- Unit tests for `./...` must pass with min 50% coverage.
