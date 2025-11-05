# Local Development Guide - Convis

Complete guide to run the Convis project locally before deployment.

## Prerequisites

### Required Software
- **Node.js** (v18 or higher) - For Next.js frontend
- **Python** (v3.11) - For FastAPI backend
- **Docker** (optional but recommended) - For containerized backend
- **MongoDB Atlas** account - Database (already configured)

### Check Your System
```bash
# Check Node.js version
node --version  # Should be v18+

# Check Python version
python3 --version  # Should be 3.11+

# Check Docker (optional)
docker --version
```

---

## Part 1: Backend (FastAPI API)

### Option A: Run with Docker (Recommended)

1. **Navigate to project root:**
```bash
cd /media/shubham/Shubham/PSITECH/Convis-main
```

2. **Make sure .env file exists:**
```bash
ls convis-api/.env
```

3. **Build the Docker image:**
```bash
docker build -t convis-api:local -f convis-api/Dockerfile convis-api
```

4. **Run the container:**
```bash
docker run -d \
  --name convis-api-local \
  -p 8010:8000 \
  --env-file convis-api/.env \
  convis-api:local
```

5. **Check if running:**
```bash
docker logs --tail 50 convis-api-local
```

6. **Test the API:**
```bash
curl http://localhost:8010/health
```

You should see: `{"status":"healthy"}`

### Option B: Run with Python Virtual Environment

1. **Navigate to API directory:**
```bash
cd /media/shubham/Shubham/PSITECH/Convis-main/convis-api
```

2. **Create virtual environment:**
```bash
python3 -m venv venv
source venv/bin/activate
```

3. **Install dependencies:**
```bash
pip install --upgrade pip
pip install -r requirements.txt
```

4. **Load environment variables:**
```bash
export $(cat .env | xargs)
```

5. **Run the API:**
```bash
uvicorn app.main:app --host 0.0.0.0 --port 8010 --reload
```

6. **Test the API:**
```bash
curl http://localhost:8010/health
```

---

## Part 2: Frontend (Next.js Web App)

1. **Open a NEW terminal window**

2. **Navigate to web directory:**
```bash
cd /media/shubham/Shubham/PSITECH/Convis-main/convis-web
```

3. **Install dependencies (first time only):**
```bash
npm install
```

4. **Create .env.local file if it doesn't exist:**
```bash
cat > .env.local << 'EOF'
NEXT_PUBLIC_API_URL=http://localhost:8010
EOF
```

5. **Run the development server:**
```bash
npm run dev
```

6. **Open browser:**
```
http://localhost:3000
```

You should see the Convis login page!

---

## Part 3: Verify Everything Works

### Check Backend API
```bash
# Health check
curl http://localhost:8010/health

# Check MongoDB connection
curl http://localhost:8010/api/health/db
```

### Check Frontend
1. Open browser to `http://localhost:3000`
2. You should see the login page
3. Try logging in with your credentials

### Check Logs
```bash
# Backend logs (Docker)
docker logs -f convis-api-local

# Backend logs (Python)
# Already visible in the terminal where you ran uvicorn

# Frontend logs
# Already visible in the terminal where you ran npm run dev
```

---

## Common Issues & Solutions

### Issue 1: Port Already in Use
```bash
# Find what's using port 8010
lsof -i :8010

# Kill the process
kill -9 <PID>

# Or use different port
docker run -p 8011:8000 ...
```

### Issue 2: MongoDB Connection Error
- Check your `.env` file has correct `MONGODB_URI`
- Verify MongoDB Atlas IP whitelist includes your IP
- Test connection: `mongosh "your-mongodb-uri"`

### Issue 3: API Keys Missing
```bash
# Check if API keys are set
docker exec convis-api-local printenv | grep API_KEY
```

Make sure these are in your `.env`:
- `OPENAI_API_KEY`
- `DEEPGRAM_API_KEY`
- `CARTESIA_API_KEY`
- `ELEVENLABS_API_KEY`

### Issue 4: Frontend Can't Connect to Backend
- Make sure backend is running on port 8010
- Check `convis-web/.env.local` has correct `NEXT_PUBLIC_API_URL`
- Disable browser extensions that might block localhost

