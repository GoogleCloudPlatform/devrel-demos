package main

import (
	"flag"
	"fmt"
	"os"
)

func main() {
	name := flag.String("name", "World", "a name to say hello to")
	flag.Parse()

	if err := run(*name); err != nil {
		fmt.Fprintf(os.Stderr, "error: %v
", err)
		os.Exit(1)
	}
}

func run(name string) error {
	fmt.Printf("Hello, %s!
", name)
	return nil
}
