# How to Create Docker Containers for Convis Project

This guide explains exactly how to create Docker containers for your Convis AI Voice Platform project.

## Prerequisites

Make sure you have:
- Docker installed (`docker --version`)
- Docker Compose installed (`docker-compose --version`)
- Your project files in: `/media/shubham/Shubham/PSITECH/Convis-main`

## Understanding the Project Structure

Your project has 3 main services:
```
Convis-main/
├── convis-api/          # Backend (FastAPI + Python)
│   ├── Dockerfile       # Instructions to build API container
│   └── requirements.txt # Python dependencies
├── convis-web/          # Frontend (Next.js + React)
│   ├── Dockerfile       # Instructions to build Web container
│   └── package.json     # Node.js dependencies
├── nginx/               # Reverse Proxy
│   └── nginx.conf       # Nginx configuration
├── docker-compose.yml   # Orchestrates all containers
└── .env                 # Environment variables
```

---

## Method 1: Create ALL Containers at Once (RECOMMENDED)

This is the simplest method - Docker Compose will build all containers automatically.

### Step 1: Navigate to Project Directory

```bash
cd /media/shubham/Shubham/PSITECH/Convis-main
```

### Step 2: Create .env File (if not exists)

```bash
# Check if .env exists
ls -la .env

# If it doesn't exist, create it:
cat > .env << 'EOF'
# MongoDB Configuration
MONGODB_URI=mongodb+srv://psitech:Psitech123@pms.ijqbdmu.mongodb.net/?retryWrites=true&w=majority
DATABASE_NAME=convis_python

# Frontend URL
FRONTEND_URL=http://localhost:3000

# API Base URL
API_BASE_URL=http://localhost:8000
BASE_URL=http://localhost:8000
NEXT_PUBLIC_API_URL=http://localhost:8000

# Encryption & Security
ENCRYPTION_KEY=xKz_4NGoARGLMXFS5pCWm1h7pj3q0Oob4sHbkCCY28E=
JWT_SECRET=iKmrSa1UltadaRffBYtsfQ+FfzkwjFWTjoKZNWgTtkU=

# Redis
REDIS_URL=redis://localhost:6379

# Twilio
TWILIO_ACCOUNT_SID=your_twilio_account_sid_here
TWILIO_AUTH_TOKEN=your_twilio_auth_token_here

# OpenAI
OPENAI_API_KEY=your_openai_api_key_here

# Google Calendar OAuth
GOOGLE_CLIENT_ID=613473789813-g12ifueq6tsd0br6dm69gvdd5qrh9ei0.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=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

# Campaign Settings
DEFAULT_TIMEZONE=Asia/Kolkata
CAMPAIGN_DISPATCH_INTERVAL_SECONDS=1
ENABLE_CALENDAR_BOOKING=true
EOF
```

### Step 3: Build All Containers

```bash
# This single command creates all 3 Docker containers
docker-compose build

# What this does:
# 1. Reads docker-compose.yml
# 2. Finds the 3 services (api, web, nginx)
# 3. Builds each container using their Dockerfile
# 4. Downloads all dependencies
# 5. Creates Docker images
```

**Expected output:**
```
Building api
[+] Building 300.5s (13/13) FINISHED
 => [1/7] FROM docker.io/library/python:3.11-slim
 => [2/7] WORKDIR /app
 => [3/7] RUN apt-get update && apt-get install...
 => [4/7] COPY requirements.txt .
 => [5/7] RUN pip install...
 => [6/7] COPY . .
 => [7/7] RUN mkdir -p uploads/knowledge_base...
 => exporting to image

Building web
[+] Building 450.2s (12/12) FINISHED
 => [deps 1/4] FROM docker.io/library/node:18-alpine
 => [deps 4/4] RUN npm install...
 => [builder 2/3] COPY . .
 => [builder 3/3] RUN npm run build...
 => exporting to image

Building nginx
[+] Building 2.1s (5/5) FINISHED
 => [1/2] FROM docker.io/library/nginx:alpine
 => [2/2] COPY nginx.conf /etc/nginx/nginx.conf
 => exporting to image
```

**This will take 10-20 minutes on first build** because it:
- Downloads base images (Python, Node.js, Nginx)
- Installs 100+ Python packages
- Installs 800+ Node.js packages
- Builds the Next.js application

### Step 4: Verify Containers Were Created

```bash
# List all Docker images
docker images

# You should see:
# REPOSITORY          TAG       IMAGE ID       CREATED          SIZE
# convis-main_web     latest    abc123def456   2 minutes ago    500MB
# convis-main_api     latest    def456ghi789   5 minutes ago    14.4GB
# convis-main_nginx   latest    ghi789jkl012   1 minute ago     50MB
```

### Step 5: Start All Containers

```bash
# Start all containers in detached mode (-d = background)
docker-compose up -d

# What this does:
# 1. Creates a network for containers to communicate
# 2. Starts API container on port 8000
# 3. Starts Web container on port 3000
# 4. Starts Nginx container on port 80
```

### Step 6: Verify Containers are Running

```bash
# Check running containers
docker-compose ps

# Expected output:
# NAME                COMMAND                  STATUS    PORTS
# convis-main_api_1   "uvicorn app.main:ap…"   Up        0.0.0.0:8000->8000/tcp
# convis-main_web_1   "node server.js"         Up        0.0.0.0:3000->3000/tcp
# convis-main_nginx_1 "nginx -g 'daemon of…"   Up        0.0.0.0:80->80/tcp
```

### Step 7: Access Your Application

- **Frontend**: http://localhost:3000
- **Backend API**: http://localhost:8000
- **API Docs**: http://localhost:8000/docs
- **Through Nginx**: http://localhost:80

