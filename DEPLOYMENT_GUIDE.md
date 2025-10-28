# 🚀 Docker Deployment Guide - Convis AI Voice Platform

Complete guide to containerize and deploy your application on a VPS server.

---

## 📋 Prerequisites

### On Your Local Machine
- Docker installed (version 20.10+)
- Docker Compose installed (version 2.0+)
- Git (to push code to VPS)

### On VPS Server
- Ubuntu 20.04+ / Debian 11+ / CentOS 8+
- Minimum 4GB RAM, 2 CPU cores
- 40GB+ disk space
- Root or sudo access
- Domain name (optional, for SSL)

---

## Part 1: Create Docker Container (Local Testing)

### Step 1: Create Environment File

Create `.env` file in the root directory:

```bash
cd /media/shubham/Shubham/PSITECH/Convis-main
nano .env
```

Add the following (replace with your actual values):

```env
# Database
MONGODB_URI=mongodb+srv://psitech:Psitech123@pms.ijqbdmu.mongodb.net/convis_python

# Security
JWT_SECRET=your-super-secret-jwt-key-change-this-in-production-min-32-chars
ENCRYPTION_KEY=your-encryption-key-exactly-32-characters-long

# API Keys
OPENAI_API_KEY=sk-your-openai-api-key-here
TWILIO_ACCOUNT_SID=ACxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
TWILIO_AUTH_TOKEN=your-twilio-auth-token

# URLs (for local testing)
API_BASE_URL=http://localhost:8000
NEXT_PUBLIC_API_URL=http://localhost:8000

# Redis
REDIS_URL=redis://localhost:6379

# Campaign Settings
CAMPAIGN_DISPATCH_INTERVAL_SECONDS=1
DEFAULT_TIMEZONE=Asia/Kolkata

# Base URL for webhooks (update for production)
BASE_URL=http://localhost:8000
```

**Save and exit** (Ctrl+X, then Y, then Enter)

### Step 2: Build Docker Containers

```bash
# Navigate to project directory
cd /media/shubham/Shubham/PSITECH/Convis-main

# Build all containers
docker-compose build

# This will take 5-10 minutes on first run
```

### Step 3: Start Containers

```bash
# Start all services
docker-compose up -d

# Check if containers are running
docker-compose ps
```

You should see:
```
NAME            STATUS          PORTS
convis-api      Up              0.0.0.0:8000->8000/tcp
convis-web      Up              0.0.0.0:3000->3000/tcp
convis-nginx    Up              0.0.0.0:80->80/tcp, 0.0.0.0:443->443/tcp
```

### Step 4: Verify Deployment

```bash
# Check backend health
curl http://localhost:8000/health

# Check frontend
curl http://localhost:3000

# View logs
docker-compose logs -f api    # Backend logs
docker-compose logs -f web    # Frontend logs
```

### Step 5: Access Application

Open browser:
- Frontend: http://localhost:3000
- Backend API: http://localhost:8000
- API Docs: http://localhost:8000/docs

### Step 6: Stop Containers (when done testing)

```bash
# Stop all containers
docker-compose down

# Stop and remove all data (volumes)
docker-compose down -v
```

---

## Part 2: Deploy to VPS Server

### Step 1: Prepare VPS Server

#### 1.1 Connect to VPS

```bash
# From your local machine
ssh root@your-vps-ip-address
# Or
ssh username@your-vps-ip-address
```

#### 1.2 Update System

```bash
sudo apt update
sudo apt upgrade -y
```

#### 1.3 Install Docker

```bash
# Install Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh

# Add your user to docker group (optional, to run without sudo)
sudo usermod -aG docker $USER

# Install Docker Compose
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose

# Verify installation
docker --version
docker-compose --version
```

#### 1.4 Install Git (if not installed)

```bash
sudo apt install git -y
```

### Step 2: Transfer Code to VPS

**Option A: Using Git (Recommended)**

```bash
# On VPS server
cd /home/username  # or wherever you want to deploy

# Clone your repository
git clone https://github.com/your-username/Convis-main.git
cd Convis-main
```

**Option B: Using SCP (Direct Transfer)**

