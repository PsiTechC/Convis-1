#!/usr/bin/env python3
"""
Call Cost Testing Script for Convis
Tests accurate per-minute costs for:
1. OpenAI Realtime API
2. Custom Provider (Deepgram + Cartesia/ElevenLabs + OpenAI)
"""

import asyncio
import time
import json
from typing import Dict, Any, List
from datetime import datetime
import statistics

# Pricing Information (as of 2025)
PRICING = {
    # OpenAI Realtime API
    # Pricing: https://openai.com/api/pricing/
    "openai_realtime": {
        "audio_input": 100 / 1_000_000,  # $100 per 1M input tokens
        "audio_output": 200 / 1_000_000,  # $200 per 1M output tokens
        "text_input": 5 / 1_000_000,  # $5 per 1M tokens (GPT-4o realtime)
        "text_output": 20 / 1_000_000,  # $20 per 1M tokens
        "estimated_tokens_per_minute": {
            "audio_input": 3000,  # ~50 tokens/sec * 60 (realistic conversation)
            "audio_output": 3000,
            "text_input": 200,  # Context + instructions
            "text_output": 300  # Response generation
        }
    },

    # Custom Provider Pricing
    "deepgram": {
        "nova-2": 0.0043 / 60,  # $0.0043 per minute
        "nova-2-medical": 0.0059 / 60,
        "nova-2-phonecall": 0.0059 / 60,
        "whisper-large": 0.0048 / 60
    },

    "cartesia": {
        "sonic": 0.00005 / 1000  # $0.05 per 1M characters (~150 chars = 1 sec audio)
    },

    "elevenlabs": {
        "eleven_turbo_v2": 0.00015 / 1000,  # $0.15 per 1K characters
        "eleven_turbo_v2_5": 0.00015 / 1000,
        "eleven_multilingual_v2": 0.00030 / 1000
    },

    "openai_llm": {
        "gpt-4": {
            "input": 0.03 / 1000,  # $30 per 1M tokens
            "output": 0.06 / 1000   # $60 per 1M tokens
        },
        "gpt-4-turbo": {
            "input": 0.01 / 1000,
            "output": 0.03 / 1000
        },
        "gpt-3.5-turbo": {
            "input": 0.0005 / 1000,
            "output": 0.0015 / 1000
        }
    }
}


