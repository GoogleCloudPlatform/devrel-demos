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

package main

import (
	"context"
	"slices"
	"strings"
	"sync"
	"testing"
)

// events downloads the agendas once for all the tests.
var events = sync.OnceValues(func() ([][]byte, error) { return fetchEvents(context.Background()) })

func load(t *testing.T) *Agenda {
	t.Helper()
	bodies, err := events()
	if err != nil {
		t.Skipf("agenda not reachable: %v", err)
	}
	a, err := loadAgenda(bodies...)
	if err != nil {
		t.Fatal(err)
	}
	return a
}

func find(t *testing.T, a *Agenda, title string) Session {
	t.Helper()
	for _, s := range a.Sessions {
		if s.Title == title {
			return s
		}
	}
	t.Fatalf("no session %q", title)
	return Session{}
}

func TestLoadBothDays(t *testing.T) {
	a := load(t)
	want := []Day{{"2026-11-03", "Builder Connect"}, {"2026-11-04", "Google Cloud Summit Poland 2026"}}
	if !slices.Equal(a.Days, want) {
		t.Errorf("days = %v, want %v", a.Days, want)
	}
	ids := map[string]bool{}
	for _, s := range a.Sessions {
		if ids[s.ID] {
			t.Errorf("duplicate session id %s", s.ID)
		}
		ids[s.ID] = true
		if strings.HasPrefix(s.Title, "Fortifying the Cloud") || s.Title == "Builder Connect" {
			t.Errorf("placeholder kept as a session: %q on %s at %s", s.Title, s.Date, s.Start)
		}
	}
}

// speakerNames drops the company after each name: the event site edits it.
func speakerNames(speakers []string) []string {
	var names []string
	for _, s := range speakers {
		name, _, _ := strings.Cut(s, ",")
		names = append(names, name)
	}
	return names
}

func TestSessionFields(t *testing.T) {
	a := load(t)
	tests := []struct {
		title, date, start, end string
		speakers                []string
	}{
		// Stored as 13:30 UTC; Warsaw is UTC+1 in November. Speakers come
		// from a list in the description.
		{"The Governance Agent That Never Sleeps", "2026-11-04", "14:30", "14:45",
			[]string{"Warun Kumar", "Thangaraju Rajasekaran"}},
		// Speaker given as plain text in the description.
		{"ADK + A2A workshop", "2026-11-03", "12:05", "13:30", []string{"Maciej Zasada"}},
		// One structured speaker plus another named in the description.
		{"Building Faster Web Apps: Edge Optimization and Kubernetes-Native CDN", "2026-11-03", "16:10", "17:35",
			[]string{"Konrad Argasiński", "Radek Scheller"}},
	}
	for _, tt := range tests {
		s := find(t, a, tt.title)
		if s.Date != tt.date || s.Start != tt.start || s.End != tt.end {
			t.Errorf("%q at %s %s-%s, want %s %s-%s", tt.title, s.Date, s.Start, s.End, tt.date, tt.start, tt.end)
		}
		if !slices.Equal(speakerNames(s.Speakers), tt.speakers) {
			t.Errorf("%q speakers = %q, want %q", tt.title, s.Speakers, tt.speakers)
		}
		if strings.Contains(s.Description, "Speaker") {
			t.Errorf("%q description still contains the speaker list", tt.title)
		}
	}
	keynotes := 0
	for _, s := range a.Sessions {
		if s.Title == "Opening Keynote" && s.Start == "09:30" {
			keynotes++
		}
	}
	if keynotes != 1 {
		t.Errorf("opening keynote listed %d times, want 1 after merging tracks", keynotes)
	}
}

