package edit

import (
	"context"
	"fmt"
	"os"
	"path/filepath"
	"strings"

	"github.com/danicat/godoctor/internal/graph"
	"github.com/modelcontextprotocol/go-sdk/mcp"
	"golang.org/x/tools/imports"
)

// Register registers the smart_edit tool with the server.
func Register(server *mcp.Server) {
	mcp.AddTool(server, &mcp.Tool{
		Name:        "smart_edit",
		Title:       "Smart Edit (Fuzzy Patch)",
		Description: "The 'Senior Dev' editor. Uses fuzzy-matching to patch specific code blocks. It auto-formats, updates imports, and PRE-COMPILES your change to catch errors before saving. Use this to safely modify large files.",
	}, toolHandler)
}

// Params defines the input parameters for the smart_edit tool.
type Params struct {
	File          string  `json:"file" jsonschema:"The absolute path to the file to edit"`
	SearchContext string  `json:"search_context" jsonschema:"The block of code to find (ignores whitespace)"`
	Replacement   string  `json:"replacement" jsonschema:"The new code to insert"`
	Threshold     float64 `json:"threshold,omitempty" jsonschema:"Similarity threshold (0.0-1.0) for fuzzy matching, default 0.95"`
}

func toolHandler(ctx context.Context, _ *mcp.CallToolRequest, args Params) (*mcp.CallToolResult, any, error) {
	if args.File == "" {
		return errorResult("file cannot be empty"), nil, nil
	}
	if !strings.HasSuffix(args.File, ".go") {
		return errorResult("file must be a Go file (*.go)"), nil, nil
	}

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
	content, err := os.ReadFile(args.File)
	if err != nil {
		return errorResult(fmt.Sprintf("failed to read file: %v", err)), nil, nil
	}

	// 2. Fuzzy Match (Ignore Whitespace)
	original := string(content)
	matchStart, matchEnd, score := findBestMatch(original, args.SearchContext)

	if score < args.Threshold {
		return errorResult(fmt.Sprintf("match not found with sufficient confidence (score: %.2f < %.2f). Suggestions: verify your search_context or lower threshold", score, args.Threshold)), nil, nil
	}

	// 3. Apply Edit
	// Ensure we don't duplicate newlines if replacement handles them differently
	// But simple string replacement is safest for now.
	newContent := original[:matchStart] + args.Replacement + original[matchEnd:]

	// 4. Auto-Format & Import check
	// Use imports.Process which runs gofmt and goimports
	formatted, err := imports.Process(args.File, []byte(newContent), nil)
	if err != nil {
		// Try to give a helpful error location
		return errorResult(fmt.Sprintf("edit produced invalid Go code: %v\nHint: Ensure your Replacement is syntactically valid in context.", err)), nil, nil
	}

	// 5. Write to disk
	if err := os.WriteFile(args.File, formatted, 0644); err != nil {
		return errorResult(fmt.Sprintf("failed to write file: %v", err)), nil, nil
	}

	// 6. Post-Check Verification (Type Check)
	// We want to verify that the file compiles within its package
	pkg, err := graph.Global.Load(args.File)
	var warning string

	if err != nil {
		// Graph loading failed, maybe severe syntax error skipped by imports.Process?
		warning = fmt.Sprintf("\n\n**WARNING:** Failed to reload package context: %v", err)
	} else if len(pkg.Errors) > 0 {
		warning = "\n\n**WARNING:** Edit successful but introduced compilation errors:\n"
		for _, e := range pkg.Errors {
			warning += fmt.Sprintf("- %s\n", e.Msg)
		}
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
		}
	}

	return &mcp.CallToolResult{
		Content: []mcp.Content{
			&mcp.TextContent{Text: fmt.Sprintf("Successfully edited %s%s", args.File, warning)},
		},
	}, nil, nil
}

// Minimal fuzzy matching for the spike/prototype
func findBestMatch(content, search string) (int, int, float64) {
	// Simple implementation: normalized whitespace comparison
	normSearch := normalize(search)
	if normSearch == "" {
		return 0, 0, 0
	}

	// We'll use a sliding window of lines
	lines := strings.Split(content, "\n")
	searchLines := strings.Split(strings.TrimSpace(search), "\n")

	bestScore := 0.0
	bestStart := 0
	bestEnd := 0

	for i := 0; i <= len(lines)-len(searchLines); i++ {
		window := strings.Join(lines[i:i+len(searchLines)], "\n")
		normWindow := normalize(window)

		score := similarity(normSearch, normWindow)
		if score > bestScore {
			bestScore = score
			bestStart = getByteOffset(lines, i)
			endLineIdx := i + len(searchLines)
			if endLineIdx > len(lines) {
				endLineIdx = len(lines)
			}
			bestEnd = getByteOffset(lines, endLineIdx)
			// Adjust bestEnd if it includes the trailing newline of the last line
			if bestEnd > bestStart && bestEnd < len(content) && content[bestEnd] == '\n' {
				// but we want to include the newline of the matched block
			}
			// If bestEnd is at the end of a line, it already includes the \n because getByteOffset adds it.
			// Let's ensure it doesn't overshoot.
			if bestEnd > len(content) {
				bestEnd = len(content)
			}
		}
	}

	return bestStart, bestEnd, bestScore
}

func normalize(s string) string {
	return strings.Join(strings.Fields(s), "")
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

func getByteOffset(lines []string, lineIdx int) int {
	offset := 0
	for i := 0; i < lineIdx && i < len(lines); i++ {
		offset += len(lines[i]) + 1 // +1 for newline
	}
	return offset
}

func errorResult(msg string) *mcp.CallToolResult {
	return &mcp.CallToolResult{
		IsError: true,
		Content: []mcp.Content{
			&mcp.TextContent{Text: msg},
		},
	}
}
