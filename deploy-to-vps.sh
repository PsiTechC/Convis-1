#!/bin/bash

# Deployment script for VPS (using ports 8010 and 3010)
# This script builds and pushes Docker images, then provides the run commands

set -e

echo "🚀 Convis VPS Deployment Script"
echo "================================"
echo ""
echo "This will:"
echo "1. Build Docker images with the latest code (including WebSocket fixes)"
echo "2. Tag them as v2"
echo "3. Push to Docker Hub"
echo "4. Provide commands to run on your VPS"
echo ""

# Check if we're in the right directory
if [ ! -f "docker-compose.yml" ]; then
    echo "❌ Error: docker-compose.yml not found!"
    echo "Please run this script from the project root directory."
    exit 1
fi

# Check if logged into Docker Hub
if ! docker info | grep -q "Username"; then
    echo "⚠️  Warning: You may not be logged into Docker Hub"
    echo "Run: docker login"
    read -p "Continue anyway? (y/n) " -n 1 -r
    echo ""
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 0
    fi
fi

echo ""
echo "📦 Step 1: Building API image..."
cd convis-api
docker build -t psittech/convis-api:v2 -t psittech/convis-api:latest .
cd ..

echo ""
echo "📦 Step 2: Building Web image..."
cd convis-web
docker build -t psittech/convis-web:v2 -t psittech/convis-web:latest .
cd ..

echo ""
echo "☁️  Step 3: Pushing images to Docker Hub..."
docker push psittech/convis-api:v2
docker push psittech/convis-api:latest
docker push psittech/convis-web:v2
docker push psittech/convis-web:latest

echo ""
echo "✅ Images built and pushed successfully!"
echo ""
echo "================================================"
echo "📋 COMMANDS TO RUN ON YOUR VPS"
echo "================================================"
echo ""
echo "1️⃣  Stop and remove old containers:"
echo ""
cat << 'EOF'
docker stop $(docker ps -q --filter ancestor=psittech/convis-api:v1) 2>/dev/null || true
docker stop $(docker ps -q --filter ancestor=psittech/convis-web:v1) 2>/dev/null || true
docker rm $(docker ps -aq --filter ancestor=psittech/convis-api:v1) 2>/dev/null || true
docker rm $(docker ps -aq --filter ancestor=psittech/convis-web:v1) 2>/dev/null || true
EOF

echo ""
echo "2️⃣  Pull new images:"
echo ""
cat << 'EOF'
docker pull psittech/convis-api:v2
docker pull psittech/convis-web:v2
EOF

echo ""
echo "3️⃣  Run API container (port 8010):"
echo ""
cat << 'EOF'
docker run -d \
  --name convis-api \
  --restart unless-stopped \
  -p 8010:8000 \
  -e MONGODB_URI='mongodb+srv://psitech:Psitech123@pms.ijqbdmu.mongodb.net/?retryWrites=true&w=majority' \
  -e DATABASE_NAME='convis_python' \
  -e EMAIL_USER='no-reply@convis.ai' \
  -e EMAIL_PASS='Test@2025' \
  -e SMTP_HOST='p1432.use1.mysecurecloudhost.com' \
  -e SMTP_PORT='465' \
  -e SMTP_USE_SSL='true' \
  -e FRONTEND_URL='https://webapp.convis.ai' \
  -e API_BASE_URL='https://api.convis.ai' \
  -e BASE_URL='https://api.convis.ai' \
  -e CORS_ORIGINS='https://webapp.convis.ai,https://api.convis.ai,http://localhost:3000' \
  -e ENCRYPTION_KEY='xKz_4NGoARGLMXFS5pCWm1h7pj3q0Oob4sHbkCCY28E=' \
  -e JWT_SECRET='iKmrSa1UltadaRffBYtsfQ+FfzkwjFWTjoKZNWgTtkU=' \
  -e REDIS_URL='redis://redis-10185.c258.us-east-1-4.ec2.redns.redis-cloud.com:10185' \
  -e OUTBOUND_TWIML_URL='https://api.convis.ai/api/twilio-webhooks/outbound-call' \
  -e TW_STATUS_CALLBACK='https://api.convis.ai/api/twilio-webhooks/call-status' \
  -e TW_RECORDING_CALLBACK='https://api.convis.ai/api/twilio-webhooks/recording' \
  -e GOOGLE_CLIENT_ID='613473789813-g12ifueq6tsd0br6dm69gvdd5qrh9ei0.apps.googleusercontent.com' \
  -e GOOGLE_CLIENT_SECRET='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' \
  -e GOOGLE_REDIRECT_URI='https://api.convis.ai/api/calendar/google/callback' \
  -e DEFAULT_TIMEZONE='Asia/Kolkata' \
  -e DEFAULT_MAX_ATTEMPTS='3' \
  -e DEFAULT_RETRY_DELAYS='15,60,1440' \
  -e ENABLE_CALENDAR_BOOKING='true' \
  -e ENABLE_POST_CALL_AI='true' \
  -e ENABLE_AUTO_RETRY='true' \
  -e CAMPAIGN_DISPATCH_INTERVAL_SECONDS='1' \
  -e ENVIRONMENT='production' \
  psittech/convis-api:v2
EOF

echo ""
echo "4️⃣  Run Web container (port 3010):"
echo ""
cat << 'EOF'
docker run -d \
  --name convis-web \
  --restart unless-stopped \
  -p 3010:3000 \
  -e NEXT_PUBLIC_API_URL='https://api.convis.ai' \
  -e NODE_ENV='production' \
  psittech/convis-web:v2
EOF

echo ""
echo "5️⃣  Check containers are running:"
echo ""
cat << 'EOF'
docker ps | grep convis
EOF

echo ""
echo "6️⃣  Check API health:"
echo ""
cat << 'EOF'
curl http://localhost:8010/health
EOF

echo ""
echo "7️⃣  Check logs if needed:"
echo ""
cat << 'EOF'
docker logs convis-api --tail 50
docker logs convis-web --tail 50
EOF

echo ""
echo "================================================"
echo "✅ Deployment instructions ready!"
echo ""
echo "Copy the commands above and run them on your VPS."
echo ""
echo "⚠️  Important: Make sure your nginx/reverse proxy on VPS"
echo "    is configured to forward:"
echo "    - https://api.convis.ai → localhost:8010"
echo "    - https://webapp.convis.ai → localhost:3010"
echo ""
echo "    And supports WebSocket connections for:"
echo "    - wss://api.convis.ai/api/inbound-calls/media-stream/*"
echo "    - wss://api.convis.ai/api/outbound-calls/media-stream/*"
echo ""
