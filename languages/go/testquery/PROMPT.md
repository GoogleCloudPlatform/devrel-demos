Your task is to create a Model Context Protocol (MCP) server to expose the testquery tool. To launch testquery in mcp mode, a new command should be implemented called mcp. For the MCP implementation, you should use the official Go SDK for MCP and write a server that communicates through a stdio transport.

For now, only implement the query command as a tool using an in-memory database.

Read these references to gather information about the technology and project structure before writing any code:

https://github.com/modelcontextprotocol/go-sdk/blob/main/README.md
https://modelcontextprotocol.io/specification/2025-06-18/basic/lifecycle
https://go.dev/doc/modules/layout

To test the implementation, you can send raw jsonrpc messages like this:
(
  echo '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2025-06-18"}}';
  echo '{"jsonrpc":"2.0","method":"notifications/initialized","params":{}}';
  echo '{"jsonrpc":"2.0","id":2,"method":"tools/list","params":{}}';
) | ./bin/tq mcp