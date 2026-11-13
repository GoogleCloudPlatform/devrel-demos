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
	"fmt"
	"sort"
	"strings"
)

func yesNo(b bool) string {
	if b {
		return "yes"
	}
	return "no"
}

func gateCell(g Gate, ok bool) string {
	if !ok {
		return "n/a"
	}
	s := "off"
	if g.Enabled {
		s = "on"
	}
	if g.Stage != "" {
		s += " (" + strings.ToLower(g.Stage) + ")"
	}
	return s
}

func row(cells ...string) string { return "| " + strings.Join(cells, " | ") + " |\n" }

func renderCensus(snaps []*Snapshot) string {
	var b strings.Builder
	header := []string{"Capability"}
	for _, s := range snaps {
		header = append(header, s.Context)
	}
	b.WriteString(row(header...))
	sep := make([]string, len(header))
	for i := range sep {
		sep[i] = "---"
	}
	b.WriteString(row(sep...))

	cells := func(label string, f func(*Snapshot) string) {
		r := []string{label}
		for _, s := range snaps {
			r = append(r, f(s))
		}
		b.WriteString(row(r...))
	}
	cells("Server version", func(s *Snapshot) string { return s.ServerVersion })
	for _, c := range capabilities {
		id := c.ID
		cells(c.Label, func(s *Snapshot) string { return yesNo(s.Capabilities[id]) })
	}
	cells("RuntimeClasses", func(s *Snapshot) string {
		if len(s.RuntimeClasses) == 0 {
			return "none"
		}
		return strings.Join(s.RuntimeClasses, ", ")
	})
	for _, name := range tableGates {
		gate := name
		cells("Feature gate "+gate+" (apiserver)", func(s *Snapshot) string {
			g, ok := s.FeatureGates[gate]
			return gateCell(g, ok)
		})
	}
	cells("Nodes reporting declaredFeatures", func(s *Snapshot) string {
		n := 0
		for _, node := range s.Nodes {
			if len(node.DeclaredFeatures) > 0 {
				n++
			}
		}
		return fmt.Sprintf("%d/%d", n, len(s.Nodes))
	})
	var errs []string
	for _, s := range snaps {
		for _, e := range s.Errors {
			errs = append(errs, s.Context+": "+e)
		}
	}
	if len(errs) > 0 {
		sort.Strings(errs)
		b.WriteString("\nErrors while collecting:\n")
		for _, e := range errs {
			b.WriteString("- " + e + "\n")
		}
	}
	return b.String()
}
