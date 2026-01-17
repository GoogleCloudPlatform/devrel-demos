package report

import (
	"encoding/json"
	"fmt"
	"io"
	"path/filepath"
	"sort"
	"strings"
	"time"

	"github.com/GoogleCloudPlatform/devrel-demos/agents/tenkai/internal/config"
	"github.com/GoogleCloudPlatform/devrel-demos/agents/tenkai/internal/db"
	"github.com/GoogleCloudPlatform/devrel-demos/agents/tenkai/internal/db/models"
	"github.com/GoogleCloudPlatform/devrel-demos/agents/tenkai/internal/runner"
)

// EnhancedReporter extends Reporter with better formatting
type EnhancedMarkdownGenerator struct {
	Results    []runner.Result
	Cfg        *config.Configuration
	Notes      []string
	w          io.Writer
	summary    *runner.ExperimentSummary
	ToolCounts map[int64]map[string]int
}

func (r *EnhancedMarkdownGenerator) Generate() error {
	// Filter to include only completed runs for the report
	terminalResults := []runner.Result{}
	for _, res := range r.Results {
		st := strings.ToUpper(res.Status)
		if st == db.RunStatusCompleted {
			terminalResults = append(terminalResults, res)
		}
	}
	r.Results = terminalResults

	// Sort results
	sort.Slice(r.Results, func(i, j int) bool {
		if r.Results[i].Scenario != r.Results[j].Scenario {
			return r.Results[i].Scenario < r.Results[j].Scenario
		}
		return r.Results[i].Alternative < r.Results[j].Alternative
	})

	r.calculateStats()

	r.writeHeader()
	r.writeExecutiveSummary()
	r.writeMetricsOverview()
	r.writePerformanceComparison()
	r.writeExperimentParameters()
	r.writeNotes()
	r.writeSummaryByScenario()
	r.writeDetailedMetrics()
	r.writeEvaluationDetails()
	r.writeToolUsage()
	r.writeStatisticalAnalysis()
	r.writeFailureAnalysis()
	r.writeConclusion()

	return nil
}

func (r *EnhancedMarkdownGenerator) calculateStats() {
	control := ""
	var allAlts []string
	if r.Cfg != nil {
		control = r.Cfg.Control
		for _, alt := range r.Cfg.Alternatives {
			allAlts = append(allAlts, alt.Name)
		}
	}
	r.summary = runner.CalculateSummary(r.Results, control, allAlts, r.ToolCounts)
}

func (r *EnhancedMarkdownGenerator) writeHeader() {
	fmt.Fprintln(r.w, "# Tenkai Experiment Report")
	fmt.Fprintf(r.w, "_Generated at: %s_\n", time.Now().Format(time.RFC1123))
}

func (r *EnhancedMarkdownGenerator) writeExperimentParameters() {
	if r.Cfg == nil {
		return
	}
	fmt.Fprintln(r.w, "\n## 🧪 Experiment Parameters")
	if r.Cfg.Description != "" {
		fmt.Fprintf(r.w, "> %s\n\n", r.Cfg.Description)
	}

	fmt.Fprintln(r.w, "| Parameter | Value |")
	fmt.Fprintln(r.w, "| :--- | :--- |")
	fmt.Fprintf(r.w, "| **Repetitions** | %d |\n", r.Cfg.Repetitions)
	fmt.Fprintf(r.w, "| **Concurrent Workers** | %d |\n", r.Cfg.MaxConcurrent)
	fmt.Fprintf(r.w, "| **Total Scenarios** | %d |\n", len(r.Cfg.Scenarios))

	fmt.Fprintln(r.w, "\n### Alternatives Configuration")
	for i, alt := range r.Cfg.Alternatives {
		role := ""
		if i == 0 {
			role = " (Control 🏳️)"
		}
		fmt.Fprintf(r.w, "- **%s**%s\n", alt.Name, role)
		if alt.Description != "" {
			fmt.Fprintf(r.w, "  > %s\n", alt.Description)
		}
		fmt.Fprintf(r.w, "  - Model: `%s`\n", getValue(alt.Args, "--model"))
		if alt.SystemPromptFile != "" {
			filepath.Base(alt.SystemPromptFile)
			fmt.Fprintf(r.w, "  - System Prompt: `%s`\n", filepath.Base(alt.SystemPromptFile))
		} else if alt.Env != nil && alt.Env["GEMINI_SYSTEM_MD"] != "" {
			path := alt.Env["GEMINI_SYSTEM_MD"]
			fmt.Fprintf(r.w, "  - System Prompt: `%s`\n", filepath.Base(path))
		}

		if alt.SettingsPath != "" {
			fmt.Fprintf(r.w, "  - Tool Settings: `%s`\n", filepath.Base(alt.SettingsPath))
		}
	}
}

