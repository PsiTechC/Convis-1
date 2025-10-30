#!/bin/bash

# Deploy fixes for Twilio call disconnection issues

set -e

echo "🔧 Deploying Twilio Call Fixes"
echo "================================"
echo ""

# Check if we're in the right directory
if [ ! -f "docker-compose.yml" ]; then
    echo "❌ Error: docker-compose.yml not found!"
    echo "Please run this script from the project root directory."
    exit 1
fi

echo "📋 Changes being deployed:"
echo "1. Fixed WebSocket URL generation in webhooks (uses API_BASE_URL)"
echo "2. Added nginx configuration for outbound call WebSocket support"
echo "3. Updated environment variables"
echo ""

# Check current environment
echo "Current environment configuration:"
echo "-----------------------------------"
grep "^API_BASE_URL=" .env 2>/dev/null || echo "API_BASE_URL: Not set"
grep "^FRONTEND_URL=" .env 2>/dev/null || echo "FRONTEND_URL: Not set"
echo ""

# Ask for confirmation
read -p "Do you want to proceed with deployment? (y/n) " -n 1 -r
echo ""
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Deployment cancelled."
    exit 0
fi

echo ""
echo "🔄 Step 1: Stopping services..."
docker-compose down

echo ""
echo "🔨 Step 2: Rebuilding API container..."
docker-compose build --no-cache api

echo ""
echo "🚀 Step 3: Starting services..."
docker-compose up -d

echo ""
echo "⏳ Step 4: Waiting for services to start..."
sleep 10

echo ""
echo "🔍 Step 5: Checking service health..."
docker-compose ps

echo ""
echo "📋 Step 6: Checking API logs..."
docker logs convis-api --tail 20

echo ""
echo "✅ Deployment complete!"
echo ""
echo "📝 Next steps:"
echo "1. Test an inbound call to verify WebSocket connection"
echo "2. Test an outbound/campaign call"
echo "3. Check logs if issues persist: docker logs convis-api -f"
echo ""
echo "🔗 Key endpoints:"
echo "   - Health: https://api.convis.ai/health"
echo "   - Voice Webhook: https://api.convis.ai/api/twilio-webhooks/voice"
echo "   - Outbound Webhook: https://api.convis.ai/api/twilio-webhooks/outbound-call"
echo ""
echo "💡 Tip: Check WebSocket connections with:"
echo "   docker logs convis-api | grep -i websocket"
