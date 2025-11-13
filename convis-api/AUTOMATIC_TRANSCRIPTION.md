# Automatic Call Transcription - How It Works

## 100% Automatic - No Buttons, No Manual Work

Transcription happens automatically in **3 scenarios**:

### 1. When Server Starts (Past Calls)
- Server automatically finds all recordings without transcripts
- Starts transcribing them in background (limit 50 at a time)
- Takes 2-5 minutes after server start
- You'll see logs: `🎙️ Found X calls to transcribe...`

### 2. When Call Ends (Future Calls)
- Call automatically recorded via Twilio
- Recording callback triggers transcription (30-60 seconds)
- Transcript appears in database automatically
- Refresh UI to see new transcripts

### 3. Background Process
- Continuously checks for new recordings
- Transcribes anything that's missing
- No manual intervention needed

## How to Verify It's Working

### Check Logs:
```bash
# Look for these messages in your API logs:
🎙️ Found X calls to transcribe - starting background transcription...
✓ Transcribed CAxxxxx
✓ Background transcription complete!
```

### Check Database:
```bash
cd convis-api
python -c "
from app.config.database import Database
db = Database.get_db()
transcribed = db['call_logs'].count_documents({'transcript': {'\$ne': None}})
print(f'Calls with transcripts: {transcribed}')
"
```

### Check UI:
- Refresh Call Logs page
- Calls with transcripts show blue document icon 📄
- Click call → See full transcript

## What Happens When You Restart

```
1. Server Starts
   ↓
2. Connects to database
   ↓
3. Waits 10 seconds
   ↓
4. Checks for calls with recordings but no transcripts
   ↓
5. Transcribes them automatically (2 sec delay between each)
   ↓
6. Logs progress: "✓ Transcribed CAxxxxx"
   ↓
7. Done! Transcripts visible in UI
```

## For New Calls

```
Call Ends
   ↓
Twilio Saves Recording
   ↓
Recording Callback → /api/twilio-webhooks/recording
   ↓
Saves recording URL to database
   ↓
Triggers transcription immediately
   ↓
(30-60 seconds)
   ↓
Transcript saved to database
   ↓
Visible in UI ✓
```

## Environment Variables Required

In `.env`:
```bash
OPENAI_API_KEY=sk-proj-xxxxx  # REQUIRED for transcription
```

Optional (for fetching from Twilio):
```bash
TWILIO_ACCOUNT_SID=ACxxxxx
TWILIO_AUTH_TOKEN=xxxxx
```

## Cost

Per call (5 minutes average):
- OpenAI Whisper: ~$0.03
- GPT analysis: ~$0.0001
- **Total: ~$0.03 per call**

## Files Involved

### Backend:
- `app/main.py` - Background transcription on startup
- `app/routes/twilio_webhooks/webhooks.py` - Recording callback
- `app/services/post_call_processor.py` - Transcription logic
- `app/routes/transcription/transcription.py` - API endpoints (optional)

### Frontend:
- `convis-web/app/phone-numbers/page.tsx` - Display transcripts

## Troubleshooting

### "No transcripts appearing"

**Wait**: Give it 2-3 minutes after server restart
**Check logs**: Look for "Found X calls to transcribe"
**Check OpenAI key**: Make sure it's set in `.env`

### "Some calls missing transcripts"

**Check recording URL**: Some calls might not have recordings
**Check API logs**: Look for transcription errors
**Restart server**: Background task will retry

### "Transcription failed"

**Causes:**
- OpenAI API key invalid
- Recording file corrupted
- Network error
- OpenAI API quota exceeded

**Solution:** Check API logs for specific error messages

## Summary

- ✅ **No buttons** - Everything automatic
- ✅ **No manual work** - Just restart server
- ✅ **Past calls** - Transcribed on startup
- ✅ **Future calls** - Transcribed when call ends
- ✅ **Background processing** - Continuous checking
- ✅ **Clean architecture** - All integrated in main app

**Just run `python run.py` and everything works!** 🎉
