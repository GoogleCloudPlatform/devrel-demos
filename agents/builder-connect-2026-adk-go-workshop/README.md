# ADK Go workshop: Builder Connect Poland 2026

The hands-on part of the ADK + A2A workshop at Builder Connect Poland
(3 November 2026). You build an agent with the
[Agent Development Kit for Go](https://github.com/google/adk-go) in three
steps:

1. An agent: a Gemini model with an instruction, tools from two MCP servers,
   and another agent used as a tool.
2. Skills, function tools that ask for confirmation, and a graph workflow.
3. A second agent that calls the first one over A2A.

The example agent answers questions about the event's agenda.

## Get the code

```bash
npx -y giget@latest gh+git:GoogleCloudPlatform/devrel-demos/agents/builder-connect-2026-adk-go-workshop adk-go-workshop
```

Or clone the whole repository and use this folder:

```bash
git clone https://github.com/GoogleCloudPlatform/devrel-demos.git
```

Then follow [workshop/README.md](./workshop/README.md).

## What's here

| Folder | What it is |
|---|---|
| [`workshop/`](./workshop) | The workshop: a start and a final folder for each step, `p0` to `p5`. Start with its README. |
| [`agendamcp/`](./agendamcp) | MCP server for the agendas of Builder Connect and Google Cloud Summit Poland 2026. It downloads them from the event site when it starts. |
| [`techmcp/`](./techmcp) | MCP server for the technologies the talks cover: which languages have an official SDK, whether they're open source, and their GitHub releases. |

`workshop/start-servers.sh` builds and runs both servers.
