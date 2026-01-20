// Package edit implements the file editing tool.
package edit

import (
	"context"
	"fmt"
	"os"
	"path/filepath"
	"strings"

	"github.com/danicat/godoctor/internal/graph"
	"github.com/danicat/godoctor/internal/roots"
	"github.com/danicat/godoctor/internal/toolnames"
	"github.com/danicat/godoctor/internal/tools/shared"
	"github.com/modelcontextprotocol/go-sdk/mcp"
	"golang.org/x/tools/imports"
)

// Register registers the smart_edit tool with the server.
func Register(server *mcp.Server) {
	def := toolnames.Registry["file_edit"]
	mcp.AddTool(server, &mcp.Tool{
		Name:        def.Name,
		Title:       def.Title,
		Description: def.Description,
	}, toolHandler)
}

// Params defines the input parameters for the smart_edit tool.
type Params struct {
	Filename      string  `json:"filename" jsonschema:"The path to the file to edit"`
	SearchContext string  `json:"search_context" jsonschema:"The block of code to find (ignores whitespace)"`
	Replacement   string  `json:"replacement" jsonschema:"The new code to insert"`
	Threshold     float64 `json:"threshold,omitempty" jsonschema:"Similarity threshold (0.0-1.0) for fuzzy matching, default 0.95"`
	StartLine     int     `json:"start_line,omitempty" jsonschema:"Optional: restrict search to this line number and after"`
	EndLine       int     `json:"end_line,omitempty" jsonschema:"Optional: restrict search to this line number and before"`
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

	if args.SearchContext == "" {
		// APPEND MODE
		// Check if file ends with newline
		if len(original) > 0 && !strings.HasSuffix(original, "\n") {
			newContent = original + "\n" + args.Replacement
		} else {
			newContent = original + args.Replacement
		}
	} else {
		// EDIT MODE (Fuzzy Match)
		// Restrict search to the specified window
		searchArea := original[searchStart:searchEnd]
		matchStart, matchEnd, score := findBestMatch(searchArea, args.SearchContext)

		if score < args.Threshold {
			bestMatch := ""
			if matchStart < matchEnd && matchEnd <= len(searchArea) {
				bestMatch = searchArea[matchStart:matchEnd]
			}
			return errorResult(fmt.Sprintf("match not found with sufficient confidence (score: %.2f < %.2f).\n\nBest Match Found:\n```go\n%s\n```\n\nSuggestions: verify your search_context or lower threshold.", score, args.Threshold, bestMatch)), nil, nil
		}

		// Adjust local offsets to global offsets
		matchStart += searchStart
		matchEnd += searchStart

		newContent = original[:matchStart] + args.Replacement + original[matchEnd:]
	}

	// 4. Auto-Format & Import check (GO ONLY)
	var formatted []byte
	isGo := strings.HasSuffix(args.Filename, ".go")

	if isGo {
		// Use imports.Process which runs gofmt and goimports
		formatted, err = imports.Process(args.Filename, []byte(newContent), nil)
		if err != nil {
			// Try to give a helpful error location
			return errorResult(fmt.Sprintf("edit produced invalid Go code: %v\nHint: Ensure your Replacement is syntactically valid in context.", err)), nil, nil
		}
	} else {
		formatted = []byte(newContent)
	}

	// 5. Write to disk
	//nolint:gosec // G306: Standard permissions for source files.
	if err := os.WriteFile(args.Filename, formatted, 0644); err != nil {
		return errorResult(fmt.Sprintf("failed to write file: %v", err)), nil, nil
	}

	// 6. Post-Check Verification (Type Check) (GO ONLY)
	var warning string

	if isGo {
		// We want to verify that the file compiles within its package
		pkg, err := graph.Global.Load(args.Filename)

		if err != nil {
			// Graph loading failed, maybe severe syntax error skipped by imports.Process?
			warning = fmt.Sprintf("\n\n**WARNING:** Failed to reload package context: %v", err)
		} else if len(pkg.Errors) > 0 {
			warning = "\n\n**WARNING:** Edit successful but introduced compilation errors:\n"
			for _, e := range pkg.Errors {
				loc := ""
				if e.Pos != "" {
					loc = e.Pos + ": "
				}
				warning += fmt.Sprintf("- %s%s\n", loc, shared.CleanError(e.Msg))
			}
			                        warning += shared.GetDocHint(pkg.Errors)
			                } else {
			                        // 7. Impact Analysis (Reverse Dependencies)
			                        // Only run if local compilation passed
			                        // We limit this to avoiding massive scans in large repos, relying on the graph.
			                        importers := graph.Global.FindImporters(pkg.PkgPath)
			                        var impactWarnings []string
			
			                        for _, imp := range importers {
			                                if len(imp.GoFiles) == 0 {
			                                        continue
			                                }
			                                impDir := filepath.Dir(imp.GoFiles[0])
			
			                                // Force reload to check against new API
			                                graph.Global.Invalidate(impDir)
			
			                                // Check for errors
			                                reloadedImp, err := graph.Global.Load(impDir)
			                                if err == nil && len(reloadedImp.Errors) > 0 {
			                                        impactWarnings = append(impactWarnings, fmt.Sprintf("Package %s: %s", reloadedImp.PkgPath, reloadedImp.Errors[0].Msg))
			                                }
			                        }
			
			                        if len(impactWarnings) > 0 {
			                                warning += "\n\n**IMPACT WARNING:** This edit broke the following dependent packages:\n"
			                                for _, w := range impactWarnings {
			                                        warning += fmt.Sprintf("- %s\n", w)
			                                }
			                                // Also check impact warnings for MCP hints if possible
			                                // (impactWarnings are strings, so we use the output helper)
			                                warning += shared.GetDocHintFromOutput(strings.Join(impactWarnings, "\n"))
			                        }
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
func findBestMatch(content, search string) (int, int, float64) {
	// 1. Pre-process search string: remove all whitespace
	normSearch := normalize(search)
	if normSearch == "" {
		return 0, 0, 0
	}

	// 2. Pre-process content: remove all whitespace and track original offsets
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

	// 3. Extract just the characters for searching
	normContentRunes := make([]rune, len(mapped))
	for i, cm := range mapped {
		normContentRunes[i] = cm.char
	}
	normContent := string(normContentRunes)

	// 4. Sliding window search on the normalized content
	searchLen := len([]rune(normSearch))
	contentLen := len(normContentRunes)

	if searchLen > contentLen {
		// If search is longer than content, it definitely won't match perfectly,
		// but let's at least return a score based on the whole file.
		return 0, len(content), similarity(normSearch, normContent)
	}

	bestScore := 0.0
	bestStartIdx := 0
	bestEndIdx := 0

	// We use a small buffer around the search length to account for slight mismatches
	// but a substring search is the primary goal.
	// Optimization: check for exact substring match first
	exactIdx := strings.Index(normContent, normSearch)
	if exactIdx != -1 {
		start := mapped[exactIdx].offset
		endIdx := exactIdx + searchLen - 1
		end := mapped[endIdx].offset + 1 // +1 to include the character itself

		// For Go, we want to include the rest of the line if it was just whitespace
		// and we should check if we ended in the middle of a multi-byte char
		// but mapped[].offset is already the byte index.
		return start, end, 1.0
	}

	// Fuzzy matching with sliding window
	// Check windows of varying lengths to account for insertions/deletions
	// We check searchLen +/- 10%
	delta := searchLen / 10
	if delta < 2 {
		delta = 2
	}

	for i := 0; i <= contentLen-searchLen; i++ {
		// Optimization: heuristic filter? (e.g. first char match)
		// normalized content first char check is cheap
		if normContent[i] != normSearch[0] {
			// Optimization: Skip if start char doesn't match?
			// Levenshtein handles substitution of first char, so skipping might miss that.
			// But for code matching, usually start aligns.
			// Let's keep it safe and NOT skip yet.
		}

		for l := searchLen - delta; l <= searchLen+delta; l++ {
			if l <= 0 {
				continue
			}
			if i+l > contentLen {
				break
			}
			window := normContent[i : i+l]
			score := similarity(normSearch, window)

			if score > bestScore {
				bestScore = score
				bestStartIdx = i
				bestEndIdx = i + l - 1
			}

			if bestScore == 1.0 {
				goto Found
			}
		}
	}
Found:

	if bestScore > 0 {
		start := mapped[bestStartIdx].offset
		end := mapped[bestEndIdx].offset + 1
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
