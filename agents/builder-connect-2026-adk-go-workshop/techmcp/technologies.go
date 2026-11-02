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
	_ "embed"
	"encoding/json"
	"fmt"
	"regexp"
	"slices"
	"sort"
	"strings"
)

// technologies.json is written by hand; releases.json is generated from GitHub
// by refresh-releases.py and confirms every SDK listed in technologies.json.
var (
	//go:embed technologies.json
	technologiesJSON []byte
	//go:embed releases.json
	releasesJSON []byte
)

type sdkSpec struct {
	Language string `json:"language"`
	Repo     string `json:"repo"`
	Path     string `json:"path"`
}

type techSpec struct {
	Name       string    `json:"name"`
	Aliases    []string  `json:"aliases"`
	Kind       string    `json:"kind"`
	Vendor     string    `json:"vendor"`
	OpenSource bool      `json:"open_source"`
	Summary    string    `json:"summary"`
	Related    []string  `json:"related"`
	SDKs       []sdkSpec `json:"sdks"`
}

// Release is a GitHub release.
type Release struct {
	Tag  string `json:"tag"`
	Date string `json:"date"` // YYYY-MM-DD
}

type releaseData struct {
	Repos map[string]struct {
		FirstRelease  *Release `json:"first_release"`
		LatestRelease *Release `json:"latest_release"`
	} `json:"repos"`
	Paths map[string]bool `json:"paths"`
}

// SDK is an official library or implementation of a technology in one
// language. Release fields are set for SDKs with their own repository.
type SDK struct {
	Language      string   `json:"language"`
	URL           string   `json:"url"`
	FirstRelease  *Release `json:"first_release,omitempty"`
	LatestRelease *Release `json:"latest_release,omitempty"`
}

// Technology is a framework, protocol, model or product covered at the
// conference.
type Technology struct {
	Name       string   `json:"name"`
	Aliases    []string `json:"aliases"`
	Kind       string   `json:"kind"`
	Vendor     string   `json:"vendor"`
	OpenSource bool     `json:"open_source"`
	Summary    string   `json:"summary"`
	Related    []string `json:"related,omitempty"`
	// Languages lists the programming languages with an official SDK.
	Languages []string `json:"languages,omitempty"`
	// FirstRelease is the earliest GitHub release of any of its SDKs, and
	// LastUpdated the most recent one.
	FirstRelease string `json:"first_release,omitempty"`
	LastUpdated  string `json:"last_updated,omitempty"`
	SDKs         []SDK  `json:"sdks,omitempty"`
}

// Technologies is the immutable list of technologies, sorted by name.
type Technologies []Technology

func loadTechnologies(techData, releaseFile []byte) (Technologies, error) {
	var spec struct {
		Technologies []techSpec `json:"technologies"`
	}
	if err := json.Unmarshal(techData, &spec); err != nil {
		return nil, fmt.Errorf("decode technologies: %w", err)
	}
	var rel releaseData
	if err := json.Unmarshal(releaseFile, &rel); err != nil {
		return nil, fmt.Errorf("decode releases: %w", err)
	}
	var ts Technologies
	for _, t := range spec.Technologies {
		tech := Technology{
			Name: t.Name, Aliases: t.Aliases, Kind: t.Kind, Vendor: t.Vendor,
			OpenSource: t.OpenSource, Summary: t.Summary, Related: t.Related,
		}
		for _, s := range t.SDKs {
			sdk := SDK{Language: s.Language, URL: "https://github.com/" + s.Repo}
			if s.Path != "" {
				if !rel.Paths[s.Repo+"/"+s.Path] {
					return nil, fmt.Errorf("%s: %s SDK %s/%s is not confirmed in releases.json; run refresh-releases.py", t.Name, s.Language, s.Repo, s.Path)
				}
				sdk.URL += "/tree/HEAD/" + s.Path
			} else {
				r, ok := rel.Repos[s.Repo]
				if !ok {
					return nil, fmt.Errorf("%s: %s SDK %s is not confirmed in releases.json; run refresh-releases.py", t.Name, s.Language, s.Repo)
				}
				sdk.FirstRelease, sdk.LatestRelease = r.FirstRelease, r.LatestRelease
				if r.FirstRelease != nil && (tech.FirstRelease == "" || r.FirstRelease.Date < tech.FirstRelease) {
					tech.FirstRelease = r.FirstRelease.Date
				}
				if r.LatestRelease != nil && r.LatestRelease.Date > tech.LastUpdated {
					tech.LastUpdated = r.LatestRelease.Date
				}
			}
			if s.Language != "Specification" && !slices.Contains(tech.Languages, s.Language) {
				tech.Languages = append(tech.Languages, s.Language)
			}
			tech.SDKs = append(tech.SDKs, sdk)
		}
		ts = append(ts, tech)
	}
	sort.Slice(ts, func(i, j int) bool { return ts[i].Name < ts[j].Name })
	return ts, nil
}

