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

// Command census records what a Kubernetes cluster can do: served APIs, named
// capabilities, RuntimeClasses, feature gates, and (with "knobs") the effective
// kubelet configuration per node pool. "diff" compares two snapshots, which is
// how Ep1 builds its "git diff 2020..2026" table.
//
// Usage:
//
//	census [--context CTX]... [--format md|json] [--out-dir DIR]
//	census knobs [--context CTX]... [--format md|json]
//	census diff A.json B.json
package main

import (
	"flag"
	"fmt"
	"os"
	"strings"
)

type stringList []string

func (s *stringList) String() string     { return strings.Join(*s, ",") }
func (s *stringList) Set(v string) error { *s = append(*s, v); return nil }

func usage() {
	fmt.Fprint(os.Stderr, `census: record what a Kubernetes cluster can do.

  census [--context CTX]... [--format md|json] [--out-dir DIR]
  census knobs [--context CTX]... [--format md|json]
  census diff A.json B.json
`)
}

func main() {
	args := os.Args[1:]
	if len(args) > 0 {
		switch args[0] {
		case "knobs":
			os.Exit(runKnobs(args[1:]))
		case "diff":
			os.Exit(runDiff(args[1:]))
		case "help", "-h", "--help":
			usage()
			return
		}
	}
	os.Exit(runCensus(args))
}

type commonFlags struct {
	contexts   stringList
	kubeconfig string
	format     string
}

func parseCommon(name string, args []string, extra func(*flag.FlagSet)) (*commonFlags, error) {
	fs := flag.NewFlagSet(name, flag.ContinueOnError)
	c := &commonFlags{}
	fs.Var(&c.contexts, "context", "kubeconfig context (repeatable; default: current context)")
	fs.StringVar(&c.kubeconfig, "kubeconfig", "", "path to kubeconfig (default: standard loading rules)")
	fs.StringVar(&c.format, "format", "md", "output format: md or json")
	if extra != nil {
		extra(fs)
	}
	if err := fs.Parse(args); err != nil {
		return nil, err
	}
	if len(c.contexts) == 0 {
		c.contexts = stringList{""}
	}
	return c, nil
}