### Issue 5: Docker Build Fails
```bash
# Clear Docker cache and rebuild
docker system prune -a
docker build --no-cache -t convis-api:local convis-api/
```

---

## Development Workflow

### 1. Start Backend (Terminal 1)
```bash
cd /media/shubham/Shubham/PSITECH/Convis-main
docker run -d --name convis-api-local -p 8010:8000 --env-file convis-api/.env convis-api:local
```

### 2. Start Frontend (Terminal 2)
```bash
cd /media/shubham/Shubham/PSITECH/Convis-main/convis-web
npm run dev
```

### 3. Make Changes
- **Backend changes**: Rebuild Docker image and restart container
- **Frontend changes**: Auto-reload (hot reload enabled)

### 4. Test Changes
- Backend: `curl http://localhost:8010/api/...`
- Frontend: Refresh browser at `http://localhost:3000`

### 5. Stop Everything
```bash
# Stop backend
docker stop convis-api-local
docker rm convis-api-local

# Stop frontend
# Press Ctrl+C in the terminal running npm dev
```

---

## Hot Reload / Development Mode

### Backend Hot Reload (Python without Docker)
```bash
cd convis-api
source venv/bin/activate
uvicorn app.main:app --reload --port 8010
```
Changes to Python files will auto-reload!

### Frontend Hot Reload (Already Enabled)
```bash
npm run dev
```
Changes to React/TypeScript files auto-reload in browser!

---

## Testing Before Deployment

### 1. Test Call Flow
1. Create an assistant in UI
2. Assign a phone number
3. Make a test call
4. Check logs for errors

### 2. Test Custom Providers
1. Create assistant with Deepgram + Cartesia
2. Make test call
3. Verify speech-to-text and text-to-speech work

### 3. Test OpenAI Realtime
1. Create assistant with OpenAI Realtime API
2. Make test call
3. Verify conversation flows naturally

### 4. Check Database
```python
python3 check_assistant_config.py
```

---

## Build for Production

### Backend
```bash
docker build -t convis-api:v13 -f convis-api/Dockerfile convis-api
```

### Frontend
```bash
cd convis-web
npm run build
npm start  # Test production build locally
```

---

## Quick Start Commands

Copy and paste these to get started quickly:

```bash
# Terminal 1: Start Backend
cd /media/shubham/Shubham/PSITECH/Convis-main
docker run -d --name convis-api-local -p 8010:8000 --env-file convis-api/.env convis-api:v12

# Terminal 2: Start Frontend
cd /media/shubham/Shubham/PSITECH/Convis-main/convis-web
npm run dev

# Open browser to http://localhost:3000
```

---

## Environment Variables Reference

### Backend (.env in convis-api/)
```env
MONGODB_URI=mongodb+srv://...
OPENAI_API_KEY=sk-...
DEEPGRAM_API_KEY=...
CARTESIA_API_KEY=sk_car_...
ELEVENLABS_API_KEY=sk_...
TWILIO_ACCOUNT_SID=...
TWILIO_AUTH_TOKEN=...
API_BASE_URL=https://your-domain.com
JWT_SECRET_KEY=...
ENCRYPTION_KEY=...
```

### Frontend (.env.local in convis-web/)
```env
NEXT_PUBLIC_API_URL=http://localhost:8010
```

---

## Need Help?

### Check Logs
```bash
# Backend logs
docker logs -f convis-api-local

# Frontend logs
# Check the terminal where npm run dev is running
```

### Debug Database
```bash
python3 check_assistant_config.py
```

### Test API Endpoints
```bash
# Health check
curl http://localhost:8010/health

# List assistants
curl -H "Authorization: Bearer YOUR_TOKEN" http://localhost:8010/api/ai-assistants/
```

---

## Next Steps After Local Testing

1. ✅ Test all features locally
2. ✅ Fix any issues
3. ✅ Build production images
4. ✅ Deploy to VPS
5. ✅ Update environment variables for production
6. ✅ Test in production

Happy coding! 🚀
