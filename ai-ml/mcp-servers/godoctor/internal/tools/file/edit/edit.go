// Package edit implements the file editing tool.
package edit

import (
	"context"
	"fmt"
	"go/parser"
	"go/token"
	"os"
	"strings"

	"github.com/danicat/godoctor/internal/roots"
	"github.com/danicat/godoctor/internal/toolnames"
	"github.com/danicat/godoctor/internal/tools/shared"
	"github.com/modelcontextprotocol/go-sdk/mcp"
	"golang.org/x/tools/imports"
)

// Register registers the smart_edit tool with the server.
func Register(server *mcp.Server) {
	def := toolnames.Registry["smart_edit"]
	mcp.AddTool(server, &mcp.Tool{
		Name:        def.Name,
		Title:       def.Title,
		Description: def.Description,
	}, toolHandler)
}

// Params defines the input parameters for the smart_edit tool.
type Params struct {
	Filename   string  `json:"filename" jsonschema:"The path to the file to edit"`
	OldContent string  `json:"old_content,omitempty" jsonschema:"Optional: The block of code to find (ignores whitespace). Required if append is false."`
	NewContent string  `json:"new_content" jsonschema:"The new code to insert"`
	Threshold  float64 `json:"threshold,omitempty" jsonschema:"Similarity threshold (0.0-1.0) for fuzzy matching, default 0.95"`

	StartLine int  `json:"start_line,omitempty" jsonschema:"Optional: restrict search to this line number and after"`
	EndLine   int  `json:"end_line,omitempty" jsonschema:"Optional: restrict search to this line number and before"`
	Append    bool `json:"append,omitempty" jsonschema:"If true, append new_content to the end of the file (ignores old_content)"`
}

func toolHandler(ctx context.Context, _ *mcp.CallToolRequest, args Params) (*mcp.CallToolResult, any, error) {
	absPath, err := roots.Global.Validate(args.Filename)

	if err != nil {
		return errorResult(err.Error()), nil, nil
	}
	args.Filename = absPath

	// Default threshold
	if args.Threshold == 0 {
		args.Threshold = 0.95
	}
	// Cap threshold
	if args.Threshold > 1.0 {
		args.Threshold = 1.0
	}
	if args.Threshold < 0.0 {
		args.Threshold = 0.0
	}

	// 1. Read File
	content, err := os.ReadFile(args.Filename)
	if err != nil {
		return errorResult(fmt.Sprintf("failed to read file: %v", err)), nil, nil
	}

	// 2. Logic: Append OR Edit
	var newContent string
	original := string(content)

	// Determine Search Bounds
	searchStart := 0
	searchEnd := len(original)
	if args.StartLine > 0 || args.EndLine > 0 {
		s, e, err := shared.GetLineOffsets(original, args.StartLine, args.EndLine)
		if err != nil {
			return errorResult(fmt.Sprintf("line range error: %v", err)), nil, nil
		}
		searchStart = s
		searchEnd = e
	}

	if args.Append || args.OldContent == "" {
		// APPEND MODE
		// Check if file ends with newline
		if len(original) > 0 && !strings.HasSuffix(original, "\n") {
			newContent = original + "\n" + args.NewContent
		} else {
			newContent = original + args.NewContent
		}
	} else {
		// EDIT MODE (Fuzzy Match)
		// Restrict search to the specified window
		searchArea := original[searchStart:searchEnd]
		matchStart, matchEnd, score := findBestMatch(searchArea, args.OldContent)

		if score < args.Threshold {
			bestMatch := ""
			if matchStart < matchEnd && matchEnd <= len(searchArea) {
				bestMatch = searchArea[matchStart:matchEnd]
			}

			// Get line numbers for the best match attempt (relative to the search area if using offsets,
			// but bestMatch logic operates on searchArea).
			// We need to map matchStart/matchEnd back to original file line numbers.
			// matchStart is byte offset in searchArea.
			// Global offset = searchStart + matchStart

			globalMatchStart := searchStart + matchStart
			globalMatchEnd := searchStart + matchEnd

			bestStartLine := shared.GetLineFromOffset(original, globalMatchStart)
			bestEndLine := shared.GetLineFromOffset(original, globalMatchEnd)

			return errorResult(fmt.Sprintf("match not found with sufficient confidence (score: %.2f < %.2f).\n\nBest Match Found (Lines %d-%d):\n```go\n%s\n```\n\nSuggestions: verify your old_content or lower threshold.", score, args.Threshold, bestStartLine, bestEndLine, bestMatch)), nil, nil
		}

		// Adjust local offsets to global offsets
		matchStart += searchStart
		matchEnd += searchStart

		newContent = original[:matchStart] + args.NewContent + original[matchEnd:]
	}

	// 4. Auto-Format & Import check (GO ONLY)
	var formatted []byte
	isGo := strings.HasSuffix(args.Filename, ".go")

	if isGo {
		// Use imports.Process which runs gofmt and goimports
		formatted, err = imports.Process(args.Filename, []byte(newContent), nil)
		if err != nil {
			// Try to give a helpful error location
			snippet := shared.ExtractErrorSnippet(newContent, err)
			return errorResult(fmt.Sprintf("edit produced invalid Go code: %v\n\nContext:\n```go\n%s\n```\nHint: Ensure your NewContent is syntactically valid in context.", err, snippet)), nil, nil
		}
	} else {
		formatted = []byte(newContent)
	}

	// 5. Write to disk
	//nolint:gosec // G306: Standard permissions for source files.
	if err := os.WriteFile(args.Filename, formatted, 0644); err != nil {
		return errorResult(fmt.Sprintf("failed to write file: %v", err)), nil, nil
	}

	// 6. Post-Check Verification (Syntax Check) (GO ONLY)
	var warning string

	if isGo {
		// We perform a final syntax check to ensure imports.Process didn't leave weirdness
		fset := token.NewFileSet()
		_, err := parser.ParseFile(fset, args.Filename, nil, parser.ParseComments)
		if err != nil {
			warning = fmt.Sprintf("\n\n**WARNING:** Post-edit syntax check failed: %v", err)
		}
	}
	return &mcp.CallToolResult{
		Content: []mcp.Content{
			&mcp.TextContent{Text: fmt.Sprintf("Successfully edited %s%s", args.Filename, warning)},
		},
	}, nil, nil
}

