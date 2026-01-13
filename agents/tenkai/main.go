package main

import (
	"github.com/GoogleCloudPlatform/devrel-demos/agents/tenkai/internal/cli"
)

var version = "dev"

func main() {
	cli.Execute(version)
}