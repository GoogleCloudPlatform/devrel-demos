Your task is to create a Model Context Protocol (MCP) server using the official Go SDK (`github.com/modelcontextprotocol/go-sdk`).

**Goal**: Create an MCP server with a "hello_world" tool.

**Requirements**:
1.  Initialize a Go module `example.com/mcphello`.
2.  Use `github.com/modelcontextprotocol/go-sdk`.
3.  Implement a server using **stdio transport**.
4.  Define a tool named `hello_world` that:
    - Takes no arguments.
    - Returns the text "Hello from MCP!".
5.  Ensure the server handles the MCP lifecycle (initialize, tools/list, tools/call).

**Validation**:
We will verify that the server compiles and responds correctly to MCP JSON-RPC messages over stdin.
