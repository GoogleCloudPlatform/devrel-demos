// Copyright 2026 Google LLC
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//     http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.

package main

import (
	"encoding/json"
	"fmt"
	"os"
	"sort"
	"strings"
)

func load(path string) (*Snapshot, error) {
	data, err := os.ReadFile(path)
	if err != nil {
		return nil, err
	}
	var s Snapshot
	if err := json.Unmarshal(data, &s); err != nil {
		return nil, fmt.Errorf("%s: %w", path, err)
	}
	return &s, nil
}

// runDiff prints what differs between two snapshots, for example the 2020
// baseline and a 2026 cluster.
func runDiff(args []string) int {
	if len(args) != 2 {
		fmt.Fprintln(os.Stderr, "usage: census diff A.json B.json")
		return 2
	}
	a, err := load(args[0])
	if err != nil {
		fmt.Fprintln(os.Stderr, err)
		return 1
	}
	b, err := load(args[1])
	if err != nil {
		fmt.Fprintln(os.Stderr, err)
		return 1
	}
	fmt.Print(renderDiff(a, b))
	return 0
}

func renderDiff(a, b *Snapshot) string {
	var out strings.Builder
	label := func(s *Snapshot) string {
		if s.Context != "" {
			return s.Context
		}
		return s.ServerVersion
	}
	out.WriteString(row("Item", label(a), label(b)))
	out.WriteString(row("---", "---", "---"))
	out.WriteString(row("Server version", a.ServerVersion, b.ServerVersion))
	for _, c := range capabilities {
		if a.Capabilities[c.ID] != b.Capabilities[c.ID] {
			out.WriteString(row(c.Label, yesNo(a.Capabilities[c.ID]), yesNo(b.Capabilities[c.ID])))
		}
	}
	groups := map[string]bool{}
	for g := range a.APIGroups {
		groups[g] = true
	}
	for g := range b.APIGroups {
		groups[g] = true
	}
	var names []string
	for g := range groups {
		names = append(names, g)
	}
	sort.Strings(names)
	for _, g := range names {
		av, bv := strings.Join(a.APIGroups[g], ", "), strings.Join(b.APIGroups[g], ", ")
		if av != bv {
			if av == "" {
				av = "absent"
			}
			if bv == "" {
				bv = "absent"
			}
			out.WriteString(row("API group "+g, av, bv))
		}
	}
	ar, br := strings.Join(a.RuntimeClasses, ", "), strings.Join(b.RuntimeClasses, ", ")
	if ar != br {
		out.WriteString(row("RuntimeClasses", orNone(ar), orNone(br)))
	}
	return out.String()
}

func orNone(s string) string {
	if s == "" {
		return "none"
	}
	return s
}
