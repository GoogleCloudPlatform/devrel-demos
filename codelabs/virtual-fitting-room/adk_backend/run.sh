#!/bin/bash
set -e

cd "$(dirname "$0")"

# Default run: serves the Flutter web build at /, API at /api/.
# For agent debugging without Flutter, run: `go run . --webui` instead.
go run .
