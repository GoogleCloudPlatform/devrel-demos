package report

import (
	"fmt"
	"io/ioutil"
	"regexp"
	"strings"
)

// FixMarkdownReport reorders sections and fixes formatting in an existing Markdown report
func FixMarkdownReport(path string) error {
	content, err := ioutil.ReadFile(path)
	if err != nil {
		return fmt.Errorf("failed to read report file: %w", err)
	}

	reportStr := string(content)

	// Define sections to look for
	sections := map[string]string{}
	headers := []string{
		"Executive Summary",
		"Experiment Parameters",
		"Notes",
		"Performance Comparison",
		"Summary by Scenario & Alternative",
		"Detailed Metrics",
		"Tool Usage Analysis",
		"Failure Analysis",
		"Conclusion",
	}

	// Pre-fix specific corruption caused by previous run
	reportStr = strings.ReplaceAll(reportStr, "Performance Comparison|", "Performance Comparison\n|")

	// Remove the specific note if present, replacing with newline to preserve formatting
	reportStr = strings.ReplaceAll(reportStr, "\n> Note: Duration and Token averages are calculated based on **successful runs only**.\n", "\n")

	// Split by H2 headers (## )
	// Uses a simple split approach assuming standard Tenkai format
	parts := strings.Split(reportStr, "\n## ")

	header := parts[0] // The H1 title and timestamp

	for _, p := range parts[1:] {
		// Re-add the ## prefix that was removed by split
		fullSection := "\n## " + p

		titleEnd := strings.Index(p, "\n")
		if titleEnd == -1 {
			continue
		}
		title := strings.TrimSpace(p[:titleEnd])
		// Remove emojis for matching
		cleanTitle := cleanTitle(title)

		sections[cleanTitle] = fullSection
	}

	var newContent strings.Builder
	newContent.WriteString(header)

	for _, h := range headers {
		if content, ok := sections[h]; ok {
			// Apply text fixes
			if h == "Performance Comparison" {
				content = strings.ReplaceAll(content, " <br> ", " ")
			}
			newContent.WriteString(content)
		} else {
			// If a section is missing from the file but expected (maybe loop warnings/notes),
			// check if we stored it under a slightly different name or just skip.
			// Since we map strictly, we skip.
		}
	}

	if err := ioutil.WriteFile(path, []byte(newContent.String()), 0644); err != nil {
		return fmt.Errorf("failed to write fixed report: %w", err)
	}

	return nil
}

func cleanTitle(t string) string {
	// Simple regex to remove emojis and formatting
	// Keep alphanumeric and spaces
	re := regexp.MustCompile(`[^\w\s&]`)
	cleaned := re.ReplaceAllString(t, "")
	return strings.TrimSpace(cleaned)
}
