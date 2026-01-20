package shared

import "fmt"

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
