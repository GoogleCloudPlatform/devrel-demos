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
kill_port 8080

# Start Agent Server
echo "Starting Agent Server..."
# Using the command specified by the user
uv run adk api_server --session_service_uri sqlite:///./.adk/sessions.db . &
AGENT_PID=$!

# Start Web Client Server
echo "Starting Web Client Server..."
# Navigate to web_client directory to serve correct files
cd web_client
export SERVER_BASE_URL="http://localhost:8000"
node server.js &
CLIENT_PID=$!

echo "Processes started:"
echo "  Agent Server PID: $AGENT_PID"
echo "  Web Client PID: $CLIENT_PID"

# Function to cleanup processes on exit
cleanup() {
    echo "\nShutting down..."
    kill $AGENT_PID 2>/dev/null
    kill $CLIENT_PID 2>/dev/null
    exit 0
}

# Trap SIGINT (Ctrl+C) and SIGTERM
trap cleanup SIGINT SIGTERM

# Monitor processes
while true; do
    if ! kill -0 $AGENT_PID 2>/dev/null; then
        echo "Agent server stopped unexpectedly."
        cleanup
    fi

    if ! kill -0 $CLIENT_PID 2>/dev/null; then
        echo "Web client server stopped unexpectedly."
        cleanup
    fi

    sleep 1
done
