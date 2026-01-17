package main

import (
	"context"
	"io"
	"os"
	"os/exec"
	"reflect"
	"strings"
	"testing"
	"time"

	"github.com/modelcontextprotocol/go-sdk/mcp"
)

func TestMain(m *testing.M) {
	if os.Getenv("GO_TEST_MODE_INTEGRATION") == "1" {
		main()
		return
	}
	os.Exit(m.Run())
}

func TestNewServer(t *testing.T) {
	server := mcp.NewServer(&mcp.Implementation{Name: "hello-tenkai"}, nil)
	if server == nil {
		t.Fatal("server should not be nil")
	}
}

func TestHelloWorldTool(t *testing.T) {
	result, _, err := helloWorldTool(context.Background(), nil, nil)
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	expected := &mcp.CallToolResult{
		Content: []mcp.Content{
			&mcp.TextContent{Text: "Hello from Tenkai!"},
		},
	}
	if !reflect.DeepEqual(result, expected) {
		t.Errorf("unexpected result: got %+v, want %+v", result, expected)
	}
}

func TestHelloWorldIntegration(t *testing.T) {
	if os.Getenv("GO_TEST_MODE_INTEGRATION") == "1" {
		t.Skip("skipping integration test in server mode")
	}
	args := []string{"-test.run=TestHelloWorldIntegration"}
	cmd := exec.Command(os.Args[0], args...)
	cmd.Env = append(os.Environ(), "GO_TEST_MODE_INTEGRATION=1")

	stdin, err := cmd.StdinPipe()
	if err != nil {
		t.Fatal(err)
	}
	stdout, err := cmd.StdoutPipe()
	if err != nil {
		t.Fatal(err)
	}
	if err := cmd.Start(); err != nil {
		t.Fatal(err)
	}

	requests := []string{
		`{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2025-06-18"}}`,
		`{"jsonrpc":"2.0","method":"notifications/initialized","params":{}}`,
		`{"jsonrpc":"2.0","id":2,"method":"tools/list","params":{}}`,
		`{"jsonrpc":"2.0","id":3,"method":"tools/call","params":{"name":"hello_world","arguments":{}}}`,
	}
	for _, req := range requests {
		if _, err := stdin.Write([]byte(req + "\n")); err != nil {
			t.Fatal(err)
		}
	}
	// Give the server a moment to process the requests
	time.Sleep(500 * time.Millisecond)
	if err := stdin.Close(); err != nil {
		t.Fatal(err)
	}

	var out []byte
	out, err = io.ReadAll(stdout)
	if err != nil {
		t.Fatal(err)
	}

	output := string(out)
	if !strings.Contains(output, "\"result\":{\"capabilities\":{\"logging\":{},\"tools\":{\"listChanged\":true}}") {
		t.Errorf("unexpected output: %s", output)
	}
	if !strings.Contains(output, "\"result\":{\"tools\":[{\"description\":\"Returns a hello message\",\"inputSchema\":{\"type\":\"object\"},\"name\":\"hello_world\"}]}") {
		t.Errorf("unexpected output: %s", output)
	}
	if !strings.Contains(output, "\"result\":{\"content\":[{\"type\":\"text\",\"text\":\"Hello from Tenkai!\"}]}") {
		t.Errorf("unexpected output: %s", output)
	}
	if err := cmd.Wait(); err != nil {
		if !strings.Contains(err.Error(), "exit status 1") {
			t.Fatal(err)
		}
	}
}
