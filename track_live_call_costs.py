#!/usr/bin/env python3
"""
Live Call Cost Tracking Script
Monitors actual API calls and calculates real-time costs
"""

import asyncio
import sys
import os
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from motor.motor_asyncio import AsyncIOMotorClient
from bson import ObjectId
import statistics

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'convis-api'))

# MongoDB connection
MONGODB_URI = "mongodb+srv://psitech:Psitech123@pms.ijqbdmu.mongodb.net/?retryWrites=true&w=majority"
DATABASE_NAME = "convis_python"

# Pricing (same as test_call_costs.py)
PRICING = {
    "openai_realtime": {
        "audio_input": 100 / 1_000_000,  # $100 per 1M input tokens
        "audio_output": 200 / 1_000_000,  # $200 per 1M output tokens
        "text_input": 5 / 1_000_000,  # $5 per 1M tokens
        "text_output": 20 / 1_000_000,  # $20 per 1M tokens
    },
    "deepgram": {
        "nova-2": 0.0043 / 60,
        "nova-2-medical": 0.0059 / 60,
        "nova-2-phonecall": 0.0059 / 60,
    },
    "cartesia": {
        "sonic": 0.00005 / 1000
    },
    "elevenlabs": {
        "eleven_turbo_v2": 0.00015 / 1000,
        "eleven_turbo_v2_5": 0.00015 / 1000,
    },
    "openai_llm": {
        "gpt-4": {"input": 0.03 / 1000, "output": 0.06 / 1000},
        "gpt-4-turbo": {"input": 0.01 / 1000, "output": 0.03 / 1000},
        "gpt-3.5-turbo": {"input": 0.0005 / 1000, "output": 0.0015 / 1000},
    }
}