---

## Method 2: Create Containers One-by-One

If you want to build containers individually (for debugging or testing):

### Build Backend (API) Container Only

```bash
cd /media/shubham/Shubham/PSITECH/Convis-main

# Build the API container
docker-compose build api

# Or build directly from Dockerfile:
cd convis-api
docker build -t convis-api:latest .

# Start just the API container
docker run -d \
  --name convis-api \
  -p 8000:8000 \
  --env-file ../.env \
  convis-api:latest

# Verify it's running
curl http://localhost:8000/health
```

### Build Frontend (Web) Container Only

```bash
cd /media/shubham/Shubham/PSITECH/Convis-main

# Build the Web container
docker-compose build web

# Or build directly from Dockerfile:
cd convis-web
docker build -t convis-web:latest .

# Start just the Web container
docker run -d \
  --name convis-web \
  -p 3000:3000 \
  --env-file ../.env \
  convis-web:latest

# Access in browser
# http://localhost:3000
```

### Build Nginx Container Only

```bash
cd /media/shubham/Shubham/PSITECH/Convis-main

# Build the Nginx container
docker-compose build nginx

# Start Nginx
docker-compose up -d nginx
```

---

## Method 3: Build and Start in One Command

The fastest way - build and start everything at once:

```bash
cd /media/shubham/Shubham/PSITECH/Convis-main

# Build and start all containers
docker-compose up -d --build

# The --build flag forces rebuilding images even if they exist
# The -d flag runs containers in background
```

---

## Understanding What Each Container Does

### 1. API Container (convis-main_api)
- **Base Image**: Python 3.11 slim
- **What it contains**:
  - FastAPI backend application
  - Python dependencies (FastAPI, MongoDB driver, AI libraries)
  - Tesseract OCR for document processing
  - System tools (curl, build-essential)
- **Port**: 8000
- **Size**: ~14.4GB (large due to AI/ML libraries)

### 2. Web Container (convis-main_web)
- **Base Image**: Node.js 18 Alpine
- **What it contains**:
  - Next.js 15 frontend application
  - React 19 components
  - Node.js dependencies
  - Compiled production build
- **Port**: 3000
- **Size**: ~500MB

### 3. Nginx Container (convis-main_nginx)
- **Base Image**: Nginx Alpine
- **What it contains**:
  - Nginx web server
  - Reverse proxy configuration
  - Routes traffic to API and Web containers
- **Port**: 80 (HTTP), 443 (HTTPS when configured)
- **Size**: ~50MB

---

## Useful Docker Commands

### View Container Logs

```bash
# All containers
docker-compose logs

# Follow logs in real-time
docker-compose logs -f

# Specific container
docker-compose logs api
docker-compose logs web
docker-compose logs nginx

# Last 100 lines
docker-compose logs --tail=100
```

### Stop Containers

```bash
# Stop all containers
docker-compose stop

# Stop specific container
docker-compose stop api
docker-compose stop web
```

### Restart Containers

```bash
# Restart all
docker-compose restart

# Restart specific
docker-compose restart api
```

### Remove Containers

```bash
# Stop and remove all containers
docker-compose down

# Remove containers and volumes (WARNING: deletes data)
docker-compose down -v

# Remove containers, volumes, and images
docker-compose down -v --rmi all
```

### Execute Commands Inside Containers

```bash
# Access API container shell
docker-compose exec api /bin/bash

# Access Web container shell
docker-compose exec web /bin/sh

# Run a command in API container
docker-compose exec api python -m pip list

# Check environment variables
docker-compose exec api env
```

### Check Container Resources

```bash
# See CPU, memory usage
docker stats

# Inspect container details
docker inspect convis-main_api_1

# Check container ports
docker port convis-main_api_1
```

### Rebuild After Code Changes

```bash
# Rebuild and restart all containers
docker-compose up -d --build

# Rebuild only one service
docker-compose build api
docker-compose up -d api
```

---

## Troubleshooting

### Build Fails - "npm install timeout"

```bash
# Increase timeout in Dockerfile
# Edit convis-web/Dockerfile line 11:
RUN npm install --network-timeout=600000
```

### Port Already in Use

```bash
# Find what's using the port
sudo lsof -i :8000
sudo lsof -i :3000

# Kill the process
kill -9 <PID>

# Or change port in docker-compose.yml
```

### Container Exits Immediately

```bash
# Check logs for errors
docker-compose logs api

# Common issues:
# - Missing environment variables
# - MongoDB connection failed
# - Port conflict
```

### Out of Disk Space

```bash
# Check disk usage
docker system df

# Clean up
docker system prune -a
docker volume prune
```

### Rebuild from Scratch

```bash
# Remove everything
docker-compose down -v --rmi all

# Remove all Docker data
docker system prune -a --volumes

# Rebuild
docker-compose up -d --build
```

---

## Summary

To create Docker containers for Convis project:

```bash
# 1. Navigate to project
cd /media/shubham/Shubham/PSITECH/Convis-main

# 2. Ensure .env file exists
ls -la .env

# 3. Build all containers (ONE COMMAND)
docker-compose build

# 4. Start all containers
docker-compose up -d

# 5. Verify they're running
docker-compose ps

# 6. Access your application
# Frontend: http://localhost:3000
# Backend: http://localhost:8000/docs
```

**That's it!** Your Docker containers are now created and running.

---

## For VPS Deployment

Once containers are working locally, deploy to VPS:

```bash
# On VPS:
1. Install Docker
2. Clone your project
3. Run: docker-compose up -d --build
4. Configure domain and SSL

See VPS_DEPLOYMENT.md for detailed instructions.
```
