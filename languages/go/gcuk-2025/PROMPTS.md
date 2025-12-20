-- setup --
go mod init gcuk25
go get github.com/modelcontextprotocol/go-sdk@latest

-- tools demo --
show me the documentation for net/http
--
show me the documentation for github.com/modelcontextprotocol/go-sdk/mcp
-- end godoctor --

-- prompts demo --
/haiku --theme="gophercon"
-- 
/import_this
-- end speedgrapher --

-- mcp from scratch --
Your task is to create a Model Context Protocol (MCP) server to expose a “hello world” tool. For the MCP implementation, you should use the official Go SDK for MCP and use the stdio transport.

Read these references to gather information about the technology and project structure before writing any code:
- https://raw.githubusercontent.com/modelcontextprotocol/go-sdk/refs/heads/main/README.md
- https://go.dev/doc/modules/layout

To test the server, use shell commands like these:
(
  echo '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2025-06-18"}}';
  echo '{"jsonrpc":"2.0","method":"notifications/initialized","params":{}}';
  echo '{"jsonrpc":"2.0","id":2,"method":"tools/list","params":{}}';
) | ./bin/godoctor
-- end mcp from scratch

-- mcp from scratch (complete) --
Your task is to create a Model Context Protocol (MCP) server to expose a “hello world” tool. For the MCP implementation, you should use the official Go SDK for MCP and use the stdio transport.

Read these references to gather information about the technology and project structure before writing any code:
- https://github.com/modelcontextprotocol/go-sdk/blob/main/README.md
- https://modelcontextprotocol.io/specification/2025-06-18/basic/lifecycle
- https://go.dev/doc/modules/layout

To test the server, use shell commands like these:
(
  echo '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2025-06-18"}}';
  echo '{"jsonrpc":"2.0","method":"notifications/initialized","params":{}}';
  echo '{"jsonrpc":"2.0","id":2,"method":"tools/list","params":{}}';
) | ./bin/godoctor
-- end mcp from scratch
