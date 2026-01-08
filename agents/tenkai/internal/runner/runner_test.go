package runner

import (
	"fmt"
	"testing"

	"github.com/GoogleCloudPlatform/devrel-demos/agents/tenkai/internal/db"
)

func TestResultSuccess(t *testing.T) {
	tests := []struct {
		name     string
		res      Result
		expected bool
	}{
		{
			name:     "Success with Validation Report",
			res:      Result{IsSuccess: true, ValidationReport: `{"overall_success": true}`},
			expected: true,
		},
		{
			name:     "Failure with Validation Report",
			res:      Result{IsSuccess: false, ValidationReport: `{"overall_success": false}`},
			expected: false,
		},
		{
			name:     "Failure with Error",
			res:      Result{Error: fmt.Errorf("timeout")},
			expected: false,
		},
		{
			name:     "Legacy Success (Tests Passed)",
			res:      Result{EvaluationMetrics: &db.EvaluationMetrics{TestsPassed: 1}},
			expected: true,
		},
		{
			name:     "Legacy Failure (No Tests)",
			res:      Result{EvaluationMetrics: &db.EvaluationMetrics{TestsPassed: 0}},
			expected: false,
		},
		{
			name:     "Empty Result",
			res:      Result{},
			expected: false,
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			if got := tt.res.Success(); got != tt.expected {
				t.Errorf("Result.Success() = %v, want %v", got, tt.expected)
			}
		})
	}
}

func TestIsTimeout(t *testing.T) {
	tests := []struct {
		name     string
		res      Result
		expected bool
	}{
		{
			name:     "Explicit Timeout Error",
			res:      Result{Error: fmt.Errorf("context deadline exceeded")},
			expected: true,
		},
		{
			name:     "Timeout String Error",
			res:      Result{Error: fmt.Errorf("execution timeout")},
			expected: true,
		},
		{
			name:     "Other Error",
			res:      Result{Error: fmt.Errorf("process failed")},
			expected: false,
		},
		{
			name:     "No Error",
			res:      Result{},
			expected: false,
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			if got := tt.res.IsTimeout(); got != tt.expected {
				t.Errorf("Result.IsTimeout() = %v, want %v", got, tt.expected)
			}
		})
	}
}
