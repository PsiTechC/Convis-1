# Call Cost Testing Guide

Complete guide for testing and monitoring call costs in Convis.

## Overview

Two powerful scripts for accurate call cost analysis:

1. **`test_call_costs.py`** - Compare all provider configurations
2. **`track_live_call_costs.py`** - Track actual call costs from database

---

## Quick Start

### 1. Test All Provider Configurations

```bash
python3 test_call_costs.py
```

**Output:**
- Cost comparison table (per minute, per hour, per 1000 minutes)
- Detailed breakdown for each configuration
- Cost savings vs OpenAI Realtime API
- Recommendations by use case
- Latency comparison
- Exports to `call_cost_analysis.json`

### 2. Track Live Call Costs

```bash
# Analyze last 24 hours
python3 track_live_call_costs.py

# Analyze last 7 days
python3 track_live_call_costs.py --hours 168

# Filter by user
python3 track_live_call_costs.py --user-id 68ea825661b48c4858c75745

# Filter by provider
python3 track_live_call_costs.py --provider twilio

# Watch mode (updates every 30 seconds)
python3 track_live_call_costs.py --watch
```

**Output:**
- Total calls and duration
- Total cost and average cost per minute
- Breakdown by provider type (Realtime vs Custom)
- List of recent calls with individual costs

---

## Cost Comparison Results

### Per-Minute Costs (Ranked)

| Configuration | Per Min | Per Hour | Per 1K Min | Savings vs Realtime |
|--------------|---------|----------|------------|---------------------|
| **Custom (Deepgram + Cartesia + GPT-3.5)** | $0.0047 | $0.28 | $4.68 | **99.5% cheaper** ✅ |
| **Custom (Deepgram + Cartesia + GPT-4-Turbo)** | $0.0112 | $0.67 | $11.21 | **98.8% cheaper** ✅ |
| Custom (Deepgram + ElevenLabs + GPT-4-Turbo) | $0.0113 | $0.68 | $11.29 | 98.8% cheaper |
| Custom (Deepgram + ElevenLabs + GPT-4) | $0.0194 | $1.16 | $19.41 | 97.9% cheaper |
| Custom (Deepgram Medical + Cartesia + GPT-4) | $0.0209 | $1.26 | $20.94 | 97.7% cheaper |
| OpenAI Realtime API | $0.9070 | $54.42 | $907.00 | Baseline |

---

## Detailed Breakdown

### 🏆 **BEST VALUE: Deepgram + Cartesia + GPT-3.5-Turbo**

**Cost:** $0.0047/min | $0.28/hour | $4.68 per 1,000 minutes

**Breakdown:**
- STT (Deepgram nova-2): $0.0043/min
- TTS (Cartesia sonic): $0.0000/min (~free, 750 chars)
- LLM (GPT-3.5-turbo): $0.0003/min
  - Input: 125 tokens × $0.0005/1K = $0.0001
  - Output: 188 tokens × $0.0015/1K = $0.0003

**Best For:**
- High-volume applications
- Cost-sensitive deployments
- Internal tools
- Testing and development

**Latency:** 380-670ms

---

### ⚡ **BEST BALANCE: Deepgram + Cartesia + GPT-4-Turbo**

**Cost:** $0.0112/min | $0.67/hour | $11.21 per 1,000 minutes

**Breakdown:**
- STT (Deepgram nova-2): $0.0043/min
- TTS (Cartesia sonic): $0.0000/min
- LLM (GPT-4-turbo): $0.0069/min
  - Input: 125 tokens × $0.01/1K = $0.0013
  - Output: 188 tokens × $0.03/1K = $0.0056

**Best For:**
- Production applications
- Customer support
- Sales calls
- General business use

**Latency:** 380-670ms

**✅ RECOMMENDED FOR PRODUCTION**

---

### 💎 **PREMIUM QUALITY: Deepgram + ElevenLabs + GPT-4**

**Cost:** $0.0194/min | $1.16/hour | $19.41 per 1,000 minutes

**Breakdown:**
- STT (Deepgram nova-2): $0.0043/min
- TTS (ElevenLabs turbo_v2): $0.0001/min (750 chars)
- LLM (GPT-4): $0.0150/min
  - Input: 125 tokens × $0.03/1K = $0.0037
  - Output: 188 tokens × $0.06/1K = $0.0112

**Best For:**
- Customer-facing applications
- High-value clients
- Demos and presentations
- Premium services

**Latency:** 380-670ms

---

### 🏥 **MEDICAL SPECIFIC: Deepgram Medical + Cartesia + GPT-4**

**Cost:** $0.0209/min | $1.26/hour | $20.94 per 1,000 minutes

**Breakdown:**
- STT (Deepgram nova-2-medical): $0.0059/min
- TTS (Cartesia sonic): $0.0000/min
- LLM (GPT-4): $0.0150/min

**Best For:**
- Healthcare applications
- Medical terminology
- HIPAA compliance required
- Patient interactions

**Latency:** 380-670ms

---

### ⚠️ **OpenAI Realtime API**

**Cost:** $0.9070/min | $54.42/hour | $907.00 per 1,000 minutes

**Breakdown:**
- Audio Input: 3,000 tokens × $100/1M = $0.3000
- Audio Output: 3,000 tokens × $200/1M = $0.6000
- Text Input: 200 tokens × $5/1M = $0.0010
- Text Output: 300 tokens × $20/1M = $0.0060

