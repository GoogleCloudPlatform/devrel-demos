-- setup --
- go mod init hello
- go get github.com/modelcontextprotocol/go-sdk@latest
-- setup --

-- tools demo --
show me the documentation for net/http
--
summarise the documentation for github.com/modelcontextprotocol/go-sdk/mcp
-- tools demo --

-- prompts demo --
/haiku --theme="bletchley park"
Or
/interview
/outline
/readability
-- prompts demo

-- mcp sdk demo  --
Your task is to create a Model Context Protocol (MCP) server to expose a “hello world” tool. For the MCP implementation, you should use the official Go SDK for MCP and use the stdio transport.

Initialise the project by running:
- go mod init hello
- go get github.com/modelcontextprotocol/go-sdk@latest

Read these references before writing any code:
- https://raw.githubusercontent.com/modelcontextprotocol/go-sdk/refs/heads/main/README.md
- https://go.dev/doc/modules/layout

To test the server, use shell commands like these:
(
  echo '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2025-06-18"}}';
  echo '{"jsonrpc":"2.0","method":"notifications/initialized","params":{}}';
  echo '{"jsonrpc":"2.0","id":2,"method":"tools/list","params":{}}';
  sleep 1;
) | ./bin/hello
-- mcp sdk demo--