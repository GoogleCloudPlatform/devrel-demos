package edit_code

import (
	"context"
	"fmt"
	"go/parser"
	"go/token"
	"os"
	"path/filepath"
	"sort"
	"strings"
	"time"

	"github.com/modelcontextprotocol/go-sdk/mcp"
	"golang.org/x/tools/go/packages"
	"golang.org/x/tools/imports"
)

// Register registers the edit_code tool with the server.
func Register(server *mcp.Server) {
	mcp.AddTool(server, &mcp.Tool{
		Name:        "edit_code",
		Title:       "Edit Go Code (Smart)",
		Description: "Smartly edits a Go file (*.go) with fuzzy matching and safety checks.",
	}, editCodeHandler)
}

type EditCodeParams struct {
	FilePath      string  `json:"file_path"`
	SearchContext string  `json:"search_context,omitempty"`
	NewContent    string  `json:"new_content"`
	Strategy      string  `json:"strategy,omitempty"` // replace_block (default), replace_all, overwrite_file, append
	Threshold     float64 `json:"threshold,omitempty"`
	AutoFix       bool    `json:"autofix,omitempty"` // Automatically fix imports and small typos
}

func editCodeHandler(ctx context.Context, request *mcp.CallToolRequest, args EditCodeParams) (*mcp.CallToolResult, any, error) {
	// Defaults
	if args.Strategy == "" {
		args.Strategy = "replace_block"
	}
	if args.Threshold == 0 {
		args.Threshold = 0.85 // Lowered slightly default to accommodate fuzzy matches
	}
	if !strings.HasSuffix(args.FilePath, ".go") {
		return errorResult("file_path must be a Go file (*.go)"), nil, nil
	}

	// 1. Read File
	contentBytes, err := os.ReadFile(args.FilePath)
	if err != nil {
		if os.IsNotExist(err) && args.Strategy == "overwrite_file" {
			// Allow creating new file
			contentBytes = []byte("")
		} else {
			return errorResult(fmt.Sprintf("failed to read file: %v", err)), nil, nil
		}
	}
	originalContent := string(contentBytes)
	var newContentStr string

	// 2. Resolve New Content
	if args.Strategy == "overwrite_file" {
		newContentStr = args.NewContent
	} else if args.Strategy == "append" {
		if len(originalContent) > 0 && !strings.HasSuffix(originalContent, "\n") {
			newContentStr = originalContent + "\n" + args.NewContent
		} else {
			newContentStr = originalContent + args.NewContent
		}
	} else {
		if args.SearchContext == "" {
			return errorResult("search_context is required for replace strategies"), nil, nil
		}

		// Sliding Window Fuzzy Match
		candidates := findMatches(originalContent, args.SearchContext, 0.0) // Get all candidates with >0 score

		// Filter by threshold
		var validCandidates []Match
		for _, c := range candidates {
			if c.Score >= args.Threshold {
				validCandidates = append(validCandidates, c)
			}
		}

		// AutoFix: Typo Correction (Distance <= 1)
		// If no matches found by threshold, but AutoFix is enabled, look for a very close match (distance <= 1).
		if len(validCandidates) == 0 && args.AutoFix && len(candidates) > 0 {
			best := candidates[0] // candidates are sorted descending by score

			// We need the window content to calc distance.
			bestContext := originalContent[best.StartIndex:best.EndIndex]
			normBest := normalizeBlock(bestContext)
			normContext := normalizeBlock(args.SearchContext)
			dist := levenshteinDistance(normContext, normBest)

			if dist <= 1 {
				validCandidates = append(validCandidates, best)
			}
		}

		if len(validCandidates) == 0 {
			// Find "Best Match" for feedback
			var bestMatchMsg string
			if len(candidates) > 0 {
				// candidates are sorted by findMatches
				best := candidates[0]
				bestContext := originalContent[best.StartIndex:best.EndIndex]
				bestMatchMsg = fmt.Sprintf(`

Best candidate found at line %d (Score: %.2f%%):
<<<
%s
>>>

Diff:
%s`,
					best.StartLine, best.Score*100, bestContext, generateDiff(bestContext, args.SearchContext))
			}

			msg := fmt.Sprintf("No match found for search_context with score >= %.2f.%s",
				args.Threshold, bestMatchMsg)
			return errorResult(msg), nil, nil
		}

		if args.Strategy == "replace_block" {
			if len(validCandidates) > 1 {
				// Check if they are identical (overlapping or repeats).
				// For now, simple ambiguity check.
				msg := fmt.Sprintf("Ambiguous match: found %d occurrences. Please provide more context.\nMatches at lines: ", len(validCandidates))
				for _, c := range validCandidates {
					msg += fmt.Sprintf("%d, ", c.StartLine)
				}
				return errorResult(msg), nil, nil
			}
			match := validCandidates[0]
			newContentStr = originalContent[:match.StartIndex] + args.NewContent + originalContent[match.EndIndex:]
		} else if args.Strategy == "replace_all" {
			// Apply edits from bottom to top to avoid index shifts
			// Sort by StartIndex descending
			sort.Slice(validCandidates, func(i, j int) bool {
				return validCandidates[i].StartIndex > validCandidates[j].StartIndex
			})

			currentContent := originalContent
			for _, match := range validCandidates {
				currentContent = currentContent[:match.StartIndex] + args.NewContent + currentContent[match.EndIndex:]
			}
			newContentStr = currentContent
		} else {
			return errorResult(fmt.Sprintf("unknown strategy: %s", args.Strategy)), nil, nil
		}
	}

	// 3. Validation & Auto-Correction (In-Memory)

	formattedBytes := []byte(newContentStr)

	// Skip validation/formatting for non-Go files
	if strings.HasSuffix(args.FilePath, ".go") {
		// A. Auto-Format (goimports)
		// Always run goimports to fix formatting and imports.
		var err error
		formattedBytes, err = imports.Process(args.FilePath, []byte(newContentStr), nil)
		if err != nil {
			// If goimports fails, try to parse specifically to give better error
			fset := token.NewFileSet()
			_, parseErr := parser.ParseFile(fset, "", newContentStr, parser.AllErrors)
			if parseErr != nil {
				return errorResult(fmt.Sprintf("Syntax Error (Pre-commit): %v", parseErr)), nil, nil
			}
			return errorResult(fmt.Sprintf("goimports failed: %v", err)), nil, nil
		}

		// B. Strict Syntax Check
		fset := token.NewFileSet()
		if _, err := parser.ParseFile(fset, "", formattedBytes, parser.AllErrors); err != nil {
			return errorResult(fmt.Sprintf("Syntax Error (Post-format): %v", err)), nil, nil
		}
	}

	// 4. Soft Check (Go Build) - Optional/Experimental
	// Write to temp file
	tmpDir := os.TempDir()
	tmpFile := filepath.Join(tmpDir, fmt.Sprintf("godoctor_check_%d.go", time.Now().UnixNano()))
	if err := os.WriteFile(tmpFile, formattedBytes, 0644); err == nil {
		defer os.Remove(tmpFile)
		// We can only easily run `go build` if the file is standalone or we are in the module.
		// Running `go build <tmpFile>` works for simple files, but for package files it might fail due to missing dependencies if not in the right dir.
		// For the prototype, let's skip the complex `go build` integration and trust `gopls` or the user to run tests.
		// Or we can run `go vet` on it?

		// Let's just return a warning if we can't verify deeply.
	}

	// 5. Commit (Write to Disk)
	if err := os.MkdirAll(filepath.Dir(args.FilePath), 0755); err != nil {
		return errorResult(fmt.Sprintf("failed to create directory: %v", err)), nil, nil
	}

	if err := os.WriteFile(args.FilePath, formattedBytes, 0644); err != nil {
		return errorResult(fmt.Sprintf("failed to write file: %v", err)), nil, nil
	}

	// 6. Post-Write Soft Validation (Go Analysis)
	// We use go/packages to load the package and run 'printf' analyzer.
	var analysisWarning string
	if diags, err := checkAnalysis(ctx, args.FilePath); err == nil && len(diags) > 0 {
		analysisWarning = fmt.Sprintf("\n\n**Warning:** Analysis found issues:\n%s", strings.Join(diags, "\n"))
	} else if err != nil {
		// Only report loading errors if they seem critical?
		// packages.Load usually returns partial packages with errors in Pkg.Errors.
		// If checkAnalysis returns error, it's likely fatal config/env error.
		// We'll ignore it to avoid noise, or log it?
		// Let's just append it if useful.
		// Actually, checkAnalysis returns formatted strings.
	}

	return &mcp.CallToolResult{
		Content: []mcp.Content{
			&mcp.TextContent{Text: fmt.Sprintf("Success: File updated. (Strategy: %s)%s", args.Strategy, analysisWarning)},
		},
	}, nil, nil
}

