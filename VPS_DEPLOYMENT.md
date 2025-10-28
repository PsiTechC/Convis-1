# Convis AI Voice Platform - VPS Deployment Guide

## Prerequisites on VPS

Your VPS should have:
- Ubuntu 20.04 or later (or Debian 11+)
- Minimum 4GB RAM (8GB recommended)
- 50GB disk space
- Root or sudo access

## Step 1: Install Docker on VPS

```bash
# Update system
sudo apt-get update
sudo apt-get upgrade -y

# Install Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh

# Add your user to docker group (replace 'your-username')
sudo usermod -aG docker $USER

# Install Docker Compose
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose

# Verify installation
docker --version
docker-compose --version

# Logout and login again for group changes to take effect
```

## Step 2: Transfer Project to VPS

### Option A: Using Git (Recommended)

```bash
# On VPS
cd /home/your-username
git clone https://your-repository-url.git
cd Convis-main
```

### Option B: Using SCP

```bash
# On your local machine
cd /media/shubham/Shubham/PSITECH
tar -czf convis.tar.gz Convis-main/
scp convis.tar.gz your-username@your-vps-ip:/home/your-username/

# On VPS
cd /home/your-username
tar -xzf convis.tar.gz
cd Convis-main
```

## Step 3: Configure Environment Variables

```bash
# On VPS
cd /home/your-username/Convis-main

# Edit .env file with your production values
nano .env
```

Update these important values in `.env`:
```env
# MongoDB - Use your MongoDB Atlas connection string
MONGODB_URI=mongodb+srv://psitech:Psitech123@pms.ijqbdmu.mongodb.net/?retryWrites=true&w=majority
DATABASE_NAME=convis_python

# Frontend URL - Use your domain or VPS IP
FRONTEND_URL=http://your-vps-ip:3000

# API Base URL - Use your domain or VPS IP
API_BASE_URL=http://your-vps-ip:8000
BASE_URL=http://your-vps-ip:8000
NEXT_PUBLIC_API_URL=http://your-vps-ip:8000

# Security Keys (IMPORTANT: Change these!)
ENCRYPTION_KEY=xKz_4NGoARGLMXFS5pCWm1h7pj3q0Oob4sHbkCCY28E=
JWT_SECRET=iKmrSa1UltadaRffBYtsfQ+FfzkwjFWTjoKZNWgTtkU=

# Redis
REDIS_URL=redis://localhost:6379

# Twilio (Get from Twilio Dashboard)
TWILIO_ACCOUNT_SID=your_actual_twilio_sid
TWILIO_AUTH_TOKEN=your_actual_twilio_token

# OpenAI (Get from OpenAI Platform)
OPENAI_API_KEY=your_actual_openai_key

# Google Calendar OAuth (Already configured)
GOOGLE_CLIENT_ID=613473789813-g12ifueq6tsd0br6dm69gvdd5qrh9ei0.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=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

# Campaign Settings
DEFAULT_TIMEZONE=Asia/Kolkata
CAMPAIGN_DISPATCH_INTERVAL_SECONDS=1
ENABLE_CALENDAR_BOOKING=true
```

## Step 4: Build and Start Docker Containers

```bash
# On VPS
cd /home/your-username/Convis-main

# Build and start all services
docker-compose up -d --build

# This will take 10-15 minutes on first run
# Monitor progress:
docker-compose logs -f
```

## Step 5: Verify Deployment

```bash
# Check if all containers are running
docker-compose ps

# Should show 3 services:
# - convis-main_api_1
# - convis-main_web_1
# - convis-main_nginx_1

# Test backend API
curl http://localhost:8000/health

# View logs
docker-compose logs api
docker-compose logs web
docker-compose logs nginx
```

## Step 6: Configure Firewall

```bash
# Allow HTTP, HTTPS, and SSH
sudo ufw allow 22/tcp
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw allow 3000/tcp
sudo ufw allow 8000/tcp
sudo ufw enable

# Check status
sudo ufw status
```

## Step 7: Access Your Application

### Temporary Access (without domain):
- Frontend: `http://your-vps-ip:3000`
- Backend API: `http://your-vps-ip:8000`
- API Docs: `http://your-vps-ip:8000/docs`

