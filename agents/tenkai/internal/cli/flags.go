package cli

import (
	"flag"
)

type Flags struct {
	ConfigPath    *string
	Serve         *bool
	Port          *int
	Reps          *int
	Concurrent    *int
	Name          *string
	Alts          *string
	Scens         *string
	Control       *string
	Timeout       *string
	ExperimentID  *int64
	FixReportPath *string
}

func parseFlags() Flags {
	f := Flags{
		ConfigPath:    flag.String("config", "", "Path to configuration file"),
		Serve:         flag.Bool("serve", false, "Run as API server"),
		Port:          flag.Int("port", 8080, "Port for API server"),
		Reps:          flag.Int("reps", 0, "Override number of repetitions"),
		Concurrent:    flag.Int("concurrent", 0, "Override max concurrent workers"),
		Name:          flag.String("name", "", "Override experiment name"),
		Alts:          flag.String("alternatives", "", "Comma-separated list of alternatives to run"),
		Scens:         flag.String("scenarios", "", "Comma-separated list of scenarios to run"),
		Control:       flag.String("control", "", "Name of the control alternative"),
		Timeout:       flag.String("timeout", "", "Override timeout duration (e.g. 5m)"),
		ExperimentID:  flag.Int64("experiment-id", 0, "Experiment ID to regenerate report"),
		FixReportPath: flag.String("fix-report", "", "Path to existing report.md to fix structure/formatting"),
	}
	flag.Parse()
	return f
}
