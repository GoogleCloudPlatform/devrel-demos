package execution

import (
	"bytes"
	"context"
	"strings"
	"testing"
)

func TestLocalExecutor_Execute(t *testing.T) {
	e := NewLocalExecutor()
	ctx := context.Background()

	stdout := &bytes.Buffer{}
	stderr := &bytes.Buffer{}
	stdin := strings.NewReader("hello stdin")

	cfg := JobConfig{
		ID:      "test-job",
		Command: []string{"cat"}, // cat checks stdin
		WorkDir: "/tmp",
		Env:     map[string]string{"foo": "bar"},
	}

	res := e.Execute(ctx, cfg, stdin, stdout, stderr)

	if res.ExitCode != 0 {
		t.Errorf("expected exit code 0, got %d", res.ExitCode)
	}
	if res.Error != nil {
		t.Errorf("expected no error, got %v", res.Error)
	}

	if stdout.String() != "hello stdin" {
		t.Errorf("expected stdout 'hello stdin', got '%s'", stdout.String())
	}
}

func TestLocalExecutor_Env(t *testing.T) {
	e := NewLocalExecutor()
	ctx := context.Background()

	stdout := &bytes.Buffer{}
	stderr := &bytes.Buffer{}
	stdin := strings.NewReader("")

	cfg := JobConfig{
		ID:      "test-env",
		Command: []string{"printenv", "TEST_VAR"},
		WorkDir: "/tmp",
		Env:     map[string]string{"TEST_VAR": "foobar"},
	}

	res := e.Execute(ctx, cfg, stdin, stdout, stderr)
	if res.Error != nil {
		t.Errorf("expected no error, got %v", res.Error)
	}

	output := strings.TrimSpace(stdout.String())
	if output != "foobar" {
		t.Errorf("expected output 'foobar', got '%s'", output)
	}
}