class LiveCallCostTracker:
    """Track costs from actual calls in the database"""

    def __init__(self, mongodb_uri: str, database_name: str):
        self.client = AsyncIOMotorClient(mongodb_uri)
        self.db = self.client[database_name]
        self.calls_collection = self.db['calls']
        self.interactions_collection = self.db['call_interactions']

    async def get_recent_calls(
        self,
        hours: int = 24,
        user_id: Optional[str] = None,
        provider: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Get recent calls from database"""

        query: Dict[str, Any] = {
            "created_at": {
                "$gte": datetime.utcnow() - timedelta(hours=hours)
            }
        }

        if user_id:
            query["user_id"] = ObjectId(user_id)

        if provider:
            query["provider"] = provider

        calls = []
        async for call in self.calls_collection.find(query):
            calls.append(call)

        return calls

    def calculate_call_cost(self, call: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate cost for a single call"""

        duration_seconds = call.get("duration", 0) or 0
        duration_minutes = duration_seconds / 60

        provider = call.get("provider", "").lower()
        assistant_config = call.get("assistant_config", {})

        # Extract provider info
        asr_provider = assistant_config.get("asr_provider", "deepgram")
        tts_provider = assistant_config.get("tts_provider", "cartesia")
        llm_model = assistant_config.get("llm_model", "gpt-4-turbo")

        cost_breakdown = {}
        total_cost = 0

        if provider == "twilio" and assistant_config.get("use_realtime_api"):
            # OpenAI Realtime API
            # Estimate from duration
            audio_input_tokens = duration_minutes * 2400
            audio_output_tokens = duration_minutes * 2400
            text_input_tokens = duration_minutes * 100
            text_output_tokens = duration_minutes * 150

            cost_breakdown = {
                "provider_type": "openai_realtime",
                "audio_input": audio_input_tokens * PRICING["openai_realtime"]["audio_input"],
                "audio_output": audio_output_tokens * PRICING["openai_realtime"]["audio_output"],
                "text_input": text_input_tokens * PRICING["openai_realtime"]["text_input"],
                "text_output": text_output_tokens * PRICING["openai_realtime"]["text_output"],
            }
            total_cost = sum(cost_breakdown.values()) - cost_breakdown["provider_type"]

        else:
            # Custom Provider
            # STT Cost
            stt_model = assistant_config.get("asr_model", "nova-2")
            if asr_provider == "deepgram" and stt_model in PRICING["deepgram"]:
                stt_cost = PRICING["deepgram"][stt_model] * duration_seconds
            else:
                stt_cost = PRICING["deepgram"]["nova-2"] * duration_seconds

            # TTS Cost (estimate ~150 words/min = ~750 chars/min)
            chars_per_minute = 750
            total_chars = chars_per_minute * duration_minutes

            if tts_provider == "cartesia":
                tts_cost = PRICING["cartesia"]["sonic"] * total_chars
            elif tts_provider == "elevenlabs":
                tts_model = assistant_config.get("tts_model", "eleven_turbo_v2")
                tts_cost = PRICING["elevenlabs"].get(tts_model, PRICING["elevenlabs"]["eleven_turbo_v2"]) * total_chars
            else:
                tts_cost = 0

            # LLM Cost (estimate 2.5 exchanges/min, 50 input + 75 output tokens each)
            exchanges = 2.5 * duration_minutes
            llm_input_tokens = 50 * exchanges
            llm_output_tokens = 75 * exchanges

            if llm_model in PRICING["openai_llm"]:
                llm_input_cost = llm_input_tokens * PRICING["openai_llm"][llm_model]["input"]
                llm_output_cost = llm_output_tokens * PRICING["openai_llm"][llm_model]["output"]
            else:
                llm_input_cost = llm_input_tokens * PRICING["openai_llm"]["gpt-4-turbo"]["input"]
                llm_output_cost = llm_output_tokens * PRICING["openai_llm"]["gpt-4-turbo"]["output"]

            llm_cost = llm_input_cost + llm_output_cost

            cost_breakdown = {
                "provider_type": "custom",
                "stt": stt_cost,
                "tts": tts_cost,
                "llm": llm_cost,
                "stt_provider": asr_provider,
                "tts_provider": tts_provider,
                "llm_model": llm_model
            }
            total_cost = stt_cost + tts_cost + llm_cost

        return {
            "call_id": str(call.get("_id")),
            "duration_seconds": duration_seconds,
            "duration_minutes": duration_minutes,
            "provider": provider,
            "cost_breakdown": cost_breakdown,
            "total_cost": total_cost,
            "cost_per_minute": total_cost / duration_minutes if duration_minutes > 0 else 0,
            "created_at": call.get("created_at")
        }

    async def analyze_calls(
        self,
        hours: int = 24,
        user_id: Optional[str] = None,
        provider: Optional[str] = None
    ) -> Dict[str, Any]:
        """Analyze costs for recent calls"""

        calls = await self.get_recent_calls(hours, user_id, provider)

        if not calls:
            return {
                "total_calls": 0,
                "message": f"No calls found in the last {hours} hours"
            }

        # Calculate cost for each call
        call_costs = []
        for call in calls:
            try:
                cost_info = self.calculate_call_cost(call)
                call_costs.append(cost_info)
            except Exception as e:
                print(f"Error calculating cost for call {call.get('_id')}: {e}")

        if not call_costs:
            return {
                "total_calls": len(calls),
                "message": "Could not calculate costs for any calls"
            }

        # Aggregate statistics
        total_duration = sum(c["duration_seconds"] for c in call_costs)
        total_cost = sum(c["total_cost"] for c in call_costs)
        costs_per_minute = [c["cost_per_minute"] for c in call_costs if c["cost_per_minute"] > 0]

        # Group by provider type
        realtime_calls = [c for c in call_costs if c["cost_breakdown"]["provider_type"] == "openai_realtime"]
        custom_calls = [c for c in call_costs if c["cost_breakdown"]["provider_type"] == "custom"]

        return {
            "period": f"Last {hours} hours",
            "total_calls": len(call_costs),
            "total_duration_minutes": total_duration / 60,
            "total_cost": total_cost,
            "average_cost_per_minute": statistics.mean(costs_per_minute) if costs_per_minute else 0,
            "median_cost_per_minute": statistics.median(costs_per_minute) if costs_per_minute else 0,
            "breakdown": {
                "realtime_api": {
                    "calls": len(realtime_calls),
                    "total_cost": sum(c["total_cost"] for c in realtime_calls),
                    "avg_cost_per_minute": statistics.mean([c["cost_per_minute"] for c in realtime_calls]) if realtime_calls else 0
                },
                "custom_provider": {
                    "calls": len(custom_calls),
                    "total_cost": sum(c["total_cost"] for c in custom_calls),
                    "avg_cost_per_minute": statistics.mean([c["cost_per_minute"] for c in custom_calls]) if custom_calls else 0
                }
            },
            "call_details": call_costs
        }

    def print_analysis(self, analysis: Dict[str, Any]):
        """Print formatted analysis"""

        print("\n" + "="*100)
        print(" LIVE CALL COST ANALYSIS")
        print("="*100)

        if analysis.get("total_calls", 0) == 0:
            print(f"\n{analysis.get('message', 'No calls found')}\n")
            return

        print(f"\nPeriod: {analysis['period']}")
        print(f"Total Calls: {analysis['total_calls']}")
        print(f"Total Duration: {analysis['total_duration_minutes']:.2f} minutes")
        print(f"Total Cost: ${analysis['total_cost']:.4f}")
        print(f"Average Cost/Min: ${analysis['average_cost_per_minute']:.4f}")
        print(f"Median Cost/Min: ${analysis['median_cost_per_minute']:.4f}")

        print("\n" + "-"*100)
        print(" BY PROVIDER TYPE")
        print("-"*100)

        breakdown = analysis["breakdown"]

        print(f"\nOpenAI Realtime API:")
        print(f"  Calls: {breakdown['realtime_api']['calls']}")
        print(f"  Total Cost: ${breakdown['realtime_api']['total_cost']:.4f}")
        print(f"  Avg Cost/Min: ${breakdown['realtime_api']['avg_cost_per_minute']:.4f}")

        print(f"\nCustom Provider:")
        print(f"  Calls: {breakdown['custom_provider']['calls']}")
        print(f"  Total Cost: ${breakdown['custom_provider']['total_cost']:.4f}")
        print(f"  Avg Cost/Min: ${breakdown['custom_provider']['avg_cost_per_minute']:.4f}")

        if breakdown['custom_provider']['calls'] > 0 and breakdown['realtime_api']['calls'] > 0:
            savings = breakdown['realtime_api']['avg_cost_per_minute'] - breakdown['custom_provider']['avg_cost_per_minute']
            savings_pct = (savings / breakdown['realtime_api']['avg_cost_per_minute']) * 100
            print(f"\n💰 Savings with Custom Provider: ${savings:.4f}/min ({savings_pct:.1f}% cheaper)")

        print("\n" + "-"*100)
        print(" RECENT CALLS (Last 10)")
        print("-"*100)

        # Show last 10 calls
        recent_calls = sorted(
            analysis["call_details"],
            key=lambda x: x.get("created_at", datetime.min),
            reverse=True
        )[:10]

        print(f"\n{'Time':<20} {'Duration':<12} {'Provider':<25} {'Cost':<12} {'Cost/Min':<12}")
        print("-"*100)

        for call in recent_calls:
            time_str = call["created_at"].strftime("%Y-%m-%d %H:%M") if call.get("created_at") else "Unknown"
            duration_str = f"{call['duration_minutes']:.2f} min"

            if call["cost_breakdown"]["provider_type"] == "openai_realtime":
                provider_str = "OpenAI Realtime"
            else:
                provider_str = f"{call['cost_breakdown']['stt_provider']}+{call['cost_breakdown']['tts_provider']}"

            cost_str = f"${call['total_cost']:.4f}"
            cost_per_min_str = f"${call['cost_per_minute']:.4f}"

            print(f"{time_str:<20} {duration_str:<12} {provider_str:<25} {cost_str:<12} {cost_per_min_str:<12}")

        print("\n" + "="*100 + "\n")

    async def close(self):
        """Close database connection"""
        self.client.close()


async def main():
    """Main function"""

    import argparse

    parser = argparse.ArgumentParser(description="Track live call costs from database")
    parser.add_argument("--hours", type=int, default=24, help="Hours to look back (default: 24)")
    parser.add_argument("--user-id", type=str, help="Filter by user ID")
    parser.add_argument("--provider", type=str, help="Filter by provider (twilio/frejun)")
    parser.add_argument("--watch", action="store_true", help="Watch mode - update every 30 seconds")

    args = parser.parse_args()

    tracker = LiveCallCostTracker(MONGODB_URI, DATABASE_NAME)

    try:
        if args.watch:
            print("Starting watch mode (updates every 30 seconds, Ctrl+C to stop)...")
            while True:
                analysis = await tracker.analyze_calls(args.hours, args.user_id, args.provider)
                tracker.print_analysis(analysis)
                await asyncio.sleep(30)
        else:
            analysis = await tracker.analyze_calls(args.hours, args.user_id, args.provider)
            tracker.print_analysis(analysis)

    except KeyboardInterrupt:
        print("\n\nStopped by user")
    finally:
        await tracker.close()


if __name__ == "__main__":
    asyncio.run(main())