func getValue(args []string, key string) string {
	for i, arg := range args {
		if arg == key && i+1 < len(args) {
			return args[i+1]
		}
	}
	return "default"
}

func (r *EnhancedMarkdownGenerator) writeNotes() {
	if len(r.Notes) == 0 {
		return
	}
	fmt.Fprintln(r.w, "\n## 📝 Notes")
	for _, note := range r.Notes {
		fmt.Fprintf(r.w, "> %s\n\n", note)
	}
}

func (r *EnhancedMarkdownGenerator) writeMetricsOverview() {
	fmt.Fprintln(r.w, "\n## 📈 Metrics Overview")
	fmt.Fprintln(r.w, "| Alternative | Avg Duration | Total Tokens | Avg Cost | Success Rate |")
	fmt.Fprintln(r.w, "| :--- | :--- | :--- | :--- | :--- |")

	for _, name := range r.getAltOrder() {
		a, ok := r.summary.Alternatives[name]
		if !ok {
			continue
		}

		avgDur := time.Duration(a.AvgDuration * float64(time.Second)).Round(time.Millisecond).String()
		cost := fmt.Sprintf("$%.4f", float64(a.AvgTokens)/1000000*0.15) // Approx cost pricing for flash/pro blend

		fmt.Fprintf(r.w, "| %s | %s | %s | %s | %.0f%% |\n", name, avgDur, formatNumber(int(a.AvgTokens*float64(a.TotalRuns))), cost, a.SuccessRate)
	}
}

func (r *EnhancedMarkdownGenerator) writeExecutiveSummary() {
	fmt.Fprintln(r.w, "\n## 📊 Executive Summary")

	if r.summary == nil || r.summary.TotalRuns == 0 {
		fmt.Fprintln(r.w, "No data available.")
		return
	}

	// 1. Overall Health
	totalRuns := r.summary.TotalRuns
	successCount := r.summary.SuccessfulRuns
	globalSuccessRate := r.summary.SuccessRate

	healthEmoji := "🟢"
	if globalSuccessRate < 80 {
		healthEmoji = "🟡"
	}
	if globalSuccessRate < 50 {
		healthEmoji = "🔴"
	}

	fmt.Fprintf(r.w, "This experiment executed **%d runs** (**%d successful**) across **%d scenarios** with an overall success rate of **%.1f%%** %s.\n\n",
		totalRuns, successCount, len(r.Cfg.Scenarios), globalSuccessRate, healthEmoji)

	// 2. Identify Winners
	var bestSuccess, bestSpeed, bestEfficiency *models.ExperimentSummaryRow

	for _, name := range r.getAltOrder() {
		s, ok := r.summary.Alternatives[name]
		if !ok {
			continue
		}
		if bestSuccess == nil || s.SuccessRate > bestSuccess.SuccessRate {
			bestSuccess = &s
		}
		if s.SuccessCount > 0 {
			if bestSpeed == nil || s.AvgDuration < bestSpeed.AvgDuration {
				bestSpeed = &s
			}
			if bestEfficiency == nil || s.AvgTokens < bestEfficiency.AvgTokens {
				bestEfficiency = &s
			}
		}
	}

	if bestSuccess != nil {
		fmt.Fprintln(r.w, "### 🏆 Key Findings")
		fmt.Fprintf(r.w, "- **Most Reliable**: **%s** passed %.1f%% of runs.\n", bestSuccess.Alternative, bestSuccess.SuccessRate)

		if bestSpeed != nil {
			fmt.Fprintf(r.w, "- **Fastest**: **%s** averaged %s per successful run.\n", bestSpeed.Alternative, time.Duration(bestSpeed.AvgDuration*float64(time.Second)).Round(time.Millisecond))
		}
		if bestEfficiency != nil {
			fmt.Fprintf(r.w, "- **Most Efficient**: **%s** used only %s tokens per run.\n", bestEfficiency.Alternative, formatNumber(int(bestEfficiency.AvgTokens)))
		}
	}
}

