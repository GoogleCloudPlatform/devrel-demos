package library_test

import (
	"testing"

	"example.com/library"
)

func TestHello(t *testing.T) {
	want := "Hello, World!"
	got := library.Hello("World")
	if got != want {
		t.Errorf("Hello() = %q, want %q", got, want)
	}
}
