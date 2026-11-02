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

// Command techmcp is an MCP server with facts about the frameworks, protocols,
// models and products covered at Builder Connect and Google Cloud Summit
// Poland 2026: what they are, which languages have official SDKs, and when
// they were released. It serves streamable HTTP at /mcp.
package main

import (
	"context"
	"log"
	"net/http"
	"os"

	"github.com/modelcontextprotocol/go-sdk/mcp"
)

type FindInput struct {
	Query              string `json:"query,omitempty" jsonschema:"Keywords matched against names, aliases, kinds, vendors and summaries, e.g. 'agents' or 'security'."`
	Language           string `json:"language,omitempty" jsonschema:"Only technologies with an official SDK in this programming language, e.g. 'Java', 'Go', 'Python', 'TypeScript'."`
	Kind               string `json:"kind,omitempty" jsonschema:"Only technologies whose kind contains this, e.g. 'framework', 'protocol', 'model', 'security'."`
	OpenSource         *bool  `json:"open_source,omitempty" jsonschema:"Only open-source (true) or only proprietary (false) technologies."`
	FirstReleasedAfter string `json:"first_released_after,omitempty" jsonschema:"Only technologies whose first GitHub release is on or after this date, YYYY-MM-DD."`
	UpdatedAfter       string `json:"updated_after,omitempty" jsonschema:"Only technologies with a GitHub release on or after this date, YYYY-MM-DD."`
}

// Summary is the short form of a technology returned by find_technologies.
type Summary struct {
	Name         string   `json:"name"`
	Aliases      []string `json:"aliases"`
	Kind         string   `json:"kind"`
	Vendor       string   `json:"vendor"`
	OpenSource   bool     `json:"open_source"`
	Languages    []string `json:"languages,omitempty"`
	FirstRelease string   `json:"first_release,omitempty"`
	LastUpdated  string   `json:"last_updated,omitempty"`
}

type FindOutput struct {
	Technologies []Summary `json:"technologies"`
}

type GetInput struct {
	Names []string `json:"names" jsonschema:"Technology names or aliases. Pass every technology you need in one call."`
}

type GetOutput struct {
	Technologies []Technology `json:"technologies"`
	NotFound     []string     `json:"not_found,omitempty"`
}

func newServer(ts Technologies) *mcp.Server {
	s := mcp.NewServer(&mcp.Implementation{Name: "technologies", Version: "v0.1.0"}, nil)

	mcp.AddTool(s, &mcp.Tool{
		Name: "find_technologies",
		Description: "Finds frameworks, protocols, models and products covered at the conference. Filter by keyword, " +
			"programming language with an official SDK, kind, open source, or GitHub release dates. Returns each " +
			"technology's name and aliases, which are the words to search the agenda for.",
	}, func(ctx context.Context, req *mcp.CallToolRequest, in FindInput) (*mcp.CallToolResult, FindOutput, error) {
		techs, err := ts.Find(Filter{
			Query: in.Query, Language: in.Language, Kind: in.Kind, OpenSource: in.OpenSource,
			FirstReleasedAfter: in.FirstReleasedAfter, UpdatedAfter: in.UpdatedAfter,
		})
		if err != nil {
			return nil, FindOutput{}, err
		}
		out := FindOutput{Technologies: []Summary{}}
		for _, t := range techs {
			out.Technologies = append(out.Technologies, Summary{
				Name: t.Name, Aliases: t.Aliases, Kind: t.Kind, Vendor: t.Vendor, OpenSource: t.OpenSource,
				Languages: t.Languages, FirstRelease: t.FirstRelease, LastUpdated: t.LastUpdated,
			})
		}
		return nil, out, nil
	})

	mcp.AddTool(s, &mcp.Tool{
		Name: "get_technologies",
		Description: "Returns full details for technologies: summary, related technologies, and each official SDK " +
			"with its GitHub URL and first and latest release.",
	}, func(ctx context.Context, req *mcp.CallToolRequest, in GetInput) (*mcp.CallToolResult, GetOutput, error) {
		found, notFound := ts.Get(in.Names)
		if found == nil {
			found = []Technology{}
		}
		return nil, GetOutput{Technologies: found, NotFound: notFound}, nil
	})
	return s
}

func main() {
	techs, err := loadTechnologies(technologiesJSON, releasesJSON)
	if err != nil {
		log.Fatalf("technologies: %v", err)
	}
	server := newServer(techs)
	mux := http.NewServeMux()
	mux.Handle("/mcp", mcp.NewStreamableHTTPHandler(func(*http.Request) *mcp.Server { return server },
		&mcp.StreamableHTTPOptions{Stateless: true}))

	port := os.Getenv("PORT")
	if port == "" {
		port = "8092"
	}
	log.Printf("technologies MCP server: %d technologies on http://localhost:%s/mcp", len(techs), port)
	log.Fatal(http.ListenAndServe(":"+port, mux))
}
