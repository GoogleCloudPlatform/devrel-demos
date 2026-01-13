package main

import (
	"fmt"

	"github.com/danicat/godoctor/internal/instructions"
)

func printAgentInstructions(experimental bool) {

	fmt.Println(instructions.Get(experimental))

}