### With Domain (Recommended):

1. **Point your domain to VPS**:
   - Add A record: `@` → `your-vps-ip`
   - Add A record: `www` → `your-vps-ip`
   - Add A record: `api` → `your-vps-ip`

2. **Install SSL Certificate** (after DNS propagation):

```bash
# Install Certbot
sudo apt-get install certbot python3-certbot-nginx -y

# Get SSL certificate (replace with your domain)
sudo certbot --nginx -d yourdomain.com -d www.yourdomain.com -d api.yourdomain.com

# Certificate will auto-renew
```

3. **Update Nginx Configuration**:

Edit `nginx/nginx.conf` to use your domain:
```nginx
server {
    listen 80;
    server_name yourdomain.com www.yourdomain.com;

    location / {
        proxy_pass http://web:3000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_cache_bypass $http_upgrade;
    }
}

server {
    listen 80;
    server_name api.yourdomain.com;

    location / {
        proxy_pass http://api:8000;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    }
}
```

Then restart:
```bash
docker-compose restart nginx
```

## Useful Commands

### View Logs
```bash
# All services
docker-compose logs -f

# Specific service
docker-compose logs -f api
docker-compose logs -f web
docker-compose logs -f nginx
```

### Restart Services
```bash
# All services
docker-compose restart

# Specific service
docker-compose restart api
docker-compose restart web
```

### Update Application
```bash
# Pull latest code
git pull origin main

# Rebuild and restart
docker-compose down
docker-compose up -d --build
```

### Stop/Start
```bash
# Stop all services
docker-compose down

# Start all services
docker-compose up -d

# Stop and remove all data (WARNING: deletes volumes)
docker-compose down -v
```

### Monitor Resources
```bash
# Check Docker stats
docker stats

# Check disk usage
docker system df

# Clean up unused resources
docker system prune -a
```

## Troubleshooting

### Container won't start
```bash
# Check logs
docker-compose logs api
docker-compose logs web

# Check container status
docker-compose ps

# Restart container
docker-compose restart api
```

### Port already in use
```bash
# Find what's using the port
sudo lsof -i :8000
sudo lsof -i :3000

# Kill the process
sudo kill -9 <PID>
```

### Out of disk space
```bash
# Check disk usage
df -h

# Clean Docker
docker system prune -a -f
docker volume prune -f
```

### MongoDB connection issues
- Verify MONGODB_URI in `.env`
- Check if MongoDB Atlas allows connections from your VPS IP
- Go to MongoDB Atlas → Network Access → Add IP Address → Add your VPS IP

### Can't access from browser
- Check firewall: `sudo ufw status`
- Verify containers are running: `docker-compose ps`
- Check nginx logs: `docker-compose logs nginx`

## Production Checklist

- [ ] MongoDB Atlas IP whitelist includes VPS IP
- [ ] Changed default JWT_SECRET and ENCRYPTION_KEY
- [ ] Added real Twilio credentials
- [ ] Added real OpenAI API key
- [ ] Configured domain and SSL certificate
- [ ] Set up backups for MongoDB
- [ ] Enabled Docker logging
- [ ] Set up monitoring (optional: Grafana, Prometheus)
- [ ] Configured automated Docker restart on failure
- [ ] Set up log rotation

## Security Best Practices

1. **Change default credentials** in `.env`
2. **Use SSL/TLS** (HTTPS) in production
3. **Keep Docker updated**: `sudo apt-get update && sudo apt-get upgrade`
4. **Limit SSH access**: Only allow key-based authentication
5. **Regular backups**: Backup MongoDB and application data
6. **Monitor logs**: Check for suspicious activity
7. **Use secrets management**: Consider using Docker secrets or HashiCorp Vault

## Support

If you encounter issues:
1. Check logs: `docker-compose logs -f`
2. Verify environment variables in `.env`
3. Check MongoDB Atlas connection
4. Ensure all ports are open in firewall
5. Verify DNS settings if using a domain

---

**Your application will be accessible at:**
- Frontend: http://your-vps-ip:3000 (or https://yourdomain.com)
- Backend: http://your-vps-ip:8000 (or https://api.yourdomain.com)
- API Docs: http://your-vps-ip:8000/docs
