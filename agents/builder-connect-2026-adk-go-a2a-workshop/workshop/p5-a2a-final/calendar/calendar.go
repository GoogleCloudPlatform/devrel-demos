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

// The attendee's calendar: its tools, which main.go gives the agent, and the
// page on :8002 that shows it.

package main

import (
	_ "embed"
	"encoding/json"
	"log"
	"net/http"
	"slices"
	"strings"
	"sync"

	"google.golang.org/adk/v2/agent"
	"google.golang.org/adk/v2/tool"
	"google.golang.org/adk/v2/tool/functiontool"
)

// Event is one session in the attendee's calendar.
type Event struct {
	Title string `json:"title" jsonschema:"Session title, exactly as the concierge gave it."`
	Date  string `json:"date" jsonschema:"Day of the session, YYYY-MM-DD."`
	Start string `json:"start" jsonschema:"Start time, HH:MM Warsaw time."`
	End   string `json:"end" jsonschema:"End time, HH:MM Warsaw time."`
	Note  string `json:"note,omitempty" jsonschema:"Optional note, e.g. the room or a question for the speaker."`
}

// Calendar is the tools' output: every event, in time order.
type Calendar struct {
	Events []Event `json:"events"`
}

// calendar keeps events in memory, so it resets when the agent restarts.
type calendar struct {
	mu     sync.Mutex
	events []Event
}

// newCalendar returns an empty calendar, with the tools that work on it:
// add_to_calendar and list_calendar.
func newCalendar() (*calendar, []tool.Tool, error) {
	c := &calendar{}
	add, err := functiontool.New(functiontool.Config{
		Name:        "add_to_calendar",
		Description: "Adds a session to the attendee's calendar, or updates it if it is already there. Returns the whole calendar.",
	}, c.add)
	if err != nil {
		return nil, nil, err
	}
	list, err := functiontool.New(functiontool.Config{
		Name:        "list_calendar",
		Description: "Returns the attendee's calendar in time order.",
	}, c.list)
	if err != nil {
		return nil, nil, err
	}
	return c, []tool.Tool{add, list}, nil
}

func (c *calendar) add(_ agent.Context, e Event) (Calendar, error) {
	c.mu.Lock()
	defer c.mu.Unlock()
	// Adding a session again updates it instead of duplicating it.
	c.events = slices.DeleteFunc(c.events, func(x Event) bool {
		return x.Date == e.Date && strings.EqualFold(x.Title, e.Title)
	})
	c.events = append(c.events, e)
	return c.snapshot(), nil
}

func (c *calendar) list(_ agent.Context, _ struct{}) (Calendar, error) {
	return c.export(), nil
}

// export returns every event, in time order.
func (c *calendar) export() Calendar {
	c.mu.Lock()
	defer c.mu.Unlock()
	return c.snapshot()
}

func (c *calendar) snapshot() Calendar {
	events := append([]Event{}, c.events...) // [] rather than null when empty
	slices.SortStableFunc(events, func(a, b Event) int {
		return strings.Compare(a.Date+a.Start, b.Date+b.Start)
	})
	return Calendar{Events: events}
}

//go:embed index.html
var indexHTML []byte

// serveCalendar serves the calendar for people, next to the agent: its export
// at /calendar.json, and a page at / that shows it.
func serveCalendar(cal *calendar) {
	mux := http.NewServeMux()
	mux.HandleFunc("GET /{$}", func(w http.ResponseWriter, r *http.Request) {
		w.Header().Set("Content-Type", "text/html; charset=utf-8")
		w.Write(indexHTML)
	})
	mux.HandleFunc("GET /calendar.json", func(w http.ResponseWriter, r *http.Request) {
		w.Header().Set("Content-Type", "application/json")
		json.NewEncoder(w).Encode(cal.export())
	})
	log.Print("Calendar page on http://localhost:8002/")
	log.Fatal(http.ListenAndServe("localhost:8002", mux))
}