**Pros:**
- Lowest latency (232-320ms)
- Single API call
- Simplest implementation

**Cons:**
- **193x more expensive** than best custom option
- **81x more expensive** than recommended production option
- Very high cost for production use

**Best For:**
- Prototyping only
- Low-volume testing
- Latency-critical demos

**⚠️ NOT RECOMMENDED FOR PRODUCTION**

---

## Cost Savings Calculator

### Example: 10,000 minutes/month

| Configuration | Monthly Cost | Savings vs Realtime |
|--------------|--------------|---------------------|
| Deepgram + Cartesia + GPT-3.5 | $47 | **Save $9,023/month** |
| Deepgram + Cartesia + GPT-4-Turbo | $112 | **Save $8,958/month** |
| OpenAI Realtime API | $9,070 | Baseline |

### Example: 100,000 minutes/month (high volume)

| Configuration | Monthly Cost | Savings vs Realtime |
|--------------|--------------|---------------------|
| Deepgram + Cartesia + GPT-3.5 | $468 | **Save $90,232/month** |
| Deepgram + Cartesia + GPT-4-Turbo | $1,121 | **Save $89,579/month** |
| OpenAI Realtime API | $90,700 | Baseline |

---

## Latency Comparison

### OpenAI Realtime API
- **End-to-end:** 232-320ms
- Single WebSocket connection
- All processing in one API call

### Custom Provider (Deepgram + Cartesia + OpenAI)
- **STT (Deepgram):** 100-150ms
- **LLM (OpenAI):** 200-400ms
- **TTS (Cartesia):** 80-120ms
- **Total:** 380-670ms
- **Difference:** ~150-350ms slower

**Trade-off:** Pay 2-3x more latency to save 99% in costs

---

## Testing Methodology

### Assumptions

1. **Call Duration:** 1 minute average
2. **Conversation Rate:** 2.5 exchanges per minute
3. **Words Per Minute:** 150 words (~750 characters)
4. **Tokens Per Exchange:**
   - Input: 50 tokens
   - Output: 75 tokens

### OpenAI Realtime Token Estimates

- **Audio Input:** ~50 tokens/second = 3,000 tokens/minute
- **Audio Output:** ~50 tokens/second = 3,000 tokens/minute
- **Text Input:** ~200 tokens/minute (context)
- **Text Output:** ~300 tokens/minute (generation)

### Pricing Sources

- **OpenAI:** https://openai.com/api/pricing/
- **Deepgram:** https://deepgram.com/pricing
- **Cartesia:** https://cartesia.ai/pricing
- **ElevenLabs:** https://elevenlabs.io/pricing

All prices current as of January 2025.

---

## Real-World Testing

### Make a Test Call

1. Create an assistant with specific providers
2. Make a 1-minute test call
3. Check actual costs in database

### Track Actual Costs

```bash
# View all calls from last 24 hours
python3 track_live_call_costs.py

# Watch live updates
python3 track_live_call_costs.py --watch

# Export detailed report
python3 track_live_call_costs.py --hours 168 > weekly_report.txt
```

### Monitor in Production

```bash
# Add to cron for daily reports
0 9 * * * cd /path/to/convis && python3 track_live_call_costs.py --hours 24 | mail -s "Daily Call Costs" admin@convis.ai
```

---

## Recommendations Summary

### 🥇 For Production (Best Choice)
**Deepgram nova-2 + Cartesia sonic + GPT-4-turbo**
- Cost: $0.0112/min ($11.21 per 1K minutes)
- Quality: Excellent
- Latency: 380-670ms
- Savings: 98.8% vs Realtime

### 🥈 For Cost Optimization
**Deepgram nova-2 + Cartesia sonic + GPT-3.5-turbo**
- Cost: $0.0047/min ($4.68 per 1K minutes)
- Quality: Good
- Latency: 380-670ms
- Savings: 99.5% vs Realtime

### 🥉 For Premium Quality
**Deepgram nova-2 + ElevenLabs turbo_v2 + GPT-4**
- Cost: $0.0194/min ($19.41 per 1K minutes)
- Quality: Best voice quality
- Latency: 380-670ms
- Savings: 97.9% vs Realtime

### ⚠️ Avoid for Production
**OpenAI Realtime API**
- Cost: $0.9070/min ($907 per 1K minutes)
- Only use for low-volume testing/demos

---

## Troubleshooting

### "No calls found"
- Check date range with `--hours`
- Verify MongoDB connection
- Ensure calls have duration field

### "Cost calculation error"
- Check assistant configuration in database
- Verify provider fields are populated
- Review logs for missing data

### Pricing Outdated
- Update `PRICING` dict in both scripts
- Check latest provider pricing pages
- Test with actual API usage data

---

## Files Generated

- `call_cost_analysis.json` - Detailed cost comparison data
- Export results for reporting tools
- Import into spreadsheets for analysis

---

## Next Steps

1. ✅ Run `test_call_costs.py` to see comparisons
2. ✅ Make test calls with different provider combinations
3. ✅ Use `track_live_call_costs.py` to verify actual costs
4. ✅ Choose optimal configuration for your use case
5. ✅ Deploy and monitor production costs

---

## Support

For questions or issues:
- Check logs: `docker logs convis-api`
- Review pricing updates
- Test with 1-minute calls first
- Contact: admin@convis.ai
