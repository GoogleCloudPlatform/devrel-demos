package edit

import (
	"testing"
)

func TestFindBestMatch(t *testing.T) {
	tests := []struct {
		name        string
		content     string
		search      string
		expectMatch bool
		minScore    float64
	}{
		{
			name:        "Exact Match",
			content:     "func main() {\n\tfmt.Println(\"Hello\")\n}",
			search:      "fmt.Println(\"Hello\")",
			expectMatch: true,
			minScore:    1.0,
		},
		{
			name:        "Whitespace Normalization (Tabs vs Spaces)",
			content:     "func main() {\tfmt.Println(\"Hello\")\n}",
			search:      "func main() { fmt.Println(\"Hello\") }",
			expectMatch: true,
			minScore:    1.0,
		},
		{
			name:        "Typo (1 char)",
			content:     "func main() {\n\tfmt.Println(\"Hello\")\n}",
			search:      "fmt.Prontln(\"Hello\")",
			expectMatch: true,
			minScore:    0.8,
		},
		{
			// Re-adding the problematic test case
			name: "Long Block with Typo (Seeding)",
			content: "func long() {\n\tline1()\n\tline2()\n\tline3()\n\tline4()\n}",
			search:      "func long() { line1() line2() line3-typo() line4() }",
			expectMatch: true,
			minScore:    0.85, 
		},
		{
			name:        "Short String (< 16 chars)",
			content:     "var x = 10",
			search:      "var x = 10",
			expectMatch: true,
			minScore:    1.0,
		},
		{
			name:        "No Match (Garbage)",
			content:     "func main() {}",
			search:      "completely different string",
			expectMatch: false,
		},
		{
			name:        "Empty File",
			content:     "",
			search:      "func main()",
			expectMatch: false,
		},
		{
			name:        "Search Larger Than File",
			content:     "short",
			search:      "longer search string",
			expectMatch: false,
		},
		{
			name:        "Unicode Support",
			content:     "func main() { fmt.Println(\"こんにちは\") }",
			search:      "fmt.Println(\"こんにちは\")",
			expectMatch: true,
			minScore:    1.0,
		},
		{
			name:        "Typos at Start",
			content:     "func main() { body }",
			search:      "fync main() { body }", // typo in first seed
			expectMatch: true,
			minScore:    0.9,
		},
		{
			name:        "Typos at End",
			content:     "func main() { body }",
			search:      "func main() { budy }", // typo in last seed
			expectMatch: true,
			minScore:    0.9,
		},
		{
			name:        "Partial Match (Substring)",
			content:     "prefix func target() {} suffix",
			search:      "func target() {}",
			expectMatch: true,
			minScore:    1.0,
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			start, end, score := findBestMatch(tt.content, tt.search)

			if !tt.expectMatch {
				if score > 0.6 {
					t.Errorf("expected no match, got score %.2f at %d-%d", score, start, end)
				}
				return
			}

			if score < tt.minScore {
				t.Errorf("score %.2f < minScore %.2f. Bounds: %d-%d", score, tt.minScore, start, end)
			}
			
			if start > end {
				t.Errorf("invalid bounds start > end: %d-%d", start, end)
			}
		})
	}
}

func TestNormalize(t *testing.T) {
	s := "  a \t b \n c "
	got := normalize(s)
	want := "abc"
	if got != want {
		t.Errorf("normalize(%q) = %q, want %q", s, got, want)
	}
}

func TestLevenshtein(t *testing.T) {
	if d := levenshtein("abc", "abd"); d != 1 {
		t.Errorf("levenshtein(abc, abd) = %d, want 1", d)
	}
	if d := levenshtein("abc", "abc"); d != 0 {
		t.Errorf("levenshtein(abc, abc) = %d, want 0", d)
	}
}