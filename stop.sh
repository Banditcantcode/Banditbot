#!/bin/bash

# Stop the Discord bot system
echo "Stopping Nova Gaming Discord Bot System..."

# Kill any existing processes
pkill -f "python3 main.py" || true

# Check if process stopped
sleep 2
if pgrep -f "python3 main.py" > /dev/null; then
    echo "Warning: Process is still running. Trying with SIGKILL..."
    pkill -9 -f "python3 main.py" || true
else
    echo "Process stopped successfully."
fi

echo "Bot system stopped." 