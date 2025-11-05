#!/bin/bash

# Convis Local Development Stop Script
# This script stops the backend container

echo "======================================"
echo "   Stopping Convis Development"
echo "======================================"
echo ""

# Stop and remove backend container
if docker ps | grep -q convis-api-local; then
    echo "Stopping backend container..."
    docker stop convis-api-local
    docker rm convis-api-local
    echo "✓ Backend stopped"
else
    echo "Backend container is not running"
fi

echo ""
echo "Note: Frontend (npm dev) should be stopped with Ctrl+C in its terminal"
echo ""
echo "Done!"
