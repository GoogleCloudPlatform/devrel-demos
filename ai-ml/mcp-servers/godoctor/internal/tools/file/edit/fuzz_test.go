package edit

import (
	"testing"
)

// FuzzFindBestMatch checks for panics and basic invariants.
func FuzzFindBestMatch(f *testing.F) {
	f.Add("func main() {}", "func main")
	f.Add("some long content with newlines\nand tabs\t", "content")
	f.Add("", "")
	
f.Fuzz(func(t *testing.T, content, search string) {
		// 1. Should not panic
		start, end, score := findBestMatch(content, search)

		// 2. Invariants
		if score < 0.0 || score > 1.0 {
			t.Errorf("Score out of range: %f", score)
		}
		if start < 0 || end < 0 {
			t.Errorf("Negative bounds: %d-%d", start, end)
		}
		if start > end {
			t.Errorf("Inverted bounds: %d-%d", start, end)
		}
		// If score > 0, bounds must be within content length (in bytes? No, mapped offsets)
		// mapped offsets are byte offsets.
		if score > 0 {
			if end > len(content) {
				// Note: mapped offsets are from 'content', so they are byte indices.
				// However, if content has multi-byte chars, len(content) is byte length.
				// This check is valid.
				t.Errorf("End %d > ContentLen %d", end, len(content))
			}
		}
	})
}

// FuzzFindBestMatch_Exact checks that exact substrings are ALWAYS found.
func FuzzFindBestMatch_Exact(f *testing.F) {
	f.Add("prefix", "target", "suffix")
	
f.Fuzz(func(t *testing.T, prefix, target, suffix string) {
		// Normalize inputs to ensure we are testing the matching logic, not whitespace logic
		// (Since findBestMatch ignores whitespace, constructing inputs with whitespace might
		// cause the 'target' to be split or merged in unexpected ways in the 'content')
		
		// To keep it simple: we only assert that if we construct a string, it MUST be found.
		// But we strip whitespace from target to ensure it's a valid search.
		normTarget := normalize(target)
		if normTarget == "" {
			return 
		}
		
		content := prefix + target + suffix
		
		// If target is unique in content (simplification), score should be 1.0
		// If target appears multiple times (e.g. prefix contains target), we still expect 1.0.
		
		_, _, score := findBestMatch(content, target)
		if score < 0.99 { // Float epsilon
			// Dump info
			t.Errorf("Failed to find exact match.\nContent: %q\nSearch: %q\nScore: %f", content, target, score)
		}
	})
}
