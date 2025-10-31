# FreJun Webhook Debug Information

## Webhook URLs Configured

**Your API Base URL:** `https://api.convis.ai`

### Incoming Call URL
```
https://api.convis.ai/api/frejun/flow
```

### Call Status URL
```
https://api.convis.ai/api/frejun/webhook
```

## Test Endpoints (For FreJun Team to Verify Connectivity)

### 1. Health Check (GET)
```bash
curl https://api.convis.ai/api/frejun/health
```

**Expected Response:**
```json
{
  "status": "healthy",
  "service": "frejun-integration",
  "version": "1.0.0"
}
```

### 2. Test Endpoint (GET)
```bash
curl https://api.convis.ai/api/frejun/test
```

**Expected Response:**
```json
{
  "status": "ok",
  "message": "FreJun webhook endpoint is reachable",
  "timestamp": "2025-10-31T..."
}
```

### 3. Test Endpoint (POST)
```bash
curl -X POST https://api.convis.ai/api/frejun/test \
  -H "Content-Type: application/json" \
  -d '{"test": "data"}'
```

**Expected Response:**
```json
{
  "status": "ok",
  "message": "FreJun webhook endpoint is reachable",
  "received_data": {"test": "data"},
  "timestamp": "2025-10-31T..."
}
```

## Flow Endpoint Specification

### Request Format (Flexible)

The endpoint accepts multiple field name formats:

```json
{
  "call_id": "string",       // or "callId" or "id"
  "account_id": "string",
  "from_number": "string",   // or "from" or "fromNumber"
  "to_number": "string"      // or "to" or "toNumber"
}
```

### Response Format

```json
{
  "type": "stream",
  "ws_url": "wss://api.convis.ai/api/frejun/media-stream/{assistant_id}?call_id={call_id}",
  "chunk_size": 500,
  "record": true
}
```

## Webhook Status Endpoint Specification

### Request Format

```json
{
  "call_id": "string",
  "status": "string",
  "duration": 120,
  "from_number": "string",
  "to_number": "string"
}
```

### Response Format

```json
{
  "status": "ok",
  "message": "Status update received"
}
```

## Common Issues & Solutions

### Issue 1: Connection Timeout
**Symptom:** FreJun cannot reach the webhook URLs
**Solution:**
- Verify `https://api.convis.ai` is publicly accessible
- Check firewall rules allow incoming HTTPS traffic on port 443
- Ensure SSL certificate is valid

### Issue 2: SSL Certificate Issues
**Symptom:** SSL handshake errors
**Solution:**
- Verify SSL certificate with: `curl -v https://api.convis.ai/api/frejun/health`
- Ensure certificate is not self-signed
- Check certificate chain is complete

### Issue 3: 404 Not Found
**Symptom:** Endpoint returns 404
**Solution:**
- Verify router is registered in main.py
- Check endpoint path is exactly: `/api/frejun/flow`
- Ensure API is deployed and running

### Issue 4: 422 Validation Error
**Symptom:** Pydantic validation fails
**Solution:**
- Endpoint now accepts flexible field formats
- Check logs for exact payload received
- Payload is logged as: `[FREJUN] Raw flow request payload: {...}`

## Debugging Steps for FreJun Team

1. **Test Basic Connectivity:**
   ```bash
   curl -I https://api.convis.ai/api/frejun/health
   ```
   Should return HTTP 200

2. **Test POST Endpoint:**
   ```bash
   curl -X POST https://api.convis.ai/api/frejun/test \
     -H "Content-Type: application/json" \
     -d '{"test": "frejun"}'
   ```
   Should return JSON with received data

3. **Test Flow Endpoint with Sample Data:**
   ```bash
   curl -X POST https://api.convis.ai/api/frejun/flow \
     -H "Content-Type: application/json" \
     -d '{
       "call_id": "test_123",
       "account_id": "acc_123",
       "from_number": "+1234567890",
       "to_number": "+0987654321"
     }'
   ```

   **Expected:** May return 404 if number not in database, but should NOT timeout

4. **Check DNS Resolution:**
   ```bash
   nslookup api.convis.ai
   ```

5. **Check SSL Certificate:**
   ```bash
   openssl s_client -connect api.convis.ai:443 -servername api.convis.ai
   ```

## What Gets Logged

All FreJun webhook requests are logged with:

1. **Flow Request:**
   ```
   [FREJUN] Raw flow request payload: {full payload}
   [FREJUN] Call flow requested - Call ID: xxx, From: xxx, To: xxx
   ```

2. **Webhook Status:**
   ```
   [FREJUN WEBHOOK] Call status update received: {full payload}
   ```

3. **Test Requests:**
   ```
   [FREJUN TEST] Received test POST request: {payload}
   ```

## Contact Information

If FreJun team needs logs or additional debugging:
- Check application logs at: `/app/logs/` in the Docker container
- Use: `docker logs convis-api` to view real-time logs
- Logs include full request payloads for debugging

## Network Requirements

**Outbound (From Convis to FreJun):**
- HTTPS port 443 to FreJun API servers
- WebSocket (WSS) for audio streaming

**Inbound (From FreJun to Convis):**
- HTTPS port 443 for webhooks
- Must accept POST requests from FreJun IP ranges
- No authentication required for webhooks (public endpoints)

## WebSocket Audio Streaming

**WebSocket URL Format:**
```
wss://api.convis.ai/api/frejun/media-stream/{assistant_id}?call_id={call_id}
```

**Audio Format:**
- Sample Rate: 8kHz (FreJun) ↔ 24kHz (OpenAI)
- Encoding: PCM 16-bit
- Channels: Mono
- Transport: Base64-encoded chunks

**Message Format (FreJun → Backend):**
```json
{
  "type": "audio",
  "data": {
    "audio_b64": "base64_encoded_pcm_audio"
  }
}
```

**Message Format (Backend → FreJun):**
```json
{
  "type": "audio",
  "data": "base64_encoded_pcm_audio"
}
```

## Server Configuration

**FastAPI Application:**
- Running on: `0.0.0.0:8000`
- Reverse Proxy: Nginx/Traefik → HTTPS
- Public URL: `https://api.convis.ai`

**Router Registration:**
```python
app.include_router(frejun_router, prefix="/api/frejun", tags=["FreJun Calls"])
```

## Next Steps

1. Share this document with FreJun support team
2. Ask them to run the test commands above
3. Request detailed error message if connection fails
4. Check if FreJun requires IP whitelisting
5. Verify FreJun can reach public endpoints (not behind VPN)

## App Configuration in FreJun

```
App ID: 7dad88a2-f257-48ff-8164-30689db41f9a
App Name: Convis
Status: Active
```

**Webhooks Must Point To:**
- Incoming Call: `https://api.convis.ai/api/frejun/flow`
- Call Status: `https://api.convis.ai/api/frejun/webhook`

---

**Last Updated:** 2025-10-31
**Version:** 1.0.0