// findBestMatch locates the best match for 'search' within 'content' ignoring whitespace and newlines.
// It returns the start and end byte offsets in the original content and a similarity score (0-1).
// Implementation: Seeded Fuzzy Match (V2). significantly faster than sliding window.
func findBestMatch(content, search string) (int, int, float64) {
	normSearch := normalize(search)
	if normSearch == "" {
		return 0, 0, 0
	}

	// 1. Build File Map (Dense -> Original Offset)
	type charMap struct {
		char   rune
		offset int
	}
	var mapped []charMap
	for offset, char := range content {
		if !isWhitespace(char) {
			mapped = append(mapped, charMap{char, offset})
		}
	}
	normContentRunes := make([]rune, len(mapped))
	for i, cm := range mapped {
		normContentRunes[i] = cm.char
	}
	normContent := string(normContentRunes)

	// 2. Exact Match Check (Optimization)
	if idx := strings.Index(normContent, normSearch); idx != -1 {
		// strings.Index returns byte offset. We need rune index for 'mapped'.
		// Count runes before the match to get the index into 'mapped'.
		runeIdx := len([]rune(normContent[:idx]))

		start := mapped[runeIdx].offset
		end := mapped[runeIdx+len([]rune(normSearch))-1].offset + 1
		return start, end, 1.0
	}

	// 3. Seeding Strategy
	searchRunes := []rune(normSearch)
	searchLen := len(searchRunes)
	contentLen := len(normContentRunes)

	if searchLen > contentLen {
		score := similarity(normSearch, normContent)
		return 0, len(content), score
	}

	// Config
	seedLen := 16
	step := 8

	// Use smaller seeds for smaller strings to ensure we can find matches around typos
	if searchLen < 64 {
		seedLen = 8
		step = 4
	}

	// Fallback to simple scan for very short strings if seeds would be ineffective
	if searchLen < seedLen {
		seedLen = 4
		step = 2
	}

	// Candidates map: projected_start_index -> votes
	candidates := make(map[int]int)

	// Helper to check a seed at specific offset
	checkSeed := func(offset int) {
		seed := string(searchRunes[offset : offset+seedLen])
		startSearch := 0
		for {
			idx := strings.Index(normContent[startSearch:], seed)
			if idx == -1 {
				break
			}
			realIdx := startSearch + idx
			projectedStart := realIdx - offset
			if projectedStart >= 0 && projectedStart <= len(normContentRunes)-searchLen {
				candidates[projectedStart]++
			}
			startSearch = realIdx + 1
		}
	}

	// Scan with stride
	for i := 0; i <= searchLen-seedLen; i += step {
		// fmt.Printf("Checking seed i=%d: '%s'\n", i, string(searchRunes[i:i+seedLen]))
		checkSeed(i)
	}

	// Ensure we check the tail (critical for short strings with typo at start)
	if searchLen >= seedLen {
		tailOffset := searchLen - seedLen
		// Avoid double checking if tail aligns with step
		if tailOffset%step != 0 {
			// fmt.Printf("Checking tail seed i=%d: '%s'\n", tailOffset, string(searchRunes[tailOffset:tailOffset+seedLen]))
			checkSeed(tailOffset)
		}
	}

	// 4. Verification
	bestScore := 0.0
	bestStartIdx := 0
	bestEndIdx := 0

	// If no candidates found (massive typo or very short string?), fallback to sliding window?
	// But V1 fallback is O(N*M). Let's stick to candidates for now.
	// If candidates is empty, we return 0 match.

	for startIdx := range candidates {
		// Define window
		endIdx := startIdx + searchLen
		if endIdx > len(normContentRunes) {
			endIdx = len(normContentRunes)
		}

		window := string(normContentRunes[startIdx:endIdx])
		score := similarity(normSearch, window)

		if score > bestScore {
			bestScore = score
			bestStartIdx = startIdx
			bestEndIdx = endIdx
		}
	}

	if bestScore > 0 {
		start := mapped[bestStartIdx].offset
		end := mapped[bestEndIdx-1].offset + 1
		return start, end, bestScore
	}

	return 0, 0, 0
}