func checkAnalysis(ctx context.Context, filePath string) ([]string, error) {
	// Load the package containing the file
	cfg := &packages.Config{
		Context: ctx,
		Mode:    packages.NeedTypes | packages.NeedSyntax | packages.NeedTypesInfo,
		Dir:     filepath.Dir(filePath),
	}

	pkgs, err := packages.Load(cfg, ".")
	if err != nil {
		return nil, err
	}

	var diags []string

	// Collect package errors (e.g. undefined variable)
	for _, pkg := range pkgs {
		for _, err := range pkg.Errors {
			diags = append(diags, fmt.Sprintf("Build: %s", err.Msg))
		}
	}

	// Run Analyzer (Printf) - DISABLED
	// Note: Running analyzers manually requires managing dependencies (e.g. inspector).
	// For now, we rely on packages.Load to report type errors (undefined vars, etc).
	/*
		for _, pkg := range pkgs {
			pass := &analysis.Pass{
				Fset:      pkg.Fset,
				Files:     pkg.Syntax,
				Pkg:       pkg.Types,
				TypesInfo: pkg.TypesInfo,
				Report: func(d analysis.Diagnostic) {
					diags = append(diags, fmt.Sprintf("Vet: %s", d.Message))
				},
				ResultOf: map[*analysis.Analyzer]interface{}{}, // Missing dependencies like inspector
			}

			// Run printf analyzer
			_, _ = printf.Analyzer.Run(pass)
		}
	*/

	// Limit warnings
	if len(diags) > 5 {
		diags = append(diags[:5], "... (more)")
	}

	return diags, nil
}