```bash
# From your local machine
scp -r /media/shubham/Shubham/PSITECH/Convis-main root@your-vps-ip:/home/convis/

# Then SSH into VPS
ssh root@your-vps-ip
cd /home/convis/Convis-main
```

**Option C: Using rsync (Recommended for updates)**

```bash
# From your local machine
rsync -avz --progress /media/shubham/Shubham/PSITECH/Convis-main/ root@your-vps-ip:/home/convis/Convis-main/
```

### Step 3: Configure Production Environment

#### 3.1 Create Production .env File

```bash
# On VPS server
cd /home/convis/Convis-main
nano .env
```

Update these values for production:

```env
# Database (same as before)
MONGODB_URI=mongodb+srv://psitech:Psitech123@pms.ijqbdmu.mongodb.net/convis_python

# Security - CHANGE THESE!
JWT_SECRET=CHANGE-THIS-TO-A-STRONG-RANDOM-STRING-MIN-32-CHARS
ENCRYPTION_KEY=CHANGE-THIS-EXACTLY-32-CHARS!!

# API Keys (same as before)
OPENAI_API_KEY=sk-your-openai-api-key
TWILIO_ACCOUNT_SID=ACxxxxxxxxxxxxx
TWILIO_AUTH_TOKEN=your-twilio-token

# URLs - UPDATE TO YOUR DOMAIN
API_BASE_URL=https://api.yourdomain.com
NEXT_PUBLIC_API_URL=https://api.yourdomain.com
BASE_URL=https://api.yourdomain.com

# Redis
REDIS_URL=redis://localhost:6379

# Settings
CAMPAIGN_DISPATCH_INTERVAL_SECONDS=1
DEFAULT_TIMEZONE=Asia/Kolkata
```

**Important Security Notes:**
1. Generate strong JWT_SECRET: `openssl rand -hex 32`
2. Generate ENCRYPTION_KEY: `openssl rand -hex 16` (must be exactly 32 chars)

#### 3.2 Secure the .env file

```bash
chmod 600 .env
```

### Step 4: Install Redis (Required for Campaign Scheduler)

```bash
# Install Redis
sudo apt install redis-server -y

# Enable Redis to start on boot
sudo systemctl enable redis-server

# Start Redis
sudo systemctl start redis-server

# Verify Redis is running
redis-cli ping
# Should return: PONG
```

### Step 5: Build and Start Containers on VPS

```bash
# Build containers
docker-compose build --no-cache

# Start in detached mode
docker-compose up -d

# Check status
docker-compose ps

# View logs
docker-compose logs -f
```

### Step 6: Configure Firewall

```bash
# Allow HTTP and HTTPS
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw allow 22/tcp  # SSH (important!)

# Enable firewall
sudo ufw enable

# Check status
sudo ufw status
```

### Step 7: Setup Domain and SSL (Optional but Recommended)

#### 7.1 Point Domain to VPS

In your domain registrar (GoDaddy, Namecheap, etc.):
- Add A record: `@` → `your-vps-ip`
- Add A record: `api` → `your-vps-ip`
- Add A record: `www` → `your-vps-ip`

Wait 5-10 minutes for DNS propagation.

#### 7.2 Install Certbot for SSL

```bash
# Install Certbot
sudo apt install certbot python3-certbot-nginx -y

# Get SSL certificate
sudo certbot --nginx -d yourdomain.com -d www.yourdomain.com -d api.yourdomain.com

# Certbot will automatically configure Nginx
# Choose option 2 (redirect HTTP to HTTPS)
```

#### 7.3 Auto-renew SSL Certificate

```bash
# Test renewal
sudo certbot renew --dry-run

# Certbot automatically sets up a cron job for renewal
```

### Step 8: Update Nginx Configuration (If needed)

```bash
# Edit nginx config
nano /home/convis/Convis-main/nginx/nginx.conf
```

Make sure it has:

