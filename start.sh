#!/bin/bash

# Start the Discord bot system
echo "Starting Nova Gaming Discord Bot System..."

# Kill any existing processes
pkill -f "python3 main.py" || true

# Start in background with nohup
nohup python3 main.py > logs/main.log 2>&1 &

# Check if process started
sleep 2
ps aux | grep "python3 main.py" | grep -v grep

echo "Bot system started. Check logs/main.log for details." 