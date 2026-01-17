package run

import (
	"testing"
)

func TestSafeShell(t *testing.T) {

	tests := []struct {
		name    string
		cmd     string
		args    []string
		wantErr bool
	}{
		{"Allowed: go version", "go", []string{"version"}, false},
		{"Blocked: rm root", "rm", []string{"-rf", "/"}, true},
		{"Blocked: path traversal", "ls", []string{".."}, true},
		{"Blocked: absolute path", "ls", []string{"/etc/passwd"}, true},
		{"Advisory: grep (no force)", "grep", []string{"foo"}, true},
		{"Blocked: git", "git", []string{"status"}, true},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			err := validateCommand(tt.cmd, tt.args, false)
			if (err != nil) != tt.wantErr {
				t.Errorf("validateCommand() error = %v, wantErr %v", err, tt.wantErr)
			}
		})
	}
}