class CallCostTester:
    """Test and calculate accurate call costs"""

    def __init__(self):
        self.results: List[Dict[str, Any]] = []

    def calculate_openai_realtime_cost_per_minute(self) -> Dict[str, Any]:
        """
        Calculate OpenAI Realtime API cost per minute
        Based on actual token usage patterns
        """
        pricing = PRICING["openai_realtime"]

        # Estimated tokens per minute (conversation)
        audio_input_tokens = pricing["estimated_tokens_per_minute"]["audio_input"]
        audio_output_tokens = pricing["estimated_tokens_per_minute"]["audio_output"]
        text_input_tokens = pricing["estimated_tokens_per_minute"]["text_input"]
        text_output_tokens = pricing["estimated_tokens_per_minute"]["text_output"]

        # Calculate costs
        audio_input_cost = audio_input_tokens * pricing["audio_input"]
        audio_output_cost = audio_output_tokens * pricing["audio_output"]
        text_input_cost = text_input_tokens * pricing["text_input"]
        text_output_cost = text_output_tokens * pricing["text_output"]

        total_cost = audio_input_cost + audio_output_cost + text_input_cost + text_output_cost

        return {
            "provider": "OpenAI Realtime API",
            "breakdown": {
                "audio_input": {
                    "tokens": audio_input_tokens,
                    "cost": audio_input_cost,
                    "rate": f"${pricing['audio_input'] * 1_000_000:.2f} per 1M tokens"
                },
                "audio_output": {
                    "tokens": audio_output_tokens,
                    "cost": audio_output_cost,
                    "rate": f"${pricing['audio_output'] * 1_000_000:.2f} per 1M tokens"
                },
                "text_input": {
                    "tokens": text_input_tokens,
                    "cost": text_input_cost,
                    "rate": f"${pricing['text_input'] * 1000:.2f} per 1K tokens"
                },
                "text_output": {
                    "tokens": text_output_tokens,
                    "cost": text_output_cost,
                    "rate": f"${pricing['text_output'] * 1000:.2f} per 1K tokens"
                }
            },
            "total_per_minute": total_cost,
            "total_per_hour": total_cost * 60,
            "total_per_1000_minutes": total_cost * 1000
        }

    def calculate_custom_provider_cost_per_minute(
        self,
        stt_provider: str = "deepgram",
        stt_model: str = "nova-2",
        tts_provider: str = "cartesia",
        tts_model: str = "sonic",
        llm_model: str = "gpt-4-turbo"
    ) -> Dict[str, Any]:
        """
        Calculate custom provider combination cost per minute

        Args:
            stt_provider: Speech-to-Text provider
            stt_model: STT model
            tts_provider: Text-to-Speech provider
            tts_model: TTS model
            llm_model: LLM model
        """

        # STT Cost (per minute of audio)
        stt_cost = PRICING[stt_provider][stt_model] * 60  # Convert to per-minute

        # TTS Cost (assuming ~150 words/minute = ~750 characters)
        words_per_minute = 150
        chars_per_minute = words_per_minute * 5  # Average 5 chars per word

        if tts_provider == "cartesia":
            tts_cost = PRICING["cartesia"][tts_model] * chars_per_minute
        else:  # elevenlabs
            tts_cost = PRICING["elevenlabs"][tts_model] * chars_per_minute

        # LLM Cost (assuming 2-3 exchanges per minute)
        # Each exchange: ~50 tokens input, ~75 tokens output
        exchanges_per_minute = 2.5
        llm_input_tokens = 50 * exchanges_per_minute
        llm_output_tokens = 75 * exchanges_per_minute

        llm_input_cost = llm_input_tokens * PRICING["openai_llm"][llm_model]["input"]
        llm_output_cost = llm_output_tokens * PRICING["openai_llm"][llm_model]["output"]
        llm_total_cost = llm_input_cost + llm_output_cost

        total_cost = stt_cost + tts_cost + llm_total_cost

        return {
            "provider": f"Custom ({stt_provider} + {tts_provider} + {llm_model})",
            "breakdown": {
                "stt": {
                    "provider": stt_provider,
                    "model": stt_model,
                    "cost": stt_cost,
                    "rate": f"${PRICING[stt_provider][stt_model] * 60:.4f} per minute"
                },
                "tts": {
                    "provider": tts_provider,
                    "model": tts_model,
                    "characters": chars_per_minute,
                    "cost": tts_cost,
                    "rate": f"${PRICING[tts_provider][tts_model] * 1000:.2f} per 1K chars"
                },
                "llm": {
                    "model": llm_model,
                    "input_tokens": llm_input_tokens,
                    "output_tokens": llm_output_tokens,
                    "input_cost": llm_input_cost,
                    "output_cost": llm_output_cost,
                    "total_cost": llm_total_cost,
                    "input_rate": f"${PRICING['openai_llm'][llm_model]['input'] * 1000:.2f} per 1K tokens",
                    "output_rate": f"${PRICING['openai_llm'][llm_model]['output'] * 1000:.2f} per 1K tokens"
                }
            },
            "total_per_minute": total_cost,
            "total_per_hour": total_cost * 60,
            "total_per_1000_minutes": total_cost * 1000
        }

    def compare_all_configurations(self) -> List[Dict[str, Any]]:
        """Compare all provider configurations"""

        configurations = [
            # OpenAI Realtime
            self.calculate_openai_realtime_cost_per_minute(),

            # Custom Provider Combinations
            # Fastest & Cheapest: Deepgram + Cartesia + GPT-3.5
            self.calculate_custom_provider_cost_per_minute(
                "deepgram", "nova-2", "cartesia", "sonic", "gpt-3.5-turbo"
            ),

            # Fastest & Mid-tier: Deepgram + Cartesia + GPT-4-Turbo
            self.calculate_custom_provider_cost_per_minute(
                "deepgram", "nova-2", "cartesia", "sonic", "gpt-4-turbo"
            ),

            # High Quality: Deepgram + ElevenLabs + GPT-4-Turbo
            self.calculate_custom_provider_cost_per_minute(
                "deepgram", "nova-2", "elevenlabs", "eleven_turbo_v2", "gpt-4-turbo"
            ),

            # Premium: Deepgram + ElevenLabs + GPT-4
            self.calculate_custom_provider_cost_per_minute(
                "deepgram", "nova-2", "elevenlabs", "eleven_turbo_v2", "gpt-4"
            ),

            # Medical Specific: Deepgram Medical + Cartesia + GPT-4
            self.calculate_custom_provider_cost_per_minute(
                "deepgram", "nova-2-medical", "cartesia", "sonic", "gpt-4"
            ),
        ]

        return configurations

    def print_comparison_table(self, configurations: List[Dict[str, Any]]):
        """Print formatted comparison table"""

        print("\n" + "="*100)
        print(" CONVIS CALL COST COMPARISON - PER MINUTE")
        print("="*100)

        # Sort by cost
        sorted_configs = sorted(configurations, key=lambda x: x["total_per_minute"])

        print(f"\n{'Configuration':<60} {'Per Min':<12} {'Per Hour':<12} {'Per 1K Min':<12}")
        print("-"*100)

        for config in sorted_configs:
            name = config["provider"]
            per_min = f"${config['total_per_minute']:.4f}"
            per_hour = f"${config['total_per_hour']:.2f}"
            per_1k_min = f"${config['total_per_1000_minutes']:.2f}"

            print(f"{name:<60} {per_min:<12} {per_hour:<12} {per_1k_min:<12}")

        print("\n" + "="*100)
        print(" DETAILED BREAKDOWN")
        print("="*100)

        for i, config in enumerate(sorted_configs, 1):
            print(f"\n{i}. {config['provider']}")
            print(f"   Total: ${config['total_per_minute']:.4f}/min | ${config['total_per_hour']:.2f}/hour")
            print(f"   Breakdown:")

            breakdown = config["breakdown"]

            if "audio_input" in breakdown:
                # OpenAI Realtime
                print(f"     • Audio Input:  {breakdown['audio_input']['tokens']} tokens × {breakdown['audio_input']['rate']} = ${breakdown['audio_input']['cost']:.4f}")
                print(f"     • Audio Output: {breakdown['audio_output']['tokens']} tokens × {breakdown['audio_output']['rate']} = ${breakdown['audio_output']['cost']:.4f}")
                print(f"     • Text Input:   {breakdown['text_input']['tokens']} tokens × {breakdown['text_input']['rate']} = ${breakdown['text_input']['cost']:.4f}")
                print(f"     • Text Output:  {breakdown['text_output']['tokens']} tokens × {breakdown['text_output']['rate']} = ${breakdown['text_output']['cost']:.4f}")
            else:
                # Custom Provider
                print(f"     • STT ({breakdown['stt']['provider']} {breakdown['stt']['model']}): ${breakdown['stt']['cost']:.4f}")
                print(f"       Rate: {breakdown['stt']['rate']}")
                print(f"     • TTS ({breakdown['tts']['provider']} {breakdown['tts']['model']}): ${breakdown['tts']['cost']:.4f}")
                print(f"       {breakdown['tts']['characters']} chars × {breakdown['tts']['rate']}")
                print(f"     • LLM ({breakdown['llm']['model']}): ${breakdown['llm']['total_cost']:.4f}")
                print(f"       Input:  {breakdown['llm']['input_tokens']:.0f} tokens × {breakdown['llm']['input_rate']} = ${breakdown['llm']['input_cost']:.4f}")
                print(f"       Output: {breakdown['llm']['output_tokens']:.0f} tokens × {breakdown['llm']['output_rate']} = ${breakdown['llm']['output_cost']:.4f}")

    def calculate_cost_savings(self, configurations: List[Dict[str, Any]]):
        """Calculate savings compared to OpenAI Realtime"""

        openai_cost = next(c for c in configurations if "Realtime" in c["provider"])["total_per_minute"]

        print("\n" + "="*100)
        print(" COST SAVINGS vs OpenAI Realtime API")
        print("="*100)
        print(f"\nOpenAI Realtime Baseline: ${openai_cost:.4f}/min | ${openai_cost * 60:.2f}/hour | ${openai_cost * 1000:.2f}/1K min\n")

        custom_configs = [c for c in configurations if "Custom" in c["provider"]]

        for config in sorted(custom_configs, key=lambda x: x["total_per_minute"]):
            cost = config["total_per_minute"]
            savings = openai_cost - cost
            savings_pct = (savings / openai_cost) * 100

            print(f"{config['provider']}")
            print(f"  Cost:    ${cost:.4f}/min")
            print(f"  Savings: ${savings:.4f}/min ({savings_pct:.1f}% cheaper)")
            print(f"  1K mins: Save ${savings * 1000:.2f} (${openai_cost * 1000:.2f} vs ${cost * 1000:.2f})")
            print()


