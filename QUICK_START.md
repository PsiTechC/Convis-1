# ⚡ Quick Start - Docker Deployment

## 🚀 Deploy in 5 Minutes

### Step 1: Create .env File (30 seconds)

```bash
cd /path/to/Convis-main
nano .env
```

Paste this (replace YOUR_VALUES):

```env
MONGODB_URI=mongodb+srv://psitech:Psitech123@pms.ijqbdmu.mongodb.net/convis_python
JWT_SECRET=YOUR-32-CHAR-SECRET-HERE
ENCRYPTION_KEY=YOUR-EXACTLY-32-CHARS-KEY!
OPENAI_API_KEY=sk-YOUR-KEY
TWILIO_ACCOUNT_SID=ACXXXXXXX
TWILIO_AUTH_TOKEN=YOUR-TOKEN
API_BASE_URL=http://localhost:8000
NEXT_PUBLIC_API_URL=http://localhost:8000
REDIS_URL=redis://localhost:6379
BASE_URL=http://localhost:8000
CAMPAIGN_DISPATCH_INTERVAL_SECONDS=1
DEFAULT_TIMEZONE=Asia/Kolkata
```

### Step 2: Start Application (2 minutes)

```bash
# Build and start
docker-compose up -d --build

# Check status
docker-compose ps
```

### Step 3: Access

- Frontend: http://localhost:3000
- Backend: http://localhost:8000/docs

Done! 🎉

---

## 🌐 Deploy to VPS

### On VPS Server:

```bash
# 1. Install Docker
curl -fsSL https://get.docker.com | sh
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose

# 2. Install Redis
sudo apt install redis-server -y
sudo systemctl start redis-server

# 3. Transfer code (from local machine)
rsync -avz /media/shubham/Shubham/PSITECH/Convis-main/ root@YOUR_VPS_IP:/home/convis/

# 4. On VPS: Create .env with production values
cd /home/convis
nano .env  # Update URLs to your domain

# 5. Start
docker-compose up -d --build

# 6. Configure firewall
sudo ufw allow 80
sudo ufw allow 443
sudo ufw allow 22
sudo ufw enable
```

Done! Your app is live at http://YOUR_VPS_IP 🚀

---

## 🔧 Essential Commands

```bash
# Start
docker-compose up -d

# Stop
docker-compose down

# Restart
docker-compose restart

# Logs
docker-compose logs -f

# Update code
git pull && docker-compose down && docker-compose up -d --build

# Clean rebuild
docker-compose down -v
docker-compose build --no-cache
docker-compose up -d
```

---

## 📝 Production Checklist

Before going live:
- [ ] Change JWT_SECRET (generate: `openssl rand -hex 32`)
- [ ] Change ENCRYPTION_KEY (generate: `openssl rand -hex 16`)
- [ ] Update all URLs to your domain
- [ ] Point domain DNS to VPS IP
- [ ] Install SSL: `sudo certbot --nginx -d yourdomain.com`
- [ ] Allow VPS IP in MongoDB Atlas Network Access

That's it! ✅
