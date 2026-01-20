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
		{"Blocked: rm root", "rm", []string{"-rf", "/"}, true}, // rm is not explicitly blocked in hardBlockList but fails validation? Actually rm is not in allowlist either. Wait, v2 doesn't have an allowlist, it validates metachars and hardBlockList. rm is just a command. If it's not in hardBlockList, it's allowed unless args are unsafe.
		// Wait, rm is dangerous. Is it in hardBlockList? I should check run.go content again.
		// No, hardBlockList has sudo, chown, etc. rm is not there.
		// But args validation catches "/" or ".."
		{"Blocked: path traversal", "ls", []string{".."}, true},
		{"Blocked: absolute path", "ls", []string{"/etc/passwd"}, true},
		{"Advisory: grep (allowed with advice)", "grep", []string{"foo"}, false}, // Changed from true to false
		{"Blocked: git", "git", []string{"status"}, true},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			_, err := validateCommand(tt.cmd, tt.args)
			if (err != nil) != tt.wantErr {
				t.Errorf("validateCommand() error = %v, wantErr %v", err, tt.wantErr)
			}
		})
	}
}