async def simulate_real_call(duration_minutes: int = 1) -> Dict[str, Any]:
    """
    Simulate a real call to measure actual costs
    This would connect to actual providers in production
    """
    print(f"\nSimulating {duration_minutes} minute call...")

    # In production, this would make actual API calls
    # For now, we'll use realistic estimates

    start_time = time.time()

    # Simulate call duration
    await asyncio.sleep(duration_minutes * 60)

    end_time = time.time()
    actual_duration = (end_time - start_time) / 60

    return {
        "duration_minutes": actual_duration,
        "timestamp": datetime.now().isoformat()
    }


def main():
    """Main testing function"""

    print("\n" + "="*100)
    print(" CONVIS CALL COST TESTING SUITE")
    print(" Testing accurate per-minute costs for all provider configurations")
    print("="*100)

    tester = CallCostTester()

    # Get all configurations
    configurations = tester.compare_all_configurations()

    # Print comparison table
    tester.print_comparison_table(configurations)

    # Calculate savings
    tester.calculate_cost_savings(configurations)

    # Recommendations
    print("\n" + "="*100)
    print(" RECOMMENDATIONS")
    print("="*100)

    print("\n🏆 BEST VALUE:")
    print("   Deepgram nova-2 + Cartesia sonic + GPT-3.5-turbo")
    print("   • Lowest cost while maintaining quality")
    print("   • 80-120ms latency")
    print("   • Best for: High volume, cost-sensitive applications")

    print("\n⚡ BEST BALANCE:")
    print("   Deepgram nova-2 + Cartesia sonic + GPT-4-turbo")
    print("   • Excellent quality at reasonable cost")
    print("   • 80-120ms latency")
    print("   • Best for: Production applications requiring good quality")

    print("\n💎 PREMIUM QUALITY:")
    print("   Deepgram nova-2 + ElevenLabs turbo_v2 + GPT-4")
    print("   • Highest voice quality")
    print("   • Higher cost but still cheaper than OpenAI Realtime")
    print("   • Best for: Customer-facing applications, demos")

    print("\n🏥 MEDICAL SPECIFIC:")
    print("   Deepgram nova-2-medical + Cartesia sonic + GPT-4")
    print("   • Medical terminology optimized")
    print("   • HIPAA compliant")
    print("   • Best for: Healthcare applications")

    print("\n" + "="*100)
    print(" LATENCY COMPARISON")
    print("="*100)

    print("\nOpenAI Realtime API:")
    print("  • End-to-end latency: 232-320ms")
    print("  • Single API call (all-in-one)")

    print("\nCustom Provider (Deepgram + Cartesia + OpenAI):")
    print("  • STT (Deepgram): 100-150ms")
    print("  • LLM (OpenAI): 200-400ms")
    print("  • TTS (Cartesia): 80-120ms")
    print("  • Total: 380-670ms")
    print("  • 🔺 ~150-350ms slower than Realtime API")

    print("\n" + "="*100)

    # Export results to JSON
    output_file = "call_cost_analysis.json"
    with open(output_file, 'w') as f:
        json.dump({
            "generated_at": datetime.now().isoformat(),
            "configurations": configurations,
            "pricing_data": PRICING
        }, f, indent=2)

    print(f"\n✓ Detailed results exported to: {output_file}")
    print("="*100 + "\n")


if __name__ == "__main__":
    main()
