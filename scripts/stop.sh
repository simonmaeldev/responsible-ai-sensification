#!/usr/bin/env bash
PIDS=$(lsof -ti :8080)
if [ -n "$PIDS" ]; then
    kill $PIDS && echo "Stopped"
else
    echo "Not running"
fi