func TestSearch(t *testing.T) {
	a := load(t)
	hits, _, err := a.Search("agents", nil, "2026-11-04", "13:00", "", maxResults)
	if err != nil {
		t.Fatal(err)
	}
	found := false
	for _, h := range hits {
		if strings.HasPrefix(h.Title, "SilkyPulse") {
			found = true
		}
		if h.Date != "2026-11-04" || h.Start < "13:00" {
			t.Errorf("%q on %s at %s is outside the filter", h.Title, h.Date, h.Start)
		}
	}
	if !found {
		t.Error(`"agents" did not match the Polish "Wieloagentowe" session`)
	}

	both, _, err := a.Search("agents", nil, "", "", "", maxResults)
	if err != nil {
		t.Fatal(err)
	}
	days := map[string]bool{}
	for _, h := range both {
		days[h.Date] = true
	}
	if !days["2026-11-03"] || !days["2026-11-04"] {
		t.Errorf("search without a day covered %v, want both days", days)
	}

	// The workshop's listing never says "agent"; it is found through the
	// spelled-out "ADK (Agent Development Kit)", and keeps its own title.
	agentHits, _, err := a.Search("agents", nil, "2026-11-03", "", "", maxResults)
	if err != nil {
		t.Fatal(err)
	}
	if !slices.ContainsFunc(agentHits, func(h Hit) bool { return h.Title == "ADK + A2A workshop" }) {
		t.Error(`"agents" did not find the ADK + A2A workshop`)
	}

	for _, bad := range []struct{ day, after string }{{"2026-11-05", ""}, {"", "1pm"}} {
		if _, _, err := a.Search("x", nil, bad.day, bad.after, "", maxResults); err == nil {
			t.Errorf("Search(day=%q, after=%q): want an error", bad.day, bad.after)
		}
	}
}

func TestCheckPlan(t *testing.T) {
	a := load(t)
	gov := find(t, a, "The Governance Agent That Never Sleeps") // 4 Nov 14:30-14:45
	workshop := find(t, a, "ADK + A2A workshop")                // 3 Nov 12:05-13:30
	var sameTimeOtherDay, overlapping Session
	for _, s := range a.Sessions {
		if s.Date == "2026-11-03" && s.Start == "14:30" {
			sameTimeOtherDay = s
		}
		if s.Date == "2026-11-03" && s.ID != workshop.ID && s.Start > "12:05" && s.Start < "13:30" {
			overlapping = s
		}
	}
	if sameTimeOtherDay.ID == "" || overlapping.ID == "" {
		t.Fatal("test data changed: no session at 14:30 on 3 Nov, or none during the workshop")
	}

	got := a.CheckPlan([]string{gov.ID, sameTimeOtherDay.ID, workshop.ID})
	if !got.OK || len(got.Overlaps) != 0 {
		t.Errorf("plan across two days reported overlaps: %+v", got.Overlaps)
	}
	if got.Sessions[0].ID != workshop.ID || got.Sessions[2].ID != gov.ID {
		t.Errorf("plan not in time order: %+v", got.Sessions)
	}

	got = a.CheckPlan([]string{workshop.ID, overlapping.ID, "nope"})
	if got.OK || len(got.Overlaps) != 1 || !slices.Equal(got.NotFound, []string{"nope"}) {
		t.Errorf("CheckPlan = %+v, want one overlap and one unknown id", got)
	}
}

func TestSearchTerms(t *testing.T) {
	a := load(t)
	hits, _, err := a.Search("", []string{"BigQuery", "Iceberg", "Beam"}, "2026-11-03", "", "", maxResults)
	if err != nil {
		t.Fatal(err)
	}
	got := map[string][]string{}
	for _, h := range hits {
		got[h.Title] = h.MatchedTerms
	}
	// BigQuery is only mentioned in this description, in passing.
	if terms := got["Gemini platform - The New Standard: Building Agentic Workflows for Fragmented Ecosystems"]; !slices.Equal(terms, []string{"BigQuery"}) {
		t.Errorf("Gemini platform talk matched %v, want [BigQuery]", terms)
	}
	if terms := got["Beyond the Data Lake: Open Table Formats and Cross-Cloud Federation on Google Cloud"]; !slices.Contains(terms, "Iceberg") {
		t.Errorf("Beyond the Data Lake matched %v, want Iceberg among them", terms)
	}
	for title, terms := range got {
		if len(terms) == 0 {
			t.Errorf("%q returned without a matched term", title)
		}
	}
	// Terms match whole words: "ADK" does not match inside another word, and
	// the spelled-out abbreviation still counts.
	adk, _, err := a.Search("", []string{"Agent Development Kit"}, "2026-11-03", "", "", maxResults)
	if err != nil {
		t.Fatal(err)
	}
	if !slices.ContainsFunc(adk, func(h Hit) bool { return h.Title == "ADK + A2A workshop" }) {
		t.Error(`"Agent Development Kit" did not find the ADK + A2A workshop`)
	}
}
