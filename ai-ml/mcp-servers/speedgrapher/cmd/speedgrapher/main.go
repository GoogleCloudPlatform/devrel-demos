// Copyright 2025 Google LLC
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
	"context"
	"flag"
	"fmt"
	"os"
	"os/signal"
	"syscall"

	"github.com/danicat/speedgrapher/internal/prompts"
	"github.com/danicat/speedgrapher/internal/tools/fog"
	"github.com/danicat/speedgrapher/internal/tools/seo"
	"github.com/modelcontextprotocol/go-sdk/mcp"
)

var version = "dev"

func main() {
	showVersion := flag.Bool("version", false, "Show the version and exit.")
	editorialGuidelines := flag.String("editorial", "EDITORIAL.md", "Path to the editorial guidelines file.")
	localizationGuidelines := flag.String("localization", "LOCALIZATION.md", "Path to the localization guidelines file.")
	flag.Parse()

	if *showVersion {
		fmt.Println(version)
		return
	}

	ctx, stop := signal.NotifyContext(context.Background(), syscall.SIGINT, syscall.SIGTERM)
	defer stop()
	if err := run(ctx, *editorialGuidelines, *localizationGuidelines); err != nil {
		fmt.Fprintln(os.Stderr, err)
		os.Exit(1)
	}
}

func run(ctx context.Context, editorialGuidelines, localizationGuidelines string) error {
	server := mcp.NewServer(
		&mcp.Implementation{Name: "speedgrapher"},
		nil,
	)
	prompts.Register(server, editorialGuidelines, localizationGuidelines)
	fog.Register(server)
	seo.Register(server)
	return server.Run(ctx, &mcp.StdioTransport{})
}