func (r *EnhancedMarkdownGenerator) getAltOrder() []string {
	names := []string{}
	if r.Cfg != nil {
		for _, alt := range r.Cfg.Alternatives {
			names = append(names, alt.Name)
		}
	}
	// Add any that are in results but not in config
	for name := range r.summary.Alternatives {
		found := false
		for _, n := range names {
			if n == name {
				found = true
				break
			}
		}
		if !found {
			names = append(names, name)
		}
	}
	return names
}

func (r *EnhancedMarkdownGenerator) writePerformanceComparison() {
	fmt.Fprintln(r.w, "\n## 🏆 Performance Comparison")

	order := r.getAltOrder()

	// Identify Control (first in config)
	var control *models.ExperimentSummaryRow
	if r.Cfg != nil && len(r.Cfg.Alternatives) > 0 {
		c, ok := r.summary.Alternatives[r.Cfg.Control]
		if ok {
			control = &c
		} else {
			// Fallback to first alt in results
			if len(order) > 0 {
				c2 := r.summary.Alternatives[order[0]]
				control = &c2
			}
		}
	}

	fmt.Fprintln(r.w, "| Alternative | Avg Duration (Success) | Avg Tokens (Success) | Success Rate | Status |")
	fmt.Fprintln(r.w, "| :--- | :--- | :--- | :--- | :--- |")

	for _, name := range order {
		a, ok := r.summary.Alternatives[name]
		if !ok {
			continue
		}

		durStr := "-"
		tokenStr := "-"
		successStr := fmt.Sprintf("%.0f%%", a.SuccessRate)

		if a.SuccessCount > 0 || (a.TotalRuns > 0 && a.AvgDuration > 0) {
			durStr = time.Duration(a.AvgDuration * float64(time.Second)).Round(time.Second).String()
			tokenStr = formatNumber(int(a.AvgTokens))

			// Calculate Deltas vs Control
			if control != nil && name != control.Alternative && control.TotalRuns > 0 {
				if control.AvgDuration > 0 {
					durDiff := a.AvgDuration - control.AvgDuration
					durPct := (durDiff / control.AvgDuration) * 100
					durStr += fmt.Sprintf(" (%+.0f%%)%s", durPct, sigFlag(a.PDuration))
				}

				if control.AvgTokens > 0 {
					tokenDiff := a.AvgTokens - control.AvgTokens
					tokenPct := (tokenDiff / control.AvgTokens) * 100
					tokenStr += fmt.Sprintf(" (%+.0f%%)%s", tokenPct, sigFlag(a.PTokens))
				}

				successStr += sigFlag(a.PSuccess)
			} else if control != nil && name == control.Alternative {
				durStr += " (Control)"
			}
		}

		status := "✅"
		if a.SuccessRate < 50 {
			status = "🔴"
		} else if a.SuccessRate < 85 {
			status = "🟡"
		}

		fmt.Fprintf(r.w, "| %s | %s | %s | %s | %s |\n", name, durStr, tokenStr, successStr, status)
	}
}

func sigFlag(p float64) string {
	if p < 0.01 {
		return " **"
	}
	if p < 0.05 {
		return " *"
	}
	return ""
}

func formatNumber(n int) string {
	if n > 1000000 {
		return fmt.Sprintf("%.1fM", float64(n)/1000000.0)
	}
	if n > 1000 {
		return fmt.Sprintf("%.1fK", float64(n)/1000.0)
	}
	return fmt.Sprintf("%d", n)
}

