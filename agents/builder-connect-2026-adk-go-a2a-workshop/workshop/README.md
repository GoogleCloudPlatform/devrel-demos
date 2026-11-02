# Workshop steps

Every step has a start folder, where you work, and a final folder with the
finished step.

- In `main.go`, each sub-step's code has its own section:

  ```go
  // ==== 1.2 Add the MCP servers =========================================
  // ==== end of 1.2 ======================================================
  ```

  In a start folder, that step's sections are empty, with a hint, and you
  write the code there. Everything around them is ready: the instruction, the
  helpers, the launcher. The final folder has the same sections filled in.
- Each start folder already has the previous step finished. To carry on with
  your own code instead, paste your sections into it.
- Stuck, or want to check your work? Compare the section with the same number
  in the final folder. Outside the sections, start and final are identical:

```bash
diff -ru p2-advance-start p3-advance-final
```

In `p0-concierge-agent-start`, uncomment each import when a sub-step uses it.
It compiles once 1.1 is done.

| Folder | What it is | Focus |
|---|---|---|
| `p0-concierge-agent-start` | Where step 1 starts: the instruction, the helpers and the launcher, with empty sections 1.1 to 1.3. | ADK basics |
| `p1-concierge-agent-final` | Step 1, finished. The concierge: a Gemini model with an instruction, the tools of two MCP servers (the agenda, and the technologies the talks cover), and a web search agent it uses as a tool. | ADK basics |
| `p2-advance-start` | Where step 2 starts: step 1 finished, plus `functions.go` and `skills/`, with empty sections 2.1 to 2.3. | Advanced ADK |
| `p3-advance-final` | Step 2, finished. `functions.go`, wired into `main.go` in a few lines: skills (`skills/`), a workspace the agent reads and writes, a bash tool that runs only what you approve, and `day_planner`, a graph workflow that researches in parallel, plans, checks the plan in code, and asks before saving. | Advanced ADK |
| `p4-a2a-start` | Where step 3 starts: step 2 finished, with an empty section 3.1, and `calendar/`, a complete second agent except section 3.2, which connects it to the concierge. | A2A |
| `p5-a2a-final` | Step 3, finished. The concierge serves A2A, and a second agent, `calendar/`, asks it for sessions and keeps your calendar, with a page that shows it. | A2A |

## New to Go?

Check whether Go is installed with `go version`. Any Go 1.21 or later works:
the first `go run` downloads the version the folders ask for, Go 1.26, which
takes a minute.

To install it:

- **Linux:** the archive from https://go.dev/dl/. Distribution packages can be
  older than Go 1.21.
- **Cloud Shell:** already installed.
- **macOS:** `brew install go`, or the installer from https://go.dev/dl/.
- **Anything else:** https://go.dev/doc/install

What you need to know for the workshop:

- `go run .` builds and runs the code in the current folder. The first run
  also downloads the modules listed in `go.mod`.
- Go refuses to compile a file with an unused import or variable. In
  `p0-concierge-agent-start`, uncomment each import only when the code you add
  uses it.
- Your editor can format the code when you save; `gofmt -w main.go` does the
  same. VS Code needs the Go extension.
- The Tour of Go, https://go.dev/tour/, covers the language basics.

## Running a step

Pick a model backend in your shell:

```bash
# Vertex AI, in your Google Cloud project (the workshop credits):
export GOOGLE_GENAI_USE_VERTEXAI=true GOOGLE_CLOUD_LOCATION=global
export GOOGLE_CLOUD_PROJECT=$(gcloud config get-value project)
# or the Gemini API, with an AI Studio key:
export GOOGLE_API_KEY=your-api-key
```

Every step needs the MCP servers. In a separate terminal:

```bash
./start-servers.sh        # agenda on :8090, technologies on :8092
```

It builds and runs the two MCP servers in `../agendamcp` and `../techmcp`, so
you need the whole folder, not only `workshop/`. The agenda server downloads
the current agenda from the event site when it starts.

Then, in the step's folder:

```bash
go run .                  # web UI at http://localhost:8080/ui/
go run . console          # or chat in the terminal
```

In Cloud Shell, open port 8080 with Web Preview and add `/ui/` to the URL.

From step 2 on, the web UI has two apps: `concierge` and `day_planner`. The
agent's files go to the step's folder, where you run it.

From step 3 on, a second agent asks the concierge over A2A. Run it in another
terminal, next to `go run .`:

```bash
go run ./calendar         # chat at http://localhost:8001/ui/
                          # calendar page at http://localhost:8002/
```

## Questions to try

| From step | App | Ask |
|---|---|---|
| 1 | concierge | `When is the ADK + A2A workshop, and who runs it?` · `I'm a Kotlin developer. Which talks should I go to today?` · `Is there a talk by someone from Carrefour today? Look up on the web what Carrefour has been doing with AI.` |
| 2 | concierge | `Start notes for the ADK + A2A workshop. I want to ask about auth between agents.` · `Put the ADK + A2A workshop and the Bielik RAG workshop into a calendar file.` (approve the command) |
| 2 | day_planner | `Plan my afternoon today. I'm a Kotlin developer and I like agents. Keep lunch free.` Then answer the approval: ask for a change, or `yes`. |
| 2 | concierge | `Turn my saved plan into a calendar file.` |
| 3 | calendar | `Add the ADK + A2A workshop and today's MCP talk to my calendar.` · `Also add tomorrow's opening keynote.` · `What's in my calendar?` |
