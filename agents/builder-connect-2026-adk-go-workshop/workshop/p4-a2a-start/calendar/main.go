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

// Command calendar is a second agent that manages the attendee's calendar. It
// knows nothing about the conference itself: it asks the concierge, over A2A,
// and keeps the sessions the attendee wants. The calendar itself, its tools
// and its page are in calendar.go.
//
// Section 3.2 below adds the concierge. In p4-a2a-start it is empty, for you
// to fill in, and p5-a2a-final has it filled.
//
//	go run .              # the concierge, serving A2A on :8080
//	go run ./calendar     # then open http://localhost:8001/ui/ to chat,
//	                      # and http://localhost:8002/ to see the calendar
package main

import (
	"context"
	"log"
	"os"

	"google.golang.org/genai"

	"google.golang.org/adk/v2/agent"
	"google.golang.org/adk/v2/agent/llmagent"
	"google.golang.org/adk/v2/cmd/launcher"
	"google.golang.org/adk/v2/cmd/launcher/full"
	"google.golang.org/adk/v2/model/gemini"
	// Uncomment these for 3.2.
	// "google.golang.org/adk/v2/agent/remoteagent/v2"
	// "google.golang.org/adk/v2/tool/agenttool"
)

const instruction = `You manage the attendee's calendar for Builder Connect
(3 November 2026) and Google Cloud Summit Poland 2026 (4 November 2026). Today
is 3 November.
You know nothing about the events yourself: for sessions, schedules, speakers
or technologies, ask the concierge, and never make up sessions. When the
attendee wants sessions in their calendar, ask the concierge for them, then add
each one with add_to_calendar, using the exact title, date and times the
concierge gave.
The attendee sees only your replies, not the concierge's answers. When you
answer with what the concierge told you, include the details in your reply:
each session's title and time. Otherwise keep answers short.`

func main() {
	ctx := context.Background()

	model, err := gemini.NewModel(ctx, "gemini-3.5-flash-lite", &genai.ClientConfig{
		// Retry with backoff when the model is busy (429 and 5xx responses).
		HTTPOptions: genai.HTTPOptions{RetryOptions: &genai.HTTPRetryOptions{}},
	})
	if err != nil {
		log.Fatal(err)
	}
	cfg := llmagent.Config{
		Name:        "calendar",
		Model:       model,
		Description: "Manages the attendee's conference calendar.",
		Instruction: instruction,
	}

	// ==== 3.2 Add the concierge, over A2A ================================
	// The concierge as a remote agent (remoteagent.NewA2A), from its agent card at
	// CONCIERGE_URL or http://localhost:8080, added to cfg.Tools as a tool.
	// ==== end of 3.2 =====================================================

	// The calendar, with its tools add_to_calendar and list_calendar.
	cal, calendarTools, err := newCalendar()
	if err != nil {
		log.Fatal(err)
	}
	cfg.Tools = append(cfg.Tools, calendarTools...)

	assistant, err := llmagent.New(cfg)
	if err != nil {
		log.Fatal(err)
	}

	go serveCalendar(cal) // the page on :8002

	l := full.NewLauncher()
	if err := l.Execute(ctx, &launcher.Config{AgentLoader: agent.NewSingleLoader(assistant)}, args()); err != nil {
		log.Fatalf("%v\n\n%s", err, l.CommandLineSyntax())
	}
}

// args returns the command line, or, when it is empty, the web UI and the REST
// API it calls, on port 8001.
func args() []string {
	if len(os.Args) > 1 {
		return os.Args[1:]
	}
	// Answers can take longer than the web server's 15-second default.
	web := []string{"web", "-port", "8001", "-write-timeout", "10m"}
	if host := os.Getenv("WEB_HOST"); host != "" {
		// Cloud Shell's Web Preview reaches the server under its own address.
		web = append(web, "-allow_origins", "https://8001-"+host)
	}
	return append(web,
		"api", "-path_prefix", "/", "-include_debug_api", // for the web UI's Traces panel
		"webui", "-api_server_address=", // the UI calls the API on its own origin
	)
}
