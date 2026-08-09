#!/bin/bash

# Determine script directory and point to root-level .venv
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
VENV_PYTHON="$SCRIPT_DIR/../.venv/bin/python3"
AGENTS_DIR="$SCRIPT_DIR/../agents"

# Kill any existing python processes running on our agent ports
echo "Cleaning up any existing agent processes on ports 8081, 8082, 8083..."
kill -9 $(lsof -t -i:8081 -i:8082 -i:8083 2>/dev/null) 2>/dev/null

echo "Starting Hotel Agent on port 8081..."
"$VENV_PYTHON" "$AGENTS_DIR/agents/hotel_agent.py" > "$AGENTS_DIR/hotel.log" 2>&1 &

echo "Starting Stadium Agent on port 8082..."
"$VENV_PYTHON" "$AGENTS_DIR/agents/stadium_agent.py" > "$AGENTS_DIR/stadium.log" 2>&1 &

echo "Waiting for sub-agents to start..."
sleep 3

echo "Starting Supervisor Agent on port 8083..."
"$VENV_PYTHON" "$AGENTS_DIR/agents/agent.py" > "$AGENTS_DIR/supervisor.log" 2>&1 &

echo "All agents launched in the background. Logs saved to: $AGENTS_DIR/*.log"
