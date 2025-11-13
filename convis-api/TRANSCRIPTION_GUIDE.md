# Call Transcription System - Quick Guide

## How It Works

### Automatic Transcription (Future Calls)
All calls are automatically:
1. **Recorded** when call ends
2. **Transcribed** using OpenAI Whisper (30-60 seconds)
3. **Analyzed** for sentiment and summary
4. **Visible** in the UI

No action needed - it's fully automatic!

### Retroactive Transcription (Past Calls)

#### From UI (Recommended):
1. Go to Phone Numbers page
2. Click the **"Transcribe All Calls"** button (purple button)
3. Wait 2-5 minutes
4. Refresh page to see transcripts

#### From API:
```bash
curl -X POST http://localhost:8000/api/transcription/transcribe-all \
  -H "Authorization: Bearer YOUR_TOKEN"
```

## API Endpoints

### POST `/api/transcription/transcribe-all`
Transcribe all past calls that have recordings

**Response:**
```json
{
  "message": "Transcription complete! 15/15 calls transcribed.",
  "total_calls": 15,
  "transcribed": 15,
  "failed": 0
}
```

### GET `/api/transcription/status`
Get transcription coverage statistics

**Response:**
```json
{
  "total_calls": 50,
  "calls_with_recordings": 30,
  "calls_with_transcripts": 28,
  "coverage_percentage": 93.3,
  "needs_transcription": 2
}
```

### POST `/api/transcription/fetch-from-twilio`
Fetch recordings from Twilio (past 30 days)

**Response:**
```json
{
  "message": "Fetched 23 recordings from Twilio",
  "total_recordings": 23,
  "recordings_added": 5,
  "transcribed": 5
}
```

## Environment Variables

Required in `.env`:
```bash
OPENAI_API_KEY=sk-proj-xxxxx  # For transcription
TWILIO_ACCOUNT_SID=ACxxxxx     # Optional, for Twilio fetch
TWILIO_AUTH_TOKEN=xxxxx        # Optional, for Twilio fetch
```

## Files Structure

```
convis-api/
├── app/
│   ├── routes/
│   │   └── transcription/
│   │       ├── __init__.py
│   │       └── transcription.py      # API endpoints
│   ├── services/
│   │   └── post_call_processor.py    # Transcription logic
│   └── main.py                        # Router registration
```

## Running the System

### Development:
```bash
cd convis-api
python run.py
```

That's it! Both automatic and manual transcription will work.

### Production:
Same command - no additional scripts needed.

## How to Use

### For Future Calls:
Just make calls normally. They'll be transcribed automatically.

### For Past Calls:
1. Open UI → Phone Numbers page
2. Click "Transcribe All Calls" button
3. Wait for completion
4. Refresh to see transcripts

## Cost

Per call (5 minutes):
- OpenAI Whisper: ~$0.03
- GPT analysis: ~$0.0001
- **Total: ~$0.03 per call**

Very affordable for AI transcription!

## Verification

Check if everything is working:
```bash
curl http://localhost:8000/api/transcription/status
```

You should see coverage percentage and call counts.

## Troubleshooting

### "OPENAI_API_KEY not set"
Add to `.env` file:
```bash
OPENAI_API_KEY=sk-proj-xxxxx
```

### Transcripts not showing
1. Wait 60-90 seconds after call ends
2. Refresh the page
3. Check API logs for errors

### Button not working
1. Make sure you're logged in
2. Check browser console for errors
3. Verify API is running

## Summary

- ✅ All code integrated into main app
- ✅ No standalone scripts in root directory
- ✅ Works with just `python run.py`
- ✅ UI button for manual transcription
- ✅ Automatic transcription for all future calls
- ✅ Clean and maintainable architecture

Everything works seamlessly with your existing development workflow!
