package db

// Experiment Statuses
const (
	ExperimentStatusRunning   = "RUNNING"
	ExperimentStatusCompleted = "COMPLETED"
	ExperimentStatusAborted   = "ABORTED"
)

// Run Statuses
const (
	RunStatusQueued    = "QUEUED"
	RunStatusRunning   = "RUNNING"
	RunStatusCompleted = "COMPLETED"
	RunStatusAborted   = "ABORTED"
)

// Run Reasons
const (
	ReasonSuccess          = "SUCCESS"
	ReasonFailedValidation = "FAILED (VALIDATION)"
	ReasonFailedLoop       = "FAILED (LOOP)"
	ReasonFailedError      = "FAILED (ERROR)"
	ReasonFailedTimeout    = "FAILED (TIMEOUT)"
)
