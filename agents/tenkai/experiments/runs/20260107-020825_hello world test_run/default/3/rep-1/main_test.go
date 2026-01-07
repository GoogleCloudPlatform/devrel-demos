package main

import (
	"bytes"
	"io"
	"os"
	"strings"
	"testing"
)

func TestGreeting(t *testing.T) {
	expected := greetingMessage
	actual := greeting()
	if actual != expected {
		t.Errorf("greeting() = %q, want %q", actual, expected)
	}
}

func TestMain(t *testing.T) {
	old := os.Stdout
	r, w, _ := os.Pipe()
	os.Stdout = w

	main()

	w.Close()
	os.Stdout = old

	var buf bytes.Buffer
	if _, err := io.Copy(&buf, r); err != nil {
		t.Fatal(err)
	}

	expected := greetingMessage
	actual := strings.TrimSpace(buf.String())
	if actual != expected {
		t.Errorf("main() output = %q, want %q", actual, expected)
	}
}
