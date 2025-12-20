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
	"strings"
	"testing"
	"time"
)

func TestRun(t *testing.T) {
	testCases := []struct {
		name        string
		args        []string
		expectError bool
		errContains string
	}{
		{
			name:        "version flag",
			args:        []string{"--version"},
			expectError: false,
		},
		{
			name:        "bad flag",
			args:        []string{"--bad-flag"},
			expectError: true,
			errContains: "flag provided but not defined: -bad-flag",
		},
	}

	for _, tc := range testCases {
		t.Run(tc.name, func(t *testing.T) {
			ctx, cancel := context.WithTimeout(context.Background(), 100*time.Millisecond)
			defer cancel()

			err := run(ctx, tc.args)

			if (err != nil) != tc.expectError {
				t.Errorf("run() error = %v, expectError %v", err, tc.expectError)
			}

			if err != nil && tc.errContains != "" {
				if !strings.Contains(err.Error(), tc.errContains) {
					t.Errorf("run() error = %q, want to contain %q", err.Error(), tc.errContains)
				}
			}
		})
	}
}