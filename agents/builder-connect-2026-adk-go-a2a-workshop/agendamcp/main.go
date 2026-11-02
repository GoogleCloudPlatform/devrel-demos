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

// Command agendamcp is an MCP server that answers questions about the agendas
// of Builder Connect (3 November 2026) and Google Cloud Summit Poland 2026
// (4 November 2026). It downloads both agendas from the event site when it
// starts, and serves streamable HTTP at /mcp.
package main

import (
	"context"
	"encoding/json"
	"log"
	"net/http"
	"os"

	"github.com/modelcontextprotocol/go-sdk/mcp"
)

type SearchInput struct {
	Query  string   `json:"query,omitempty" jsonschema:"Keywords matched against titles, speakers, tracks and descriptions, e.g. 'agents' or 'security BigQuery'. Leave empty to list everything in the time window."`
	Terms  []string `json:"terms,omitempty" jsonschema:"Exact names or phrases, e.g. technology names and aliases from the technology catalog. Only sessions mentioning at least one are returned, and each result lists the terms it mentions."`
	Day    string   `json:"day,omitempty" jsonschema:"Only sessions on this day, YYYY-MM-DD. Leave empty to search every day."`
	After  string   `json:"after,omitempty" jsonschema:"Only sessions starting at or after this time, HH:MM in Warsaw time."`
	Before string   `json:"before,omitempty" jsonschema:"Only sessions starting before this time, HH:MM in Warsaw time."`
}

type SessionSummary struct {
	ID       string   `json:"id"`
	Event    string   `json:"event"`
	Date     string   `json:"date"`
	Start    string   `json:"start"`
	End      string   `json:"end"`
	Title    string   `json:"title"`
	Track    string   `json:"track,omitempty"`
	Speakers []string `json:"speakers,omitempty"`
	// Note says "speakers not announced" when the agenda lists none.
	Note         string   `json:"note,omitempty"`
	MatchedIn    []string `json:"matched_in,omitempty"`
	MatchedTerms []string `json:"matched_terms,omitempty"`
	// MatchContext shows why a description-only match matched.
	MatchContext string `json:"match_context,omitempty"`
	Summary      string `json:"summary,omitempty"`
}

type SearchOutput struct {
	Timezone     string           `json:"timezone"`
	TotalMatches int              `json:"total_matches"`
	Sessions     []SessionSummary `json:"sessions"`
}

type GetInput struct {
	IDs []string `json:"ids" jsonschema:"Session ids, as returned by search_sessions. Pass every id you need in one call."`
}

type GetOutput struct {
	Sessions []Session `json:"sessions"`
	NotFound []string  `json:"not_found,omitempty"`
}

type PlanInput struct {
	IDs []string `json:"ids" jsonschema:"Ids of the sessions in the proposed plan."`
}

const maxResults = 150

func summary(desc string) string {
	r := []rune(desc)
	if len(r) <= 200 {
		return desc
	}
	return string(r[:200]) + "…"
}

func newServer(a *Agenda) *mcp.Server {
	s := mcp.NewServer(&mcp.Implementation{Name: "summit-agenda", Version: "v0.1.0"}, nil)

	// "the catalog" here and in SearchInput.Terms is deliberate, though the
	// server is now called technologies: every other wording tested made the
	// model split "I'm a Kotlin developer" into several searches and miss talks.
	mcp.AddTool(s, &mcp.Tool{
		Name: "search_sessions",
		Description: "Searches the agendas of " + a.DaysText() + ", both at PGE Narodowy, Warsaw. " +
			"Returns matching sessions ordered by time, with dates and times in Warsaw local time. " +
			"To find sessions about several things at once, such as technologies from the catalog, pass all their " +
			"names and aliases as terms in one call. Use get_sessions for full descriptions.",
	}, func(ctx context.Context, req *mcp.CallToolRequest, in SearchInput) (*mcp.CallToolResult, SearchOutput, error) {
		matches, total, err := a.Search(in.Query, in.Terms, in.Day, in.After, in.Before, maxResults)
		if err != nil {
			return nil, SearchOutput{}, err
		}
		out := SearchOutput{Timezone: "Europe/Warsaw", TotalMatches: total, Sessions: []SessionSummary{}}
		for _, m := range matches {
			s := SessionSummary{
				ID: m.ID, Event: m.Event, Date: m.Date, Start: m.Start, End: m.End, Title: m.Title, Track: m.Track,
				Speakers: m.Speakers, MatchedIn: m.MatchedIn, MatchedTerms: m.MatchedTerms, MatchContext: m.Context, Summary: summary(m.Description),
			}
			if len(s.Speakers) == 0 {
				s.Note = "speakers not announced"
			}
			out.Sessions = append(out.Sessions, s)
		}
		return nil, out, nil
	})

	mcp.AddTool(s, &mcp.Tool{
		Name: "get_sessions",
		Description: "Returns full descriptions and speakers for one or more sessions. " +
			"Fetch all the sessions you need in a single call. Times are Warsaw local time.",
	}, func(ctx context.Context, req *mcp.CallToolRequest, in GetInput) (*mcp.CallToolResult, GetOutput, error) {
		out := GetOutput{Sessions: []Session{}}
		for _, id := range in.IDs {
			if sess, ok := a.Find(id); ok {
				out.Sessions = append(out.Sessions, sess)
			} else {
				out.NotFound = append(out.NotFound, id)
			}
		}
		return nil, out, nil
	})
	mcp.AddTool(s, &mcp.Tool{
		Name: "check_plan",
		Description: "Checks a proposed schedule: returns the sessions in time order with their exact dates, start and " +
			"end times, and every pair that overlaps. Run it on a plan before presenting it.",
	}, func(ctx context.Context, req *mcp.CallToolRequest, in PlanInput) (*mcp.CallToolResult, PlanCheck, error) {
		return nil, a.CheckPlan(in.IDs), nil
	})
	return s
}

func main() {
	events, err := fetchEvents(context.Background())
	if err != nil {
		log.Fatalf("agenda: %v", err)
	}
	agenda, err := loadAgenda(events...)
	if err != nil {
		log.Fatalf("agenda: %v", err)
	}
	server := newServer(agenda)
	mux := http.NewServeMux()
	mux.Handle("/mcp", mcp.NewStreamableHTTPHandler(func(*http.Request) *mcp.Server { return server },
		&mcp.StreamableHTTPOptions{Stateless: true}))
	// All sessions as JSON, for presenters and for scoring test runs.
	mux.HandleFunc("/sessions.json", func(w http.ResponseWriter, r *http.Request) {
		w.Header().Set("Content-Type", "application/json")
		_ = json.NewEncoder(w).Encode(agenda.Sessions)
	})

	port := os.Getenv("PORT")
	if port == "" {
		port = "8090"
	}
	log.Printf("agenda MCP server: %d sessions from %s on http://localhost:%s/mcp", len(agenda.Sessions), agenda.DaysText(), port)
	log.Fatal(http.ListenAndServe(":"+port, mux))
}
