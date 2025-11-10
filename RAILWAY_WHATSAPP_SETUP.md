# Railway WhatsApp API Integration - Quick Setup Guide

## Overview

The WhatsApp integration has been updated to work with your **Railway WhatsApp API** instead of Meta's direct API.

---

## 🔑 Credentials You Need

From your curl command, users will need:

1. **API Key** (`x-api-key`): `ef99d3d2-e032-4c04-8e27-9313b2e6b172`
2. **Bearer Token** (`Authorization`): `bn-9a32959187ad4140bf0b2c48b7c9cb08`
3. **API URL** (optional): `https://whatsapp-api-backend-production.up.railway.app`

---

## ✅ Changes Made

### Backend Updates:

1. **WhatsAppService** ([whatsapp_service.py](convis-api/app/services/whatsapp_service.py))
   - Changed from Meta API to Railway API
   - Uses `api_key` and `bearer_token` instead of `access_token` and `phone_number_id`
   - Implements `/api/send-message` and `/api/sync-templates` endpoints

2. **Models** ([whatsapp.py](convis-api/app/models/whatsapp.py:12-38))
   - Updated `WhatsAppCredentialCreate` to use Railway API fields
   - Updated `WhatsAppConnectionTest` for Railway API
   - Changed response models to reflect Railway API structure

3. **Routes** ([credentials.py](convis-api/app/routes/whatsapp/credentials.py), [messages.py](convis-api/app/routes/whatsapp/messages.py))
   - Updated to work with encrypted Railway API credentials
   - Connection test uses `/api/sync-templates` endpoint

---

## 🎯 How Users Will Add Their WhatsApp Account

### Step 1: Get Credentials
Users need to obtain their Railway WhatsApp API credentials:
- API Key
- Bearer Token

### Step 2: Add in Convis UI

Navigate to `/whatsapp` page and click "Add Account":

**Form Fields:**
```
Label: My WhatsApp Business
API Key: ef99d3d2-e032-4c04-8e27-9313b2e6b172
Bearer Token: bn-9a32959187ad4140bf0b2c48b7c9cb08
API URL: https://whatsapp-api-backend-production.up.railway.app (default)
```

### Step 3: Test Connection
Click "Test Connection" - it will call `/api/sync-templates` to verify credentials.

### Step 4: Save
Once verified, credentials are encrypted and stored in MongoDB.

---

## 📤 Sending Messages

### Template Message (Recommended)

```bash
curl -X POST "http://localhost:8000/api/whatsapp/send" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "credential_id": "67...abc",
    "to": "+919131296862",
    "message_type": "template",
    "template_name": "atithi_host_1",
    "template_params": ["sanket","sagar","9131296862","taj hotel lobby","interview"]
  }'
```

### Text Message (if supported by Railway API)

```bash
curl -X POST "http://localhost:8000/api/whatsapp/send" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "credential_id": "67...abc",
    "to": "+919131296862",
    "message_type": "text",
    "text": "Hello from Convis!"
  }'
```

---

## 🔄 API Endpoints Mapping

| Convis Endpoint | Railway API Endpoint | Purpose |
|----------------|---------------------|---------|
| `POST /api/whatsapp/test-connection` | `GET /api/sync-templates` | Verify credentials |
| `POST /api/whatsapp/send` | `POST /api/send-message` | Send message |
| `GET /api/whatsapp/templates` | `GET /api/sync-templates` | Get templates |

---

## 📝 Frontend Modal Updates Needed

Update `AddCredentialModal.tsx` to use Railway API fields:

```typescript
const [formData, setFormData] = useState({
  label: '',
  api_key: '',  // Instead of phone_number_id
  bearer_token: '',  // Instead of access_token
  api_url: 'https://whatsapp-api-backend-production.up.railway.app'  // Optional
});
```

Form fields:
```tsx
<input
  name="api_key"
  placeholder="Your Railway API Key (x-api-key)"
  ...
/>

<input
  name="bearer_token"
  placeholder="Your Railway Bearer Token"
  ...
/>

<input
  name="api_url"
  placeholder="https://whatsapp-api-backend-production.up.railway.app"
  value={formData.api_url}
  ...
/>
```

---

## 🗄️ Database Schema

### `whatsapp_credentials` Collection

