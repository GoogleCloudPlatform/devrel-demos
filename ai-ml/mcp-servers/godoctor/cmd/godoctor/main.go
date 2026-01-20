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

// Package main is the entry point for the godoctor MCP server.
package main

import (
	"context"
	"fmt"
	"os"
	"os/signal"
	"sort"
	"syscall"

	"github.com/danicat/godoctor/internal/config"
	"github.com/danicat/godoctor/internal/graph"
	"github.com/danicat/godoctor/internal/instructions"
	"github.com/danicat/godoctor/internal/server"
	"github.com/danicat/godoctor/internal/toolnames"
)

var (
	version = "dev"
)

func main() {
	os.Exit(runMain())
}

func runMain() int {
	ctx, stop := signal.NotifyContext(context.Background(), syscall.SIGINT, syscall.SIGTERM)
	defer stop()

	err := run(ctx, os.Args[1:])
	if err != nil {
		fmt.Fprintln(os.Stderr, err)
		return 1
	}
	return 0
}

func run(ctx context.Context, args []string) error {
	cfg, err := config.Load(args)
	if err != nil {
		return err
	}

	if cfg.Version {
		fmt.Println(version)
		return nil
	}

		if cfg.ListTools {
			var tools []toolnames.ToolDef
			for _, def := range toolnames.Registry {
				if cfg.IsToolEnabled(def.Name) {
					tools = append(tools, def)
				}
			}
	
			// Sort by name
			sort.Slice(tools, func(i, j int) bool {
				return tools[i].Name < tools[j].Name
			})
	
			for _, tool := range tools {
				fmt.Printf("Name: %s\nTitle: %s\nDescription: %s\n\n", tool.Name, tool.Title, tool.Description)
			}
			return nil
		}
	if cfg.Agents {
		// printAgentInstructions needs to be updated or we perform a manual check here.
		// Since printAgentInstructions likely uses instructions.Get, we can refactor that.
		// For now, let's just assume we want to print instructions using the new method.
		fmt.Println(instructions.Get(cfg))
		return nil
	}
	srv := server.New(cfg, version)
	if err := srv.RegisterHandlers(); err != nil {
		return err
	}

	// Initialize with CWD as a baseline root.
	// This will be overridden if the client supports and provides workspace roots.
	graph.Global.Initialize(".")

	return srv.Run(ctx)
}
