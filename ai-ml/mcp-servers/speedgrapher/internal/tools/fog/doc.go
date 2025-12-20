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

/*
Package fog provides a tool for calculating the Gunning Fog Index of a given text.
The Gunning Fog Index is a readability test that estimates the years of formal
education a person needs to understand a text on the first reading.

This implementation provides not only the numerical Fog Index but also a
qualitative classification to help writers calibrate their text for a specific
audience.

# Implementation and Design

The development of this tool was an iterative process, with several key design
decisions made along the way:

## Syllable Counting

The core of the Fog Index is the identification of "complex words," which are
defined as words with three or more syllables. The syllable counting algorithm
went through several iterations:

1.  **Initial Approach:** A rule-based system that attempted to handle common
    suffixes (e.g., -es, -ed, -ing) and silent 'e' endings. This proved to be
    brittle and difficult to maintain.

2.  **Simplified Approach:** A version that simply counted vowel groups, where a
    vowel group is any sequence of one or more consecutive vowels. This was more
    robust and predictable, but it tended to overestimate the complexity of some
    common words.

3.  **Final Approach:** The current implementation uses the simplified vowel
    group counting method. This was chosen because it provides a consistent and
    reproducible heuristic, even if it is not perfectly aligned with linguistic
    syllabification. The goal is to provide a consistent measure, and this
    approach achieves that.

## Classification Ranges

The classification of the Fog Index into descriptive categories was also a
key focus. The goal was to provide labels that were more prescriptive and
user-friendly than the traditional grade-level system. The final categories
are:

*   **Unreadable:** (Score >= 22)
*   **Hard to Read:** (Score 18-21)
*   **Professional Audiences:** (Score 13-17)
*   **General Audiences:** (Score 9-12)
*   **Simplistic:** (Score < 9)

These ranges were chosen based on research into the readability of popular
and professional publications, with the 9-12 range identified as the ideal
target for most general-purpose writing.

# Usage

The `fog` tool can be used programmatically by calling the `CalculateFogIndex`
and `ClassifyFogIndex` functions.

Example:

	text := "This is a sample sentence to be analyzed."
	fogIndex := fog.CalculateFogIndex(text)
	classification := fog.ClassifyFogIndex(fogIndex)
	fmt.Printf("Fog Index: %.2f\n", fogIndex)
	fmt.Printf("Classification: %s\n", classification)

# External References

*   **Gunning Fog Index (Wikipedia):**
    https://en.wikipedia.org/wiki/Gunning_fog_index

*   **How to Build an MCP Server with Gemini CLI and Go:**
    https://danicat.dev/posts/20250729-how-to-build-an-mcp-server-with-gemini-cli-and-go/
*/
package fog
