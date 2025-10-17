# Campaign Creation Troubleshooting Guide

## Current Issue

**Error**: 500 Internal Server Error when creating campaign
**Message**: "Failed to create campaign"

## Recent Fixes Applied

### 1. Enhanced Error Logging (✅ Complete)

Updated `/convis-api/app/routes/campaigns.py`:
- Added detailed logging for campaign creation
- Better error messages with full traceback
- Validation for user_id and assistant_id formats
- Clear error messages for invalid ObjectId formats

### 2. Frontend Error Handling (✅ Complete)

Updated `/convis-web/app/campaigns/create-campaign-modal.tsx`:
- Added detailed console logging
- Better error message display
- Shows API response status and details

### 3. Fixed AI Agent ID Field Mismatch (✅ Complete - 2025-01-16)

**Issue**: Campaign creation failed with "Invalid assistant_id format: 'Feedback Collection Agent' is not a valid ObjectId"

**Root Cause**: The AI assistants API returns assistants with an `id` field, but the frontend interface expected `_id`, causing the dropdown to use the wrong field.

**Fix**: Updated `/convis-web/app/campaigns/create-campaign-modal.tsx`:
- Changed `AIAgent` interface from `_id: string` to `id: string`
- Updated dropdown to use `agent.id` instead of `agent._id`
- Added enhanced logging in `fetchAIAgents()` to help debug data format issues

## Diagnostic Steps

### Step 1: Check Server is Running

```bash
# Check if FastAPI server is running
ps aux | grep uvicorn

# If not running, start it:
cd /media/shubham/Shubham/PSITECH/Convis-main/convis-api
python run.py
```

### Step 2: Check Server Logs

When you click "Create Campaign", watch the server console for:

```
INFO: Creating campaign with payload: {...}
INFO: Inserting campaign document: {...}
INFO: Created campaign {id} for user {user_id}
```

Or error messages like:
```
ERROR: Invalid user_id format: ...
ERROR: Invalid assistant_id format: ...
ERROR: Full traceback: ...
```

### Step 3: Verify Prerequisites

#### MongoDB Connection
```bash
# Test MongoDB connection
python -c "from app.config.database import Database; db = Database.get_db(); print('MongoDB connected!')"
```

#### Redis Connection
```bash
# Test Redis
redis-cli ping
# Should return: PONG
```

### Step 4: Check Data Format

#### User ID Format
The user ID must be a valid MongoDB ObjectId (24 hex characters).

**Check in browser console:**
```javascript
// After opening the modal, check:
console.log(localStorage.getItem('user'))
```

Expected format:
```json
{
  "id": "507f1f77bcf86cd799439011",  // or
  "_id": "507f1f77bcf86cd799439011",  // or
  "clientId": "507f1f77bcf86cd799439011"
}
```

#### AI Agent ID Format
Must be a valid MongoDB ObjectId.

**Test API call:**
```bash
# Get your user ID first
USER_ID="your_user_id_here"

# Fetch AI agents
curl http://localhost:8000/api/ai-assistants/user/$USER_ID
```

Expected response:
```json
{
  "assistants": [
    {
      "_id": "507f1f77bcf86cd799439011",
      "name": "My AI Agent"
    }
  ]
}
```

#### Phone Number Format
Must be in E.164 format (e.g., +12125551234).

**Test API call:**
```bash
# Fetch phone numbers
curl http://localhost:8000/api/phone-numbers/user/$USER_ID
```

Expected response:
```json
{
  "phone_numbers": [
    {
      "_id": "507f1f77bcf86cd799439011",
      "phone_number": "+12125551234",
      "friendly_name": "Main Line"
    }
  ]
}
```

## Common Issues & Solutions

### Issue 1: Invalid User ID

**Symptom**: Error says "Invalid user_id format"

**Solution**:
1. Check user object in localStorage
2. Ensure `id`, `_id`, or `clientId` field exists
3. Verify it's a 24-character hex string

**Fix in code:**
```typescript
// In create-campaign-modal.tsx
const userId = user?.id || user?._id || user?.clientId;
console.log('Using user ID:', userId);
```

### Issue 2: Empty Dropdowns

**Symptom**: AI Agent or Phone Number dropdowns are empty

**Solution**:
1. Create AI agents first via AI Agent page
2. Add phone numbers via Phone Numbers page
3. Check API responses in browser console

**Quick test:**
```bash
# Check if you have AI agents
curl http://localhost:8000/api/ai-assistants/user/YOUR_USER_ID

# Check if you have phone numbers
curl http://localhost:8000/api/phone-numbers/user/YOUR_USER_ID
```

### Issue 3: MongoDB Connection Error

**Symptom**: "Failed to connect to MongoDB" in server logs

**Solution**:
```bash
# Check .env file
cat /media/shubham/Shubham/PSITECH/Convis-main/convis-api/.env | grep MONGODB

# Should show:
# MONGODB_URI=mongodb+srv://psitech:Psitech123@...
# DATABASE_NAME=convis_python
```

