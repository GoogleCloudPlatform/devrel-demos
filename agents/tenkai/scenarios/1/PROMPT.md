Your task is to create a Model Context Protocol (MCP) server to expose a “hello_world” tool. For the MCP implementation, you should use the official Go SDK for MCP and use the stdio transport. When called, this tool should return the string "Hello from Tenkai!"

Read these references to understand the protocol and the desired module layout:
- https://modelcontexprotocol.io
- https://go.dev/doc/modules/layout

TODO:
- Get package github.com/modelcontextprotocol/go-sdk/mcp to create the mcp server (official SDK)
- Read the package documentation to discover the API (it is not trivial)
- Create the server with stdio transport
- Create one tool "hello_world" that returns the message "Hello from Tenkai!"
- Compile the binary as "./hello"

## Acceptance Criteria
- Linter `./...` must pass with max 5 issues.
- Global unit test coverage across all packages in the project (`./...`) must be at least 50%.
- Command `./hello` with stdin `{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2025-06-18"}}
{"jsonrpc":"2.0","method":"notifications/initialized","params":{}}
{"jsonrpc":"2.0","id":2,"method":"tools/list","params":{}}` must succeed (must have: stdout containing `hello_world`).
- Command `./hello` with stdin `{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2025-06-18"}}
{"jsonrpc":"2.0","method":"notifications/initialized","params":{}}
{"jsonrpc":"2.0","id":3,"method":"tools/call","params":{"name":"hello_world","arguments":{}}}` must succeed (must have: stdout containing `Hello from Tenkai!`).
