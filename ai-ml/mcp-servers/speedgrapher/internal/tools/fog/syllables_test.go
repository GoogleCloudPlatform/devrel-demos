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

package fog

import (
	"testing"
)

func TestCountSyllables(t *testing.T) {
	testCases := []struct {
		word     string
		expected int
	}{
		{"complex", 2},
		{"sentence", 3},
		{"difficult", 3},
		{"dog", 1},
		{"cat", 1},
		{"created", 2},
		{"beautiful", 3},
		{"requires", 3},
		{"understanding", 4},
	}

	for _, tc := range testCases {
		t.Run(tc.word, func(t *testing.T) {
			if got := countSyllables(tc.word); got != tc.expected {
				t.Errorf("for word '%s', expected %d syllables but got %d", tc.word, tc.expected, got)
			}
		})
	}
}
