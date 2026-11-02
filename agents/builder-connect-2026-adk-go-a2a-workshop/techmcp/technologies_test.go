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
	"slices"
	"strings"
	"testing"
)

func load(t *testing.T) Technologies {
	t.Helper()
	ts, err := loadTechnologies(technologiesJSON, releasesJSON)
	if err != nil {
		t.Fatal(err)
	}
	return ts
}

func names(ts []Technology) []string {
	var out []string
	for _, t := range ts {
		out = append(out, t.Name)
	}
	return out
}

func TestEverySDKConfirmed(t *testing.T) {
	// loadTechnologies fails on an SDK that releases.json does not confirm.
	ts := load(t)
	adk, _ := ts.Get([]string{"ADK"})
	if len(adk) != 1 {
		t.Fatalf("ADK not found by alias")
	}
	want := []string{"Python", "Java", "Go", "TypeScript", "Kotlin"}
	if !slices.Equal(adk[0].Languages, want) {
		t.Errorf("ADK languages = %v, want %v", adk[0].Languages, want)
	}
	if adk[0].FirstRelease == "" || adk[0].LastUpdated < adk[0].FirstRelease {
		t.Errorf("ADK releases first=%q last=%q", adk[0].FirstRelease, adk[0].LastUpdated)
	}

	broken := strings.Replace(string(technologiesJSON), `"google/adk-go"`, `"google/adk-cobol"`, 1)
	if _, err := loadTechnologies([]byte(broken), releasesJSON); err == nil {
		t.Error("loadTechnologies accepted an SDK missing from releases.json")
	}
}

func TestFind(t *testing.T) {
	ts := load(t)
	yes := true
	tests := []struct {
		name    string
		f       Filter
		want    []string // must be included
		exclude []string
	}{
		{"java", Filter{Language: "Java"},
			[]string{"Agent Development Kit (ADK)", "Agent2Agent (A2A)", "Model Context Protocol (MCP)", "BigQuery", "Firebase AI Logic", "Apache Beam"},
			[]string{"Kueue", "Gemini CLI", "Gemini", "Apache Airflow"}},
		{"javascript means the TypeScript SDKs", Filter{Language: "javascript"},
			[]string{"Genkit", "Gemini CLI"}, []string{"Kueue"}},
		{"protocols", Filter{Kind: "protocol"},
			[]string{"Agent2Agent (A2A)", "Model Context Protocol (MCP)"}, []string{"Agent Development Kit (ADK)"}},
		{"open-source models", Filter{Kind: "model", OpenSource: &yes},
			[]string{"Gemma", "Bielik"}, []string{"Gemini"}},
		{"first released in 2026", Filter{FirstReleasedAfter: "2026-01-01"},
			[]string{"Agents CLI"}, []string{"Agent Development Kit (ADK)", "Gemini"}},
		{"keyword", Filter{Query: "security"},
			[]string{"Model Armor", "Agent Gateway"}, []string{"BigQuery"}},
	}
	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			got, err := ts.Find(tt.f)
			if err != nil {
				t.Fatal(err)
			}
			n := names(got)
			for _, w := range tt.want {
				if !slices.Contains(n, w) {
					t.Errorf("missing %q in %v", w, n)
				}
			}
			for _, x := range tt.exclude {
				if slices.Contains(n, x) {
					t.Errorf("unexpected %q in %v", x, n)
				}
			}
		})
	}
	if _, err := ts.Find(Filter{UpdatedAfter: "last year"}); err == nil {
		t.Error("want an error for a non-YYYY-MM-DD date")
	}
}

func TestGet(t *testing.T) {
	ts := load(t)
	found, notFound := ts.Get([]string{"model context protocol", "Kueue", "COBOL Agents"})
	if got := names(found); !slices.Equal(got, []string{"Model Context Protocol (MCP)", "Kueue"}) {
		t.Errorf("found %v", got)
	}
	if !slices.Equal(notFound, []string{"COBOL Agents"}) {
		t.Errorf("notFound = %v", notFound)
	}
	for _, s := range found[0].SDKs {
		if !strings.HasPrefix(s.URL, "https://github.com/modelcontextprotocol/") {
			t.Errorf("unexpected SDK URL %q", s.URL)
		}
	}
}