func (r *EnhancedMarkdownGenerator) writeSummaryByScenario() {
	fmt.Fprintln(r.w, "\n## 📋 Summary by Scenario")

	scenarios := make(map[string]map[string]float64)
	allScenarios := []string{}

	for _, res := range r.Results {
		if _, ok := scenarios[res.Scenario]; !ok {
			scenarios[res.Scenario] = make(map[string]float64)
			allScenarios = append(allScenarios, res.Scenario)
		}
	}
	sort.Strings(allScenarios)

	header := "| Scenario |"
	divider := "| :--- |"
	order := r.getAltOrder()
	for _, alt := range order {
		header += " " + alt + " |"
		divider += " :---: |"
	}
	fmt.Fprintln(r.w, header)
	fmt.Fprintln(r.w, divider)

	// Calculate success rates per scenario per alternative
	for _, scen := range allScenarios {
		line := "| " + scen + " |"
		for _, alt := range order {
			count := 0
			success := 0
			for _, res := range r.Results {
				if res.Scenario == scen && res.Alternative == alt {
					count++
					if res.IsSuccess {
						success++
					}
				}
			}
			if count > 0 {
				rate := float64(success) / float64(count) * 100
				line += fmt.Sprintf(" %.0f%% |", rate)
			} else {
				line += " - |"
			}
		}
		fmt.Fprintln(r.w, line)
	}
}

func (r *EnhancedMarkdownGenerator) writeDetailedMetrics() {
	fmt.Fprintln(r.w, "\n## 📈 Detailed Metrics")
	fmt.Fprintln(r.w, "| Alternative | Avg Tool Calls | Tool Success | Avg Lint Issues | Test Pass Rate |")
	fmt.Fprintln(r.w, "| :--- | :---: | :---: | :---: | :---: |")

	for _, name := range r.getAltOrder() {
		a, ok := r.summary.Alternatives[name]
		if !ok {
			continue
		}

		avgTools := float64(a.TotalToolCalls) / float64(a.TotalRuns)
		toolSuccess := 0.0
		if a.TotalToolCalls > 0 {
			toolSuccess = float64(a.TotalToolCalls-a.FailedToolCalls) / float64(a.TotalToolCalls) * 100
		}

		fmt.Fprintf(r.w, "| %s | %.1f | %.1f%% | %.1f | %.1f%% |\n",
			name, avgTools, toolSuccess, a.AvgLint, a.SuccessRate) // Simplified test pass rate for now
	}
}

func (r *EnhancedMarkdownGenerator) writeEvaluationDetails() {
	fmt.Fprintln(r.w, "\n## 🧪 Evaluation Details")
	fmt.Fprintln(r.w, "Detailed breakdown of failed runs and evaluation outputs.")

	for _, res := range r.Results {
		if !res.IsSuccess {
			status := "FAIL"
			if res.Error != nil && strings.Contains(res.Error.Error(), "timeout") {
				status = "TIMEOUT"
			}
			fmt.Fprintf(r.w, "\n### ❌ %s: %s (Rep #%d) [%s]\n", res.Alternative, res.Scenario, res.Repetition, status)
			if res.Error != nil {
				fmt.Fprintf(r.w, "> **Error:** `%v`\n", res.Error)
			}
			if res.ValidationReport != "" {
				var report runner.ValidationReport
				if err := json.Unmarshal([]byte(res.ValidationReport), &report); err == nil {
					for _, item := range report.Items {
						if item.Status == "FAIL" {
							fmt.Fprintf(r.w, "- **%s**: %s\n", item.Type, item.Description)
						}
					}
				}
			}
		}
	}
}

