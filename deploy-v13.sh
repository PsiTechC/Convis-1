#!/bin/bash

# Deploy v13 to VPS
# This fixes AI stopping mid-conversation

echo "Building v13 with conversation flow fixes..."
docker build -t convis-api:v13 -f convis-api/Dockerfile convis-api

echo ""
echo "Tagging for Docker Hub..."
docker tag convis-api:v13 psittech/convis-api:v13

echo ""
echo "Pushing to Docker Hub..."
docker push psittech/convis-api:v13

echo ""
echo "✓ Image pushed to Docker Hub"
echo ""
echo "Now SSH to your VPS and run:"
echo ""
echo "  docker pull psittech/convis-api:v13"
echo "  docker stop convis-api"
echo "  docker rm convis-api"
echo "  docker run -d --name convis-api -p 8010:8000 --env-file /path/to/.env psittech/convis-api:v13"
echo ""
