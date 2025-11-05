#!/bin/bash

################################################################################
# Check Backend Logs on VPS
################################################################################

echo "=================================="
echo "CONVIS BACKEND LOGS"
echo "=================================="
echo ""

# Check if running locally or on VPS
if docker ps | grep -q "convis-api"; then
    echo "✓ Running on VPS/Local Docker environment"
    echo ""

    # Show last 100 lines of API logs
    echo "--- Last 100 lines of API logs ---"
    docker logs --tail 100 convis-api

    echo ""
    echo "=================================="
    echo "FOLLOW LIVE LOGS:"
    echo "=================================="
    echo ""
    echo "Run: docker logs -f convis-api"
    echo ""
    echo "To filter for specific issues:"
    echo "  docker logs -f convis-api | grep ERROR"
    echo "  docker logs -f convis-api | grep CUSTOM"
    echo "  docker logs -f convis-api | grep FREJUN"
    echo "  docker logs -f convis-api | grep REALTIME"
    echo ""
else
    echo "⚠ Docker container 'convis-api' not found"
    echo ""
    echo "Check if containers are running:"
    echo "  docker ps"
    echo ""
fi
