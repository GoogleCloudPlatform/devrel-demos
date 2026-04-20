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

# Kill existing processe
kill_port 8080

if [ -f .env ]; then
    source .env
fi

if [ "$SERVER_BASE_URL" == "" ]; then
    SERVER_BASE_URL="http://localhost:8000"
fi

export SERVER_BASE_URL
export AGENT_NAME

# Start ADK Web Client Server
echo "Starting ADK Web Client Server..."
cd src
node server.js