```nginx
server {
    listen 80;
    server_name yourdomain.com www.yourdomain.com;

    # Frontend
    location / {
        proxy_pass http://web:3000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_cache_bypass $http_upgrade;
    }

    # Backend API
    location /api/ {
        proxy_pass http://api:8000/api/;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_cache_bypass $http_upgrade;
    }

    # WebSocket support
    location /ws/ {
        proxy_pass http://api:8000/ws/;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "Upgrade";
        proxy_set_header Host $host;
    }
}
```

Restart containers:

```bash
docker-compose restart nginx
```

---

## 🔧 Maintenance Commands

### View Logs

```bash
# All logs
docker-compose logs -f

# Specific service
docker-compose logs -f api
docker-compose logs -f web
docker-compose logs -f nginx

# Last 100 lines
docker-compose logs --tail=100 api
```

### Restart Services

```bash
# Restart all
docker-compose restart

# Restart specific service
docker-compose restart api
docker-compose restart web
```

### Update Application

```bash
# Pull latest code
cd /home/convis/Convis-main
git pull origin main  # or rsync from local

# Rebuild and restart
docker-compose down
docker-compose build --no-cache
docker-compose up -d
```

### Check Resource Usage

```bash
# Container stats
docker stats

# Disk usage
docker system df

# Clean up unused images
docker system prune -a
```

### Backup Database

```bash
# Since you're using MongoDB Atlas, backups are automatic
# But you can export data:
mongodump --uri="mongodb+srv://psitech:Psitech123@pms.ijqbdmu.mongodb.net/convis_python" --out=/backup/$(date +%Y%m%d)
```

---

## 🐛 Troubleshooting

### Container Won't Start

```bash
# Check logs
docker-compose logs api

# Check if port is already in use
sudo netstat -tulpn | grep :8000

# Rebuild from scratch
docker-compose down -v
docker-compose build --no-cache
docker-compose up -d
```

### Can't Access Application

```bash
# Check if containers are running
docker-compose ps

# Check firewall
sudo ufw status

# Check nginx logs
docker-compose logs nginx

# Test direct backend access
curl http://localhost:8000/health
```

### Database Connection Issues

```bash
# Test MongoDB connection from VPS
mongo "mongodb+srv://psitech:Psitech123@pms.ijqbdmu.mongodb.net/convis_python"

# Check if MongoDB allows your VPS IP
# Go to MongoDB Atlas → Network Access → Add IP Address
```

### Redis Connection Issues

```bash
# Check if Redis is running
sudo systemctl status redis-server

# Test Redis
redis-cli ping

# Restart Redis
sudo systemctl restart redis-server
```

---

## 📊 Monitoring

### Setup Basic Monitoring

```bash
# Install htop for system monitoring
sudo apt install htop -y

# Run htop
htop
```

### Monitor Docker Containers

```bash
# Watch container stats in real-time
watch docker stats
```

### Check Application Health

```bash
# Create health check script
nano ~/check-health.sh
```

Add:

```bash
#!/bin/bash
echo "Checking backend health..."
curl -s http://localhost:8000/health | jq

echo -e "\nChecking frontend..."
curl -s -o /dev/null -w "%{http_code}" http://localhost:3000
echo ""
```

Make executable:

```bash
chmod +x ~/check-health.sh
./check-health.sh
```

---

## 🎯 Production Checklist

Before going live:

- [ ] Changed JWT_SECRET to production value
- [ ] Changed ENCRYPTION_KEY to production value
- [ ] Updated BASE_URL to production domain
- [ ] Configured domain DNS records
- [ ] Installed SSL certificate
- [ ] Configured firewall (ports 80, 443, 22)
- [ ] Verified MongoDB Atlas allows VPS IP
- [ ] Redis is running on VPS
- [ ] Tested all application features
- [ ] Backup strategy in place
- [ ] Monitoring setup complete

---

## 📞 Support

### Common Commands Quick Reference

```bash
# Start application
docker-compose up -d

# Stop application
docker-compose down

# Restart application
docker-compose restart

# View logs
docker-compose logs -f

# Update application
git pull && docker-compose down && docker-compose build && docker-compose up -d

# Check health
curl http://localhost:8000/health
```

---

**Deployment Guide Version**: 1.0
**Last Updated**: 2025-10-28
**Platform**: Docker + VPS
**Status**: Production Ready ✅
