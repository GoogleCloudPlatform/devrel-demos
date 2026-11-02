// Copyright 2026 Google LLC
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//     https://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.

// Command concierge is the conference concierge from the ADK + A2A workshop.
// Each sub-step's code has its own section below, marked "==== 1.2 ... ====".
// A start folder has the step's sections empty, for you to fill in, and the
// matching final folder has the same sections filled.
//
//	../start-servers.sh   # the MCP servers, in another terminal
//	go run .              # then open http://localhost:8080/ui/
//	go run . console      # or chat in the terminal
package main

import (
	"context"
	"fmt"
	"log"
	"os"

	"google.golang.org/genai"

	"google.golang.org/adk/v2/agent"
	"google.golang.org/adk/v2/agent/llmagent"
	"google.golang.org/adk/v2/cmd/launcher"
	"google.golang.org/adk/v2/cmd/launcher/full"
	"google.golang.org/adk/v2/model/gemini"
	"google.golang.org/adk/v2/tool"
	"google.golang.org/adk/v2/tool/agenttool"
	"google.golang.org/adk/v2/tool/geminitool"
	"google.golang.org/adk/v2/tool/mcptoolset"
)

// instruction tells the model who it is and how to answer.
const instruction = `You are the concierge for two Google events at PGE Narodowy,
Warsaw: Builder Connect on 3 November 2026 and Google Cloud Summit Poland 2026
on 4 November 2026. Today is 3 November, the Builder Connect day, unless the
attendee says otherwise. Help attendees find sessions and plan their days.
All times are Warsaw time. Keep answers short, and if you don't have the
information, say so instead of guessing.
Use the agenda tools to find sessions. Only mention sessions the tools
returned and copy their times exactly. Before presenting a schedule, run
check_plan on it and fix any overlaps.
For questions about the technologies themselves, such as programming
languages, open source or release dates, use find_technologies and
get_technologies. When a question combines both, for example talks about
projects with Java support, find the technologies first, then search the
agenda once with all their names and aliases as terms.
Use web_search only when asked about something outside the agenda and the
technologies, such as a speaker's or company's background.`

func main() {
	ctx := context.Background()

	// ==== 1.1 Create the agent ===========================================
	// No backend is set, so the environment picks it: Vertex AI when
	// GOOGLE_GENAI_USE_VERTEXAI=true, otherwise the Gemini API with
	// GOOGLE_API_KEY. Flash-Lite answers each step in about a second, which
	// keeps multi-step answers interactive.
	model, err := gemini.NewModel(ctx, "gemini-3.5-flash-lite", &genai.ClientConfig{
		// Retry with backoff when the model is busy (429 and 5xx responses).
		HTTPOptions: genai.HTTPOptions{RetryOptions: &genai.HTTPRetryOptions{}},
	})
	if err != nil {
		log.Fatal(err)
	}
	// The concierge's configuration. The next sections add its tools, and
	// llmagent.New, after them, creates the agent.
	cfg := llmagent.Config{
		Name:        "concierge",
		Model:       model,
		Description: "Concierge for Builder Connect and Google Cloud Summit Poland 2026.",
		Instruction: instruction,
		GenerateContentConfig: &genai.GenerateContentConfig{
			ThinkingConfig: &genai.ThinkingConfig{ThinkingLevel: genai.ThinkingLevelLow},
		},
	}
	// ==== end of 1.1 =====================================================

	// ==== 1.2 Add the MCP servers ========================================
	// Every tool an MCP server offers becomes a tool of this agent.
	agenda, err := mcptoolset.New(mcptoolset.Config{Endpoint: serverURL("AGENDA_MCP_URL", 8090)})
	if err != nil {
		log.Fatal(err)
	}
	technologies, err := mcptoolset.New(mcptoolset.Config{Endpoint: serverURL("TECH_MCP_URL", 8092)})
	if err != nil {
		log.Fatal(err)
	}
	cfg.Toolsets = append(cfg.Toolsets, agenda, technologies)
	// ==== end of 1.2 =====================================================

	// ==== 1.3 Add web search =============================================
	// Gemini's built-in Google Search can't share a request with other tools,
	// so it gets its own small agent, which the concierge uses as a tool.
	webSearch, err := llmagent.New(llmagent.Config{
		Name:        "web_search",
		Model:       model,
		Description: "Searches the web with Google Search, e.g. for speakers, companies or products.",
		Instruction: "Answer the request with Google Search. Be brief and factual.",
		Tools:       []tool.Tool{geminitool.GoogleSearch{}},
	})
	if err != nil {
		log.Fatal(err)
	}
	cfg.Tools = append(cfg.Tools, agenttool.New(webSearch, nil))
	// ==== end of 1.3 =====================================================

	// ==== 2.1 Skills =====================================================
	// The skills in skills/, from functions.go.
	skills, err := newSkills(ctx)
	if err != nil {
		log.Fatal(err)
	}
	cfg.Toolsets = append(cfg.Toolsets, skills)
	// ==== end of 2.1 =====================================================

	// ==== 2.2 A workspace, with bash you approve =========================
	// read_file, write_file and bash, from functions.go, in the folder you run
	// the agent from.
	ws, workspaceTools, err := newWorkspace(".")
	if err != nil {
		log.Fatal(err)
	}
	cfg.Tools = append(cfg.Tools, workspaceTools...)
	cfg.Instruction += "\nThe attendee has a workspace folder for their files: read_file and write_file" +
		"\nwork there, and bash runs commands there once the attendee approves them."
	// ==== end of 2.2 =====================================================

	// cfg comes from 1.1, with everything the sections above added to it.
	concierge, err := llmagent.New(cfg)
	if err != nil {
		log.Fatal(err)
	}
	loader := agent.NewSingleLoader(concierge)

	// ==== 2.3 A workflow: the day planner ================================
	// day_planner, from functions.go, served next to the concierge: the web UI
	// lists them as two apps.
	planner, err := newDayPlanner(model, agenda, technologies, ws)
	if err != nil {
		log.Fatal(err)
	}
	loader, err = agent.NewMultiLoader(concierge, planner)
	if err != nil {
		log.Fatal(err)
	}
	// ==== end of 2.3 =====================================================

	l := full.NewLauncher()
	if err := l.Execute(ctx, &launcher.Config{AgentLoader: loader}, args()); err != nil {
		log.Fatalf("%v\n\n%s", err, l.CommandLineSyntax())
	}
}

// serverURL is an MCP server's endpoint: the environment variable env if set,
// otherwise a server running locally on port (see ../start-servers.sh).
func serverURL(env string, port int) string {
	if u := os.Getenv(env); u != "" {
		return u
	}
	return fmt.Sprintf("http://localhost:%d/mcp", port)
}

// args returns the command line or, when it is empty, the default: the web UI
// and the REST API it calls on port 8080, plus A2A from 3.1 on.
func args() []string {
	if len(os.Args) > 1 {
		return os.Args[1:]
	}
	// Answers can take longer than the web server's 15-second default.
	web := []string{"web", "-port", "8080", "-write-timeout", "10m"}
	if host := os.Getenv("WEB_HOST"); host != "" {
		// Cloud Shell's Web Preview reaches the server under its own address.
		web = append(web, "-allow_origins", "https://8080-"+host)
	}
	return append(web,
		"api", "-path_prefix", "/", "-include_debug_api", // for the web UI's Traces panel
		// ==== 3.1 Serve the concierge over A2A ===============================
		// The a2a launcher, and the URL its agent card gives other agents:
		// http://localhost:8080.
		// ==== end of 3.1 =====================================================
		"webui", "-api_server_address=", // the UI calls the API on its own origin
	)
}
