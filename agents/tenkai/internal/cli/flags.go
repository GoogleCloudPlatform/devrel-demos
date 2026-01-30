package cli

import (
	"flag"
	"os"
	"strconv"
)

type Flags struct {
	ConfigPath        *string
	Serve             *bool
	Port              *int
	Reps              *int
	Concurrent        *int
	Name              *string
	Alts              *string
	Scens             *string
	Control           *string
	Timeout           *string
	ExperimentID      *int64
	RevalID           *int64
	FixReportPath     *string
	Worker            *bool
	GCSBucket         *string
	StartExperimentID *int64
}

func ParseFlags() Flags {
	defaultPort := 8080
	if envPort := os.Getenv("PORT"); envPort != "" {
		if p, err := strconv.Atoi(envPort); err == nil {
			defaultPort = p
		}
	}
	f := Flags{
		ConfigPath:        flag.String("config", "", "Path to configuration file"),
		Serve:             flag.Bool("serve", false, "Run as API server"),
		Port:              flag.Int("port", defaultPort, "Port for API server"),
		Reps:              flag.Int("reps", 0, "Override number of repetitions"),
		Concurrent:        flag.Int("concurrent", 0, "Override max concurrent workers"),
		Name:              flag.String("name", "", "Override experiment name"),
		Alts:              flag.String("alternatives", "", "Comma-separated list of alternatives to run"),
		Scens:             flag.String("scenarios", "", "Comma-separated list of scenarios to run"),
		Control:           flag.String("control", "", "Name of the control alternative"),
		Timeout:           flag.String("timeout", "", "Override timeout duration (e.g. 5m)"),
		ExperimentID:      flag.Int64("experiment-id", 0, "Experiment ID to regenerate report"),
		RevalID:           flag.Int64("reval", 0, "Experiment ID to re-validate runs"),
		FixReportPath:     flag.String("fix-report", "", "Path to existing report.md to fix structure/formatting"),
		Worker:            flag.Bool("worker", false, "Run in worker mode"),
		GCSBucket:         flag.String("gcs-bucket", "", "GCS bucket for artifact storage"),
		StartExperimentID: flag.Int64("start-experiment-id", 0, "Experiment ID to start (resume/orchestrate)"),
	}
	flag.Parse()
	return f
}