### Issue 4: Redis Not Running

**Symptom**: "Connection refused" for Redis

**Solution**:
```bash
# Start Redis
sudo systemctl start redis
# or
redis-server

# Verify
redis-cli ping
```

## Manual Test via API

You can bypass the UI and test the API directly:

```bash
# Create a test campaign
curl -X POST http://localhost:8000/api/campaigns \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "YOUR_USER_ID_HERE",
    "name": "Test Campaign",
    "country": "US",
    "caller_id": "+12125551234",
    "assistant_id": "YOUR_ASSISTANT_ID_HERE",
    "working_window": {
      "timezone": "America/New_York",
      "start": "09:00",
      "end": "17:00",
      "days": [0, 1, 2, 3, 4]
    },
    "retry_policy": {
      "max_attempts": 3,
      "retry_after_minutes": [15, 60, 1440]
    },
    "pacing": {
      "calls_per_minute": 1,
      "max_concurrent": 1
    }
  }'
```

**Expected Response (Success):**
```json
{
  "id": "67890abcdef...",
  "name": "Test Campaign",
  "status": "draft",
  "created_at": "2025-01-16T..."
}
```

**Expected Response (Error):**
```json
{
  "detail": "Invalid user_id format: ..."
}
```

## Verify Data in MongoDB

After successful creation, check MongoDB:

```javascript
// In MongoDB Compass or mongo shell
use convis_python

// Find all campaigns
db.campaigns.find().pretty()

// Find by user
db.campaigns.find({ user_id: ObjectId("YOUR_USER_ID") }).pretty()
```

Expected document structure:
```json
{
  "_id": ObjectId("..."),
  "user_id": ObjectId("..."),
  "name": "Test Campaign",
  "country": "US",
  "working_window": {
    "timezone": "America/New_York",
    "start": "09:00",
    "end": "17:00",
    "days": [0, 1, 2, 3, 4]
  },
  "caller_id": "+12125551234",
  "assistant_id": ObjectId("..."),
  "retry_policy": {
    "max_attempts": 3,
    "retry_after_minutes": [15, 60, 1440]
  },
  "pacing": {
    "calls_per_minute": 1,
    "max_concurrent": 1
  },
  "status": "draft",
  "created_at": ISODate("2025-01-16T..."),
  "updated_at": ISODate("2025-01-16T..."),
  "next_index": 0,
  "start_at": null,
  "stop_at": null
}
```

## Next Steps After Fixing

Once the campaign is created successfully:

1. **Upload Leads**: The modal will automatically upload the CSV
2. **Verify in MongoDB**:
   ```javascript
   // Check leads collection
   db.leads.find({ campaign_id: ObjectId("YOUR_CAMPAIGN_ID") }).count()
   ```

3. **Start Campaign**:
   ```bash
   curl -X PATCH http://localhost:8000/api/campaigns/YOUR_CAMPAIGN_ID/status \
     -H "Content-Type: application/json" \
     -d '{"status": "running"}'
   ```

## Environment Variables Checklist

Ensure these are set in `/convis-api/.env`:

```env
# MongoDB (✓ Already configured)
MONGODB_URI=mongodb+srv://...
DATABASE_NAME=convis_python

# Redis (Required for campaigns)
REDIS_URL=redis://localhost:6379

# Twilio (Required for calling)
TWILIO_ACCOUNT_SID=ACxxxxx
TWILIO_AUTH_TOKEN=xxxxx

# OpenAI (Required for post-call AI)
OPENAI_API_KEY=sk-xxxxx

# Base URL (Required for webhooks)
API_BASE_URL=https://your-ngrok-url.ngrok-free.dev
BASE_URL=https://your-ngrok-url.ngrok-free.dev
```

## Quick Fix Checklist

- [ ] FastAPI server is running
- [ ] MongoDB is connected
- [ ] Redis is running
- [ ] User has valid ObjectId format
- [ ] At least one AI agent exists
- [ ] At least one phone number exists
- [ ] All required env variables are set
- [ ] Server logs show detailed error messages
- [ ] Browser console shows request/response

## Getting More Help

If the issue persists:

1. **Capture Full Error**:
   - Server console output
   - Browser console output
   - Network tab showing the request/response

2. **Check Logs**:
   ```bash
   # Server logs
   cd /media/shubham/Shubham/PSITECH/Convis-main/convis-api
   tail -f logs/app.log  # if logging to file
   ```

3. **Test Components Individually**:
   - Test MongoDB connection
   - Test campaign model validation
   - Test API endpoint with curl
   - Test frontend form submission

## Contact Points

- Backend API: `http://localhost:8000`
- API Docs: `http://localhost:8000/docs`
- Frontend: `http://localhost:3000`
- MongoDB: `mongodb+srv://...` (already configured)
- Redis: `localhost:6379`

---

**Last Updated**: 2025-01-16
**Status**: Debugging in progress
**Priority**: High - Campaign creation is a core feature
