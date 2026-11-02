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

	"google.golang.org/adk/v2/agent"
	"google.golang.org/adk/v2/agent/llmagent"
	"google.golang.org/adk/v2/cmd/launcher"
	"google.golang.org/adk/v2/cmd/launcher/full"
	// Uncomment each import when a sub-step uses it.
	// "google.golang.org/genai"                  // 1.1
	// "google.golang.org/adk/v2/model/gemini"    // 1.1
	// "google.golang.org/adk/v2/tool/mcptoolset" // 1.2
	// "google.golang.org/adk/v2/tool"            // 1.3
	// "google.golang.org/adk/v2/tool/agenttool"  // 1.3
	// "google.golang.org/adk/v2/tool/geminitool" // 1.3
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
	// The model, and cfg: the concierge's llmagent.Config, with its name, model,
	// description and instruction.
	// ==== end of 1.1 =====================================================

	// ==== 1.2 Add the MCP servers ========================================
	// The agenda and technologies MCP servers, as toolsets in cfg.Toolsets.
	// serverURL, below, gives their endpoints.
	// ==== end of 1.2 =====================================================

	// ==== 1.3 Add web search =============================================
	// web_search, a small agent with Google Search, added to cfg.Tools as a
	// tool.
	// ==== end of 1.3 =====================================================

	// cfg comes from 1.1, with everything the sections above added to it.
	concierge, err := llmagent.New(cfg)
	if err != nil {
		log.Fatal(err)
	}
	loader := agent.NewSingleLoader(concierge)

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
		"webui", "-api_server_address=", // the UI calls the API on its own origin
	)
}
