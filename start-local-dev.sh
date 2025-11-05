#!/bin/bash

# Convis Local Development Startup Script
# This script starts both backend and frontend for local development

set -e

echo "======================================"
echo "   Convis Local Development Setup"
echo "======================================"
echo ""

# Get the directory where the script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check if backend container is already running
if docker ps | grep -q convis-api-local; then
    echo -e "${YELLOW}Backend container is already running${NC}"
    read -p "Do you want to restart it? (y/n) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        echo "Stopping existing container..."
        docker stop convis-api-local
        docker rm convis-api-local
    else
        echo "Keeping existing container running"
    fi
fi

# Start backend if not running
if ! docker ps | grep -q convis-api-local; then
    echo -e "${GREEN}Starting backend API...${NC}"

    # Check if .env file exists
    if [ ! -f "convis-api/.env" ]; then
        echo -e "${RED}ERROR: convis-api/.env file not found!${NC}"
        echo "Please create the .env file with your configuration"
        exit 1
    fi

    # Check if image exists, if not build it
    if ! docker images | grep -q "convis-api.*v12"; then
        echo "Building backend Docker image (this may take a few minutes)..."
        docker build -t convis-api:v12 -f convis-api/Dockerfile convis-api
    fi

    # Run the container
    docker run -d \
        --name convis-api-local \
        -p 8010:8000 \
        --env-file convis-api/.env \
        convis-api:v12

    echo "Waiting for backend to start..."
    sleep 5

    # Check if backend is healthy
    if curl -s http://localhost:8010/health | grep -q "healthy"; then
        echo -e "${GREEN}✓ Backend API is running on http://localhost:8010${NC}"
    else
        echo -e "${RED}✗ Backend failed to start. Check logs with: docker logs convis-api-local${NC}"
        exit 1
    fi
else
    echo -e "${GREEN}✓ Backend API is already running on http://localhost:8010${NC}"
fi

echo ""
echo -e "${GREEN}Starting frontend...${NC}"

# Navigate to frontend directory
cd convis-web

# Check if node_modules exists
if [ ! -d "node_modules" ]; then
    echo "Installing frontend dependencies (this may take a few minutes)..."
    npm install
fi

# Create .env.local if it doesn't exist
if [ ! -f ".env.local" ]; then
    echo "Creating .env.local file..."
    echo "NEXT_PUBLIC_API_URL=http://localhost:8010" > .env.local
fi

echo ""
echo -e "${GREEN}======================================"
echo "   Development Environment Ready!"
echo "======================================${NC}"
echo ""
echo "Backend API: http://localhost:8010"
echo "Frontend:    http://localhost:3000"
echo ""
echo -e "${YELLOW}Starting Next.js development server...${NC}"
echo "Press Ctrl+C to stop"
echo ""

# Start the frontend dev server (this will keep running)
npm run dev
