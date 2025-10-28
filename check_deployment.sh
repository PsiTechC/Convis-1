#!/bin/bash

echo "==================================="
echo "Convis Deployment Status Check"
echo "==================================="
echo ""

echo "1. Checking Docker containers..."
docker-compose ps
echo ""

echo "2. Checking backend health..."
curl -s http://localhost:8000/health 2>/dev/null && echo "" || echo "Backend not ready yet"
echo ""

echo "3. Checking frontend..."
FRONTEND_STATUS=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:3000 2>/dev/null)
if [ "$FRONTEND_STATUS" = "200" ]; then
    echo "Frontend is ready! Status: $FRONTEND_STATUS"
else
    echo "Frontend not ready yet. Status: $FRONTEND_STATUS"
fi
echo ""

echo "4. Access URLs:"
echo "   - Frontend:     http://localhost:3000"
echo "   - Backend API:  http://localhost:8000"
echo "   - API Docs:     http://localhost:8000/docs"
echo ""

echo "==================================="