func (r *EnhancedMarkdownGenerator) writeToolUsage() {
	fmt.Fprintln(r.w, "\n## 🛠️ Tool Usage Analysis")

	// 1. Raw Counts (Using authoritative ToolCounts map)
	usage := make(map[string]map[string]int)
	for _, res := range r.Results {
		counts := r.ToolCounts[res.RunID]
		if counts != nil {
			if _, ok := usage[res.Alternative]; !ok {
				usage[res.Alternative] = make(map[string]int)
			}
			for name, count := range counts {
				usage[res.Alternative][name] += count
			}
		}
	}

	for _, alt := range r.getAltOrder() {
		u, ok := usage[alt]
		if !ok {
			continue
		}
		summary, okSummary := r.summary.Alternatives[alt]
		fmt.Fprintf(r.w, "\n### %s\n", alt)

		// Sort tools by frequency
		var toolNames []string
		for name := range u {
			toolNames = append(toolNames, name)
		}
		sort.Slice(toolNames, func(i, j int) bool {
			return u[toolNames[i]] > u[toolNames[j]]
		})

		for _, name := range toolNames {
			total := u[name]
			// Detailed failure breakdown by tool is not currently available in the lightweight reporting struct.
			// Showing total usage count.
			fmt.Fprintf(r.w, "- `%s`: %d\n", name, total)
		}

		// 2. Statistical Impact
		if okSummary && len(summary.ToolAnalysis) > 0 {
			var drivers []string
			var costs []string

			for _, t := range summary.ToolAnalysis {
				// Success Driver
				if t.SuccFailPValue >= 0 && t.SuccFailPValue < 0.05 {
					// We need to know direction (did winners use it MORE or LESS?).
					// MannWhitney just says 'differs'. We can infer from raw data if we had it here,
					// or just state "Significant Difference".
					// For now: "Significantly different usage in successful runs"
					drivers = append(drivers, fmt.Sprintf("- **%s** (p=%.4f) - differs between success/fail", t.ToolName, t.SuccFailPValue))
				}

				// Cost Driver (Correlation > 0.5)
				if t.DurationCorr > 0.5 {
					costs = append(costs, fmt.Sprintf("- **%s** (rho=%.2f) - correlates with duration", t.ToolName, t.DurationCorr))
				}
				if t.TokensCorr > 0.5 {
					costs = append(costs, fmt.Sprintf("- **%s** (rho=%.2f) - correlates with token usage", t.ToolName, t.TokensCorr))
				}
			}

			if len(drivers) > 0 || len(costs) > 0 {
				fmt.Fprintln(r.w, "\n  **📈 Statistical Insights:**")
				for _, d := range drivers {
					fmt.Fprintln(r.w, "  "+d)
				}
				for _, c := range costs {
					fmt.Fprintln(r.w, "  "+c)
				}
			}
		}
	}
}

func (r *EnhancedMarkdownGenerator) writeFailureAnalysis() {
	timeouts := []string{}
	failures := []string{}
	loops := []string{}

	for _, res := range r.Results {
		key := fmt.Sprintf("%s|%s|#%d", res.Alternative, res.Scenario, res.Repetition)
		if res.Error != nil && strings.Contains(strings.ToLower(res.Error.Error()), "timeout") {
			timeouts = append(timeouts, key)
		} else if !res.IsSuccess {
			failures = append(failures, key)
		}
		if res.AgentMetrics != nil && res.AgentMetrics.LoopDetected {
			loops = append(loops, key)
		}
	}

	if len(timeouts) > 0 || len(failures) > 0 || len(loops) > 0 {
		fmt.Fprintln(r.w, "\n## ⚠️ Failure Analysis")

		if len(timeouts) > 0 {
			fmt.Fprintf(r.w, "\n### Timeouts (%d runs)\n", len(timeouts))
			byAlt := make(map[string]int)
			for _, t := range timeouts {
				alt := strings.Split(t, "|")[0]
				byAlt[alt]++
			}
			for alt, count := range byAlt {
				fmt.Fprintf(r.w, "- **%s**: %d timeout(s)\n", alt, count)
			}
		}

		if len(failures) > 0 {
			fmt.Fprintf(r.w, "\n### Semantic Failures (%d runs)\n", len(failures))
			uniqueErrors := make(map[string]struct {
				count int
				alts  map[string]bool
			})
			for _, res := range r.Results {
				if !res.IsSuccess && (res.Error == nil || !strings.Contains(strings.ToLower(res.Error.Error()), "timeout")) {
					reason := "Validation Failure"
					if res.Error != nil {
						reason = res.Error.Error()
					}
					info := uniqueErrors[reason]
					info.count++
					if info.alts == nil {
						info.alts = make(map[string]bool)
					}
					info.alts[res.Alternative] = true
					uniqueErrors[reason] = info
				}
			}

			fmt.Fprintln(r.w, "| Failure Reason | Count | Alternatives |")
			fmt.Fprintln(r.w, "| :--- | :---: | :--- |")
			for reason, data := range uniqueErrors {
				alts := []string{}
				for a := range data.alts {
					alts = append(alts, a)
				}
				fmt.Fprintf(r.w, "| %s | %d | %s |\n", reason, data.count, strings.Join(alts, ", "))
			}
		}

		// Problem Scenarios
		scenarioStats := make(map[string]struct{ total, failed int })
		for _, res := range r.Results {
			s := scenarioStats[res.Scenario]
			s.total++
			if !res.IsSuccess {
				s.failed++
			}
			scenarioStats[res.Scenario] = s
		}

		var problemScenarios []string
		for scenario, stats := range scenarioStats {
			failRate := float64(stats.failed) / float64(stats.total) * 100
			if failRate > 50 {
				problemScenarios = append(problemScenarios, fmt.Sprintf("- **%s**: %.0f%% failure rate (likely broken scenario)", scenario, failRate))
			}
		}

		if len(problemScenarios) > 0 {
			fmt.Fprintln(r.w, "\n### Problem Scenarios")
			for _, line := range problemScenarios {
				fmt.Fprintln(r.w, line)
			}
		}
	}
}