```javascript
{
  _id: ObjectId("..."),
  user_id: ObjectId("..."),
  label: "My WhatsApp Business",
  api_key: "encrypted_api_key",  // Encrypted
  bearer_token: "encrypted_bearer_token",  // Encrypted
  api_url: "https://whatsapp-api-backend-production.up.railway.app",
  last_four: "b172",  // Last 4 chars of API key
  api_url_masked: "railway.app",
  status: "active",
  created_at: ISODate("..."),
  updated_at: ISODate("...")
}
```

---

## 🧪 Testing

### 1. Test Railway API Directly

```bash
# Sync templates
curl -X GET https://whatsapp-api-backend-production.up.railway.app/api/sync-templates \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer bn-9a32959187ad4140bf0b2c48b7c9cb08" \
  -H "x-api-key: ef99d3d2-e032-4c04-8e27-9313b2e6b172"

# Send message
curl -X POST "https://whatsapp-api-backend-production.up.railway.app/api/send-message" \
  -H "Content-Type: application/json" \
  -H "x-api-key: ef99d3d2-e032-4c04-8e27-9313b2e6b172" \
  -H "Authorization: Bearer bn-9a32959187ad4140bf0b2c48b7c9cb08" \
  -d '{
    "to_number": "+919131296862",
    "template_name": "atithi_host_1",
    "whatsapp_request_type": "TEMPLATE",
    "parameters": ["sanket","sagar","9131296862","taj hotel lobby","interview"]
  }'
```

### 2. Test Convis Backend

```bash
# Start backend
cd convis-api
python run.py

# Test connection endpoint
curl -X POST "http://localhost:8000/api/whatsapp/test-connection" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "api_key": "ef99d3d2-e032-4c04-8e27-9313b2e6b172",
    "bearer_token": "bn-9a32959187ad4140bf0b2c48b7c9cb08"
  }'
```

### 3. Test Frontend

```bash
cd convis-web
npm run dev

# Navigate to http://localhost:3010/whatsapp
# Add account and test
```

---

## 🔐 Security Notes

1. **Encryption**: API keys and bearer tokens are encrypted using Fernet before storing in MongoDB
2. **Authentication**: All endpoints require JWT authentication
3. **Validation**: Input validation on all fields
4. **Masked Display**: Only last 4 characters of API key shown in UI

---

## 🚀 CSV Bulk Sending Integration

To integrate with your existing CSV function:

```python
# In your CSV processing code
from app.services.whatsapp_service import WhatsAppService

# Get user's credential
credential = credentials_collection.find_one({"user_id": user_id, "status": "active"})

# Initialize service
whatsapp_service = WhatsAppService(
    api_key=encryption_service.decrypt(credential["api_key"]),
    bearer_token=encryption_service.decrypt(credential["bearer_token"]),
    base_url=credential.get("api_url")
)

# Send to each number from CSV
for row in csv_data:
    number = row["Contact Number"]
    result = await whatsapp_service.send_template_message(
        to=number,
        template_name="user_call_confirm_v1",
        parameters=[company_name]
    )
```

---

## 📋 Next Steps

1. **Update Frontend Modal** - Copy the updated modal code from this guide
2. **Set Environment Variables** - Add `ENCRYPTION_KEY` to `.env`
3. **Test Connection** - Use your Railway credentials to test
4. **Send Test Message** - Try sending a template message
5. **Integrate with CSV** - Connect to your existing CSV upload function

---

## ⚠️ Important Notes

- Railway API primarily supports **template messages**
- Make sure templates are approved in Meta Business Manager before using
- Template names must match exactly (e.g., `atithi_host_1`)
- Phone numbers must include country code with `+` prefix
- Parameters array order must match template variable order

---

## 🐛 Troubleshooting

**Error: "Connection failed"**
- Verify API key and bearer token are correct
- Check if Railway API is accessible
- Ensure credentials haven't expired

**Error: "Template not found"**
- Run `/api/sync-templates` to get available templates
- Verify template name spelling
- Check template is approved in Meta

**Error: "Invalid phone number"**
- Must start with `+` and country code
- Format: `+919131296862` (not `9131296862`)

---

## 📞 Support

Railway API seems to be a custom wrapper around Meta WhatsApp API. If you need specific features:
- Check Railway API documentation
- Contact Railway API support for additional endpoints
- Request features like direct text messages if needed

---

Your WhatsApp integration is now configured for Railway API! 🎉
