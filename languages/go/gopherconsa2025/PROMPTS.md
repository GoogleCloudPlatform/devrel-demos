-- hello world --

create a hello world application in Go

-- hello world mcp server (bad) --

create a hello world MCP server in Go

-- hello world mcp server (ok) --

Create a hello world MCP server in Go. MCP stands for Model Context Protocol. You should use official Go SDK and the stdio transport.

-- hello world mcp server (better)

Create a hello world MCP server in Go. MCP stands for Model Context Protocol. You should use official Go SDK and the stdio transport.

Read these references to gather information about the technology and project structure before writing any code:
- https://github.com/modelcontextprotocol/go-sdk/blob/main/README.md
- https://modelcontextprotocol.io/specification/2025-06-18/basic/lifecycle
- https://go.dev/doc/modules/layout

-- call via shell --
now test it calling via shell tool, use the following method:
(
  echo '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2025-06-18"}}';
  echo '{"jsonrpc":"2.0","method":"notifications/initialized","params":{}}';
  echo '{"jsonrpc":"2.0","id":2,"method":"tools/list","params":{}}';
) | server-command

-- godoctor full --

Your task is to create a Model Context Protocol (MCP) server to expose the go doc command, giving LLMs the capability to query Go documentation. The tool should be named go-doc and should take two arguments: package_path (required) and symbol_name (optional). For the documentation part, use the `go doc` shell command. For the MCP implementation, you should use the official Go SDK for MCP and write a production-ready MCP server that communicates through a stdio transport. You should also create a simple CLI client to allow me to test the server.

Read these references to gather information about the technology and project structure before writing any code:
- https://github.com/modelcontextprotocol/go-sdk/blob/main/README.md
- https://modelcontextprotocol.io/specification/2025-06-18/basic/lifecycle
- https://go.dev/doc/modules/layout