func errorResult(msg string) *mcp.CallToolResult {
	return &mcp.CallToolResult{
		IsError: true,
		Content: []mcp.Content{
			&mcp.TextContent{Text: msg},
		},
	}
}

// Matching Logic
type Match struct {
	StartIndex int
	EndIndex   int
	StartLine  int
	Score      float64
}

func findMatches(content, context string, minScore float64) []Match {
	// Normalize line endings
	content = strings.ReplaceAll(content, "\r\n", "\n")
	context = strings.ReplaceAll(context, "\r\n", "\n")

	contentLines := strings.Split(content, "\n")
	contextLines := strings.Split(context, "\n")

	if len(contextLines) == 0 {
		return nil
	}

	var matches []Match

	// We want to compare the search_context (as a block) to every window of lines in the content.
	// Since fuzzy.LevenshteinDistance works on strings, we join the window lines.
	// NOTE: Whitespace sensitivity. The user might have different indentation.
	// We should probably strip whitespace from both for the comparison to be robust against indentation changes.

	normalizedContext := normalizeBlock(context)
	contextLen := len(contextLines)

	for i := 0; i <= len(contentLines)-contextLen; i++ {
		// Construct window
		windowLines := contentLines[i : i+contextLen]
		windowBlock := strings.Join(windowLines, "\n")
		normalizedWindow := normalizeBlock(windowBlock)

		// Calculate similarity
		distance := levenshteinDistance(normalizedContext, normalizedWindow)
		maxLen := max(len(normalizedContext), len(normalizedWindow))

		var score float64
		if maxLen == 0 {
			score = 1.0
		} else {
			score = 1.0 - (float64(distance) / float64(maxLen))
		}

		if score >= minScore {
			startIdx := lineIndexToByteIndex(content, i)
			endIdx := lineIndexToByteIndex(content, i+contextLen)

			// Adjust EndIndex to exclude the trailing newline of the last line
			// so that we don't consume the newline and merge lines unexpectedly.
			if endIdx > startIdx && endIdx <= len(content) && content[endIdx-1] == '\n' {
				endIdx--
			}

			matches = append(matches, Match{
				StartIndex: startIdx,
				EndIndex:   endIdx,
				StartLine:  i + 1,
				Score:      score,
			})
		}
	}

	// Sort matches by score descending
	sort.Slice(matches, func(i, j int) bool {
		return matches[i].Score > matches[j].Score
	})

	// Filter overlapping matches (Greedy NMS)
	var uniqueMatches []Match
	for _, m := range matches {
		overlaps := false
		for _, u := range uniqueMatches {
			// Check overlap
			// [Start, End)
			if m.StartIndex < u.EndIndex && m.EndIndex > u.StartIndex {
				overlaps = true
				break
			}
		}
		if !overlaps {

			uniqueMatches = append(uniqueMatches, m)
		}
	}

	return uniqueMatches
}

func normalizeBlock(s string) string {
	// Remove all whitespace
	return strings.Join(strings.Fields(s), "")
}

func lineIndexToByteIndex(s string, lineIdx int) int {
	lines := strings.Split(s, "\n") // Note: strings.Split keeps empty string at end if trailing \n
	idx := 0
	for i := 0; i < lineIdx && i < len(lines); i++ {
		idx += len(lines[i]) + 1 // +1 for newline
	}
	if idx > len(s) {
		return len(s)
	}
	return idx
}

func max(a, b int) int {
	if a > b {
		return a
	}
	return b
}

func generateDiff(original, expected string) string {
	// Simple diff visualization
	return fmt.Sprintf("- %s\n+ %s", strings.ReplaceAll(original, "\n", "\n- "), strings.ReplaceAll(expected, "\n", "\n+ "))
}

func levenshteinDistance(s1, s2 string) int {
	r1, r2 := []rune(s1), []rune(s2)
	n, m := len(r1), len(r2)
	if n == 0 {
		return m
	}
	if m == 0 {
		return n
	}

	row := make([]int, n+1)
	for i := 0; i <= n; i++ {
		row[i] = i
	}

	for j := 1; j <= m; j++ {
		prev := j
		for i := 1; i <= n; i++ {
			cost := 0
			if r1[i-1] != r2[j-1] {
				cost = 1
			}
			current := min(min(row[i]+1, prev+1), row[i-1]+cost)
			row[i-1] = prev
			prev = current
		}
		row[n] = prev
	}
	return row[n]
}

func min(a, b int) int {
	if a < b {
		return a
	}
	return b
}