// languageAliases maps how people name a language to its name in
// technologies.json.
var languageAliases = map[string]string{
	"javascript": "typescript", "js": "typescript", "node": "typescript", "node.js": "typescript", "nodejs": "typescript", "ts": "typescript",
	"golang": "go", "csharp": "c#", ".net": "c#", "dotnet": "c#", "py": "python",
}

func normLanguage(l string) string {
	l = strings.ToLower(strings.TrimSpace(l))
	if a, ok := languageAliases[l]; ok {
		return a
	}
	return l
}

// Filter selects technologies. Zero fields match everything.
type Filter struct {
	Query              string
	Language           string
	Kind               string
	OpenSource         *bool
	FirstReleasedAfter string // YYYY-MM-DD, inclusive
	UpdatedAfter       string // YYYY-MM-DD, inclusive
}

var datePattern = regexp.MustCompile(`^\d{4}-\d{2}-\d{2}$`)

// Find returns the technologies matching every set field of f.
func (ts Technologies) Find(f Filter) ([]Technology, error) {
	for _, d := range []string{f.FirstReleasedAfter, f.UpdatedAfter} {
		if d != "" && !datePattern.MatchString(d) {
			return nil, fmt.Errorf("dates must be YYYY-MM-DD, got %q", d)
		}
	}
	words := strings.Fields(strings.ToLower(f.Query))
	var out []Technology
	for _, t := range ts {
		if f.Language != "" && !slices.ContainsFunc(t.Languages, func(l string) bool { return normLanguage(l) == normLanguage(f.Language) }) {
			continue
		}
		if f.Kind != "" && !strings.Contains(strings.ToLower(t.Kind), strings.ToLower(f.Kind)) {
			continue
		}
		if f.OpenSource != nil && t.OpenSource != *f.OpenSource {
			continue
		}
		if f.FirstReleasedAfter != "" && (t.FirstRelease == "" || t.FirstRelease < f.FirstReleasedAfter) {
			continue
		}
		if f.UpdatedAfter != "" && (t.LastUpdated == "" || t.LastUpdated < f.UpdatedAfter) {
			continue
		}
		if len(words) > 0 {
			text := strings.ToLower(strings.Join(append([]string{t.Name, t.Kind, t.Vendor, t.Summary}, t.Aliases...), " "))
			if !slices.ContainsFunc(words, func(w string) bool { return strings.Contains(text, w) }) {
				continue
			}
		}
		out = append(out, t)
	}
	return out, nil
}

// Get returns the technologies with the given names or aliases, and the
// names it did not recognize.
func (ts Technologies) Get(names []string) (found []Technology, notFound []string) {
	for _, n := range names {
		i := slices.IndexFunc(ts, func(t Technology) bool {
			return strings.EqualFold(t.Name, n) || slices.ContainsFunc(t.Aliases, func(a string) bool { return strings.EqualFold(a, n) })
		})
		if i < 0 {
			notFound = append(notFound, n)
			continue
		}
		found = append(found, ts[i])
	}
	return found, notFound
}
