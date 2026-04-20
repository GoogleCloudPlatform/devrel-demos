#!/bin/bash

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Function to kill processes on a given port
kill_port() {
    local port=$1
    echo "Checking port $port..."
    local pids=$(lsof -ti:$port)
    if [ -n "$pids" ]; then
        echo "Killing processes on port $port: $pids"
        kill -9 $pids 2>/dev/null
    else
        echo "No processes found on port $port"
    fi
}

# Kill existing processes
kill_port 8000

# Start Agent Server
echo "Starting Agent Server..."
# Using the command specified by the user
uv run adk api_server --session_service_uri sqlite:///./.adk/sessions.db .
