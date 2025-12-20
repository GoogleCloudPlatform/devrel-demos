-- setup --
go mod init golab2025
go get github.com/modelcontextprotocol/go-sdk@latest

-- mcp demo --
show me the documentation for net/http
--
show me the documentation for github.com/modelcontextprotocol/go-sdk/mcp
-- end mcp demo --

-- mcp from scratch (step 1) --
Your task is to create a Model Context Protocol (MCP) server to expose a “hello world” tool. For the MCP implementation, you should use the official Go SDK for MCP v1.0.0 and use the stdio transport.

Read these references to gather information about the technology and project structure before writing any code:
- https://raw.githubusercontent.com/modelcontextprotocol/go-sdk/refs/heads/main/README.md
- https://go.dev/doc/modules/layout

To test the server, use shell commands like these:
(
  echo '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2025-06-18"}}';
  echo '{"jsonrpc":"2.0","method":"notifications/initialized","params":{}}';
  echo '{"jsonrpc":"2.0","id":2,"method":"tools/list","params":{}}';
  sleep 1;
) | ./bin/godoctor
-- end mcp from scratch

-- mcp from scratch (step 2) --
Add a new tool to our MCP server called "godoc" that invokes the "go doc" shell command. The tool will take a mandatory "package" argument and an optional "symbol" argument.

Read the reference for the go doc command to understand its API: https://pkg.go.dev/golang.org/x/tools/cmd/godoc

Test it by executing the call with:
  echo '{"jsonrpc":"2.0","id":2,"method":"tools/call","params":{"name": "godoc", "arguments": {"package": "fmt"} } }'
 | ./bin/godoctor

Test it using both a standard library package and an external package like "github.com/modelcontextprotocol/go-sdk/mcp", both with and without symbols.
-- end mcp from scratch
