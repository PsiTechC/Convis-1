#!/bin/bash

# Helper script to switch between development and production environments

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

usage() {
    echo "Usage: $0 [local|production]"
    echo ""
    echo "Switches environment configuration for Convis project"
    echo ""
    echo "Options:"
    echo "  local       - Switch to local development environment (with ngrok)"
    echo "  production  - Switch to production environment (VPS)"
    echo ""
    echo "Examples:"
    echo "  $0 local"
    echo "  $0 production"
    exit 1
}

if [ $# -eq 0 ]; then
    usage
fi

ENV=$1

case $ENV in
    local|dev|development)
        echo "📦 Switching to LOCAL DEVELOPMENT environment..."

        if [ ! -f .env.local ]; then
            echo "❌ Error: .env.local file not found!"
            exit 1
        fi

        cp .env.local .env
        echo "✅ Copied .env.local to .env"
        echo ""
        echo "⚠️  IMPORTANT: Update your ngrok URL in .env!"
        echo ""
        echo "Steps:"
        echo "1. Start ngrok: ngrok http 8000"
        echo "2. Copy the ngrok URL (e.g., https://abc123.ngrok-free.dev)"
        echo "3. Edit .env and update API_BASE_URL with your ngrok URL"
        echo "4. Restart: docker-compose down && docker-compose up -d"
        echo "5. Update Twilio webhook URLs to use ngrok URL"
        echo ""
        ;;

    production|prod)
        echo "🚀 Switching to PRODUCTION environment..."

        if [ ! -f .env.production ]; then
            echo "❌ Error: .env.production file not found!"
            exit 1
        fi

        cp .env.production .env
        echo "✅ Copied .env.production to .env"
        echo ""
        echo "📋 Checklist:"
        echo "1. Deploy to VPS: docker-compose up -d"
        echo "2. Verify API: curl https://api.convis.ai/health"
        echo "3. Update Twilio webhooks to: https://api.convis.ai/api/twilio-webhooks/voice"
        echo "4. Assign AI assistants to phone numbers in dashboard"
        echo ""
        ;;

    *)
        echo "❌ Error: Unknown environment '$ENV'"
        echo ""
        usage
        ;;
esac

echo "Current API_BASE_URL:"
grep "^API_BASE_URL=" .env || echo "Not set"
echo ""
echo "Current FRONTEND_URL:"
grep "^FRONTEND_URL=" .env || echo "Not set"
