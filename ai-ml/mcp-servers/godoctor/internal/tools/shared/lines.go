package shared

import (
	"fmt"
	"strings"
)

// GetLineOffsets calculates the byte offsets for a given line range.
// line numbers are 1-based.
func GetLineOffsets(content string, startLine, endLine int) (int, int, error) {
	currentLine := 1
	startOffset := 0
	endOffset := len(content)

	foundStart := false

	// If startLine is not set (0), start from beginning (offset 0)
	if startLine <= 1 {
		startOffset = 0
		foundStart = true
	}

	for i, char := range content {
		if char == '\n' {
			currentLine++
			if !foundStart && currentLine == startLine {
				startOffset = i + 1 // Start after the newline
				foundStart = true
			}
			if endLine > 0 && currentLine > endLine {
				endOffset = i + 1 // Include the newline of the last line
				break
			}
		}
	}

	if startLine > currentLine && startLine > 1 {
		return 0, 0, fmt.Errorf("start_line %d is beyond file length (%d lines)", startLine, currentLine)
	}

	return startOffset, endOffset, nil
}

// GetSnippet returns a context window around the specified line number.
func GetSnippet(content string, lineNum int) string {
	lines := strings.Split(content, "\n")
	if lineNum < 1 || lineNum > len(lines) {
		return ""
	}

	start := lineNum - 5
	if start < 1 {
		start = 1
	}
	end := lineNum + 5
	if end > len(lines) {
		end = len(lines)
	}

	var sb strings.Builder
	for i := start; i <= end; i++ {
		prefix := "  "
		if i == lineNum {
			prefix = "-> "
		}
		sb.WriteString(fmt.Sprintf("%s%d | %s\n", prefix, i, lines[i-1]))
	}
	return sb.String()
}

// ExtractErrorSnippet attempts to parse a line number from an error message
// and returns a snippet of the content around that line.
func ExtractErrorSnippet(content string, err error) string {
	// Parse error string "filename:line:col: message" or ":line:col: message"
	errMsg := err.Error()
	parts := strings.Split(errMsg, ":")

	var lineNum int
	for _, part := range parts {
		var n int
		// Try to parse the first number we find in the error parts
		if _, e := fmt.Sscanf(strings.TrimSpace(part), "%d", &n); e == nil {
			lineNum = n
			break
		}
	}

	if lineNum == 0 {
		return "Could not determine error line."
	}

	return GetSnippet(content, lineNum)
}

// GetLineFromOffset calculates the 1-based line number for a given byte offset.
func GetLineFromOffset(content string, offset int) int {
	if offset < 0 || offset > len(content) {
		return 0
	}
	return strings.Count(content[:offset], "\n") + 1
}
