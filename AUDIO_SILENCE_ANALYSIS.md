# Audio Silence Issue - Complete Analysis

## Issue Summary
All outbound calls experience silence - no audio is heard by the caller.

## TTS Providers & Audio Format Analysis

### Twilio Requirements
- **Format**: μ-law (G.711)
- **Sample Rate**: 8000 Hz
- **Channels**: 1 (mono)
- **Encoding**: 8-bit μ-law
- **Container**: Raw audio chunks (base64 encoded)

### Provider Outputs vs Requirements

#### 1. **Cartesia TTS** ✅ (Best Match)
- **Output Format**: PCM 16-bit LE @ 8000 Hz
- **File**: `app/providers/tts.py:95-118`
- **Conversion Needed**: PCM → μ-law
- **Status**: Configured correctly, conversion handled at `custom_provider_stream.py:468-477`

#### 2. **ElevenLabs TTS** ⚠️
- **Output Format**: PCM @ 16000 Hz
- **File**: `app/providers/tts.py:176-186`
- **Conversion Needed**: Resample 16kHz→8kHz + PCM→μ-law
- **Status**: Conversion handled at `custom_provider_stream.py:447-477`

#### 3. **OpenAI TTS** ⚠️
- **Output Format**: PCM @ 24000 Hz
- **File**: `app/providers/tts.py:260-285`
- **Conversion Needed**: Resample 24kHz→8kHz + PCM→μ-law
- **Status**: Conversion handled at `custom_provider_stream.py:449-477`
- **Note**: Added comprehensive debug logging

#### 4. **Sarvam TTS** ⚠️⚠️ (MOST LIKELY ISSUE)
- **Output Format**: WAV @ 8000 Hz (unknown actual format)
- **File**: `app/voice_pipeline/synthesizer/sarvam_synthesizer.py`
- **Conversion Pipeline**:
  1. Sarvam WebSocket → receives WAV bytes
  2. `resample()` @ line 378 → resamples WAV to 8kHz
  3. `wav_bytes_to_pcm()` @ line 379 → extracts PCM from WAV
  4. `pcm16_to_mulaw()` @ line 382 → converts to μ-law
- **Status**: ⚠️ **AUDIO NOT BEING RECEIVED FROM SARVAM API**

## Analysis from User's Test Logs

### What We See:
```
[SARVAM_TTS] Connected to wss://api.sarvam.ai/text-to-speech/ws?model=bulbul:v2
[SARVAM_TTS] Sent text chunk: Hello! Thanks for calling. How can I help you toda...
[SARVAM_TTS] Sent flush signal
```

### What We DON'T See:
```
[SARVAM_TTS] 📨 Received message type: audio  ← MISSING!
[SARVAM_TTS] ✅ Received audio chunk (XXXX bytes)  ← MISSING!
```

## Root Cause

### Primary Issue: **Sarvam API Not Returning Audio**

The logs show:
1. ✅ WebSocket connection established
2. ✅ Text sent to Sarvam
3. ✅ Flush signal sent
4. ❌ **NO audio received back from Sarvam**

### Possible Reasons:

#### 1. **Sarvam API Key Issue** (Most Likely)
   - Invalid API key
   - Expired API key
   - Missing required headers

#### 2. **Config Message Format**
   - Lines 257-272 of `sarvam_synthesizer.py`
   - Config sent to Sarvam might be incorrect
   - Check: `output_audio_codec`, `output_audio_bitrate`, `max_chunk_length`

#### 3. **Language/Speaker Mismatch**
   - Speaker: `manisha`
   - Language: `hi-IN` (Hindi)
   - Text sent: `"Hello! Thanks for calling..."` (English)
   - **This mismatch might cause Sarvam to fail silently!**

#### 4. **Model Not Responding**
   - Model: `bulbul:v2`
   - WebSocket might not support this model
   - Try: `bulbul:v3-beta`

## Debug Logging Added

### Files Modified:
1. **`sarvam_synthesizer.py:226-244`** - Added message type logging
2. **`sarvam_synthesizer.py:268-300`** - Added config send/receive logging
3. **`sarvam_synthesizer.py:170-190`** - Added detailed text/flush message logging
4. **`custom_provider_stream.py:302-360`** - Added TTS call logging
5. **`tts.py:260-285`** - Added OpenAI TTS debug logging

### Enhanced Logging Output:
```
[SARVAM_TTS] 📤 Sending config: {...}        ← Full config JSON
[SARVAM_TTS] 📥 Config response: {...}       ← What Sarvam responds
[SARVAM_TTS] 📤 Sending text message: {...}  ← Exact text being sent
[SARVAM_TTS] ✅ Text chunk sent successfully
[SARVAM_TTS] 📤 Sending flush: {...}
[SARVAM_TTS] ✅ Flush signal sent successfully
[SARVAM_TTS] 📨 Received message type: XXX   ← What Sarvam returns
[SARVAM_TTS] ✅ Received audio chunk (N bytes)
```

### What to Look For in Next Test:
```bash
# Run a test call and check logs:
docker logs -f convis-api | grep -E "(SARVAM|CUSTOM|OpenAI TTS)"
```

Critical checkpoints:
1. ✅ Config sent → Did Sarvam acknowledge or reject it?
2. ✅ Text message format → Is JSON properly formatted?
3. ✅ Flush signal → Was it sent successfully?
4. ❌ **MISSING**: Audio message reception
5. Look for errors: `❌ Config rejected` or `❌ Error from Sarvam`

## Recommended Fixes

### Immediate Action (Test These in Order):

#### 1. **Fix Language Mismatch**
The greeting is in English but Sarvam is configured for Hindi (`hi-IN`).

**Location**: Check assistant configuration
- If bot speaks English → change language to `en-IN`
- If bot speaks Hindi → change greeting to Hindi

#### 2. **Verify Sarvam API Key**
```bash
# Test Sarvam API directly
curl -X POST https://api.sarvam.ai/text-to-speech \
  -H "api-subscription-key: YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "target_language_code": "en-IN",
    "speaker": "manisha",
    "text": "Hello, this is a test"
  }'
```

#### 3. **Try Different TTS Provider**
Test with OpenAI TTS instead of Sarvam to isolate the issue:
- Change assistant TTS provider to: `openai`
- This will use the working OpenAI TTS pipeline

#### 4. **Check Sarvam Config**
In `sarvam_synthesizer.py:257-272`, try:
```python
config_message = {
    "type": "config",
    "data": {
        "target_language_code": "en-IN",  # Change to English
        "speaker": "manisha",
        "pitch": 0.0,
        "pace": 1.0,
        "loudness": 1.0,
        "enable_preprocessing": True,
        "output_audio_codec": "wav",  # Try "pcm" instead
        "output_audio_bitrate": "16k",  # Try "8k" instead
    }
}
```

## Next Steps

1. **Run another test call** with the debug logging
2. **Share the complete logs** from call start to end
3. **Check Sarvam API documentation** for correct WebSocket format
4. **Consider switching to OpenAI TTS** temporarily as a workaround

## Files to Review
- `convis-api/app/voice_pipeline/synthesizer/sarvam_synthesizer.py`
- `convis-api/app/voice_pipeline/helpers/utils.py`
- `convis-api/app/routes/frejun/custom_provider_stream.py`
- `convis-api/app/providers/tts.py`
