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

package inspect_test

import (
	"context"
	"os"
	"path/filepath"
	"strings"
	"testing"

	"github.com/danicat/godoctor/internal/tools/inspect"
	"github.com/modelcontextprotocol/go-sdk/mcp"
)

func TestInspectTool(t *testing.T) {
	// Create temp file
	tmpDir := t.TempDir()
	srcFile := filepath.Join(tmpDir, "main.go")
	src := `package main

import (
	"fmt"
	"net/http"
)

func main() {
	fmt.Println("Hello")
	http.Get("https://example.com")
}
`
	if err := os.WriteFile(srcFile, []byte(src), 0644); err != nil {
		t.Fatal(err)
	}

	// Setup server
	server := mcp.NewServer(&mcp.Implementation{Name: "test", Version: "1.0"}, nil)
	handler := inspect.NewToolHandler(server)

	// Call tool
	res, _, err := handler(context.Background(), nil, inspect.Params{FilePath: srcFile})
	if err != nil {
		t.Fatalf("handler failed: %v", err)
	}

	if res.IsError {
		t.Errorf("tool returned error: %v", res.Content)
	}

	if len(res.Content) == 0 {
		t.Fatal("no content returned")
	}

	textContent, ok := res.Content[0].(*mcp.TextContent)
	if !ok {
		t.Fatal("content is not text")
	}
	text := textContent.Text

	if !strings.Contains(text, "fmt.Println") {
		t.Errorf("expected fmt.Println in %s", text)
	}
	if !strings.Contains(text, "net/http.Get") {
		t.Errorf("expected net/http.Get in %s", text)
	}
}