func (r *EnhancedMarkdownGenerator) writeConclusion() {
	fmt.Fprintln(r.w, "\n## 💡 Conclusion")
	if r.summary.SuccessRate > 90 {
		fmt.Fprintln(r.w, "The models are performing exceptionally well across all scenarios.")
	} else if r.summary.SuccessRate > 70 {
		fmt.Fprintln(r.w, "Overall performance is good, but there are clear areas for improvement in specific scenarios.")
	} else {
		fmt.Fprintln(r.w, "Performance is below expectations. Further analysis of semantic failures is recommended.")
	}
}

func (r *EnhancedMarkdownGenerator) writeStatisticalAnalysis() {
	// Find Control
	control := ""
	if r.Cfg != nil {
		control = r.Cfg.Control
	}
	// Fallback to first alt if not set
	if control == "" && len(r.summary.Alternatives) > 0 {
		control = r.getAltOrder()[0]
	}

	hasStats := false
	for _, alt := range r.summary.Alternatives {
		if alt.Alternative == control {
			continue
		}
		// Check for sentinel value -1.0 (Not Calculated)
		// If any p-value is >= 0, stats were calculated.
		if alt.PSuccess >= 0 || alt.PDuration >= 0 || alt.PTokens >= 0 || alt.PLint >= 0 {
			hasStats = true
			break
		}
	}

	if !hasStats {
		return
	}

	fmt.Fprintln(r.w, "\n## 📊 Statistical Analysis Notes")
	fmt.Fprintln(r.w, "This report uses **Welch's t-test** for continuous metrics (Duration, Tokens, Lint Issues) and **Fisher's Exact Test** for categorical metrics (Success Rate, Timeouts).")
	fmt.Fprintln(r.w, "\n- **( * )**: Significant at p < 0.05")
	fmt.Fprintln(r.w, "- **( ** )**: Highly significant at p < 0.01")
	fmt.Fprintln(r.w, "\n### Significant Findings")

	foundSig := false
	for _, name := range r.getAltOrder() {
		if name == control {
			continue
		}
		alt := r.summary.Alternatives[name]

		// Helper to format
		check := func(metric string, p float64) {
			// p < 0 means not calculated
			if p >= 0 && p < 0.05 {
				foundSig = true
				stars := "*"
				if p < 0.01 {
					stars = "**"
				}
				fmt.Fprintf(r.w, "- **%s** shows a significant difference in **%s** (p=%.4f) %s\n", name, metric, p, stars)
			}
		}

		check("Success Rate", alt.PSuccess)
		check("Duration", alt.PDuration)
		check("Token Usage", alt.PTokens)
		check("Lint Issues", alt.PLint)
	}

	if !foundSig {
		fmt.Fprintln(r.w, "No statistically significant differences (p < 0.05) were detected between the alternatives and the control.")
	}
}