func isWhitespace(r rune) bool {
	switch r {
	case ' ', '\t', '\n', '\r':
		return true
	}
	return false
}

func normalize(s string) string {
	var sb strings.Builder
	for _, r := range s {
		if !isWhitespace(r) {
			sb.WriteRune(r)
		}
	}
	return sb.String()
}

func similarity(s1, s2 string) float64 {
	if s1 == s2 {
		return 1.0
	}
	d := levenshtein(s1, s2)
	maxLen := len(s1)
	if len(s2) > maxLen {
		maxLen = len(s2)
	}
	if maxLen == 0 {
		return 1.0
	}
	return 1.0 - float64(d)/float64(maxLen)
}

func levenshtein(s1, s2 string) int {
	r1, r2 := []rune(s1), []rune(s2)
	n, m := len(r1), len(r2)
	if n > m {
		r1, r2 = r2, r1
		n, m = m, n
	}
	currentRow := make([]int, n+1)
	for i := 0; i <= n; i++ {
		currentRow[i] = i
	}
	for i := 1; i <= m; i++ {
		previousRow := currentRow
		currentRow = make([]int, n+1)
		currentRow[0] = i
		for j := 1; j <= n; j++ {
			add, del, change := previousRow[j]+1, currentRow[j-1]+1, previousRow[j-1]
			if r1[j-1] != r2[i-1] {
				change++
			}
			min := add
			if del < min {
				min = del
			}
			if change < min {
				min = change
			}
			currentRow[j] = min
		}
	}
	return currentRow[n]
}

func errorResult(msg string) *mcp.CallToolResult {
	return &mcp.CallToolResult{
		IsError: true,
		Content: []mcp.Content{
			&mcp.TextContent{Text: msg},
		},
	}
}
