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

package godoc

import (
	"context"
	"strings"
	"testing"

	"github.com/modelcontextprotocol/go-sdk/mcp"
)

func TestResourceHandler(t *testing.T) {
	ctx := context.Background()

	testCases := []struct {
		name        string
		uri         string
		wantErr     bool
		wantContent string
	}{
		{
			name:        "Valid Package",
			uri:         "godoc://fmt",
			wantErr:     false,
			wantContent: "# fmt",
		},
		{
			name:        "Valid Symbol (Split Path)",
			uri:         "godoc://fmt/Println",
			wantErr:     false,
			wantContent: "func Println",
		},
		{
			name:        "Invalid Scheme",
			uri:         "http://google.com",
			wantErr:     true,
			wantContent: "invalid URI scheme",
		},
		{
			name:        "Missing Package",
			uri:         "godoc://non/existent",
			wantErr:     true,
			wantContent: "Resource not found",
			// Handled by standard MCP error usually, but our handler returns specific error or nil
		},
	}

	for _, tc := range testCases {
		t.Run(tc.name, func(t *testing.T) {
			req := &mcp.ReadResourceRequest{
				Params: &mcp.ReadResourceParams{
					URI: tc.uri,
				},
			}
			result, err := ResourceHandler(ctx, req)
			
			if tc.wantErr {
				if err == nil {
					t.Error("Expected error, got nil")
				}
			} else {
				if err != nil {
					t.Errorf("Unexpected error: %v", err)
				}
				if len(result.Contents) == 0 {
					t.Error("Expected content, got empty")
				}
				if !strings.Contains(result.Contents[0].Text, tc.wantContent) {
					t.Errorf("Expected content to contain %q, got %q", tc.wantContent, result.Contents[0].Text)
				}
			}
		})
	}
}
