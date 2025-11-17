"""
Test TTS Providers - Quick diagnostic script
"""
import asyncio
import sys
import os

# Add convis-api to path
sys.path.insert(0, '/media/shubham/Shubham/PSITECH/Convis-main/convis-api')

from app.providers.tts import CartesiaTTS, ElevenLabsTTS, OpenAITTS

async def test_provider(name, provider_class, api_key_env, voice):
    """Test a single TTS provider"""
    print(f"\n{'='*60}")
    print(f"Testing {name} TTS Provider")
    print(f"{'='*60}")

    # Check API key
    api_key = os.getenv(api_key_env)
    if not api_key:
        print(f"❌ {api_key_env} not set in environment")
        return False

    print(f"✓ API key found: {api_key[:10]}...")

    # Try to instantiate
    try:
        provider = provider_class(api_key=api_key, voice=voice)
        print(f"✓ Provider instantiated successfully")
    except Exception as e:
        print(f"❌ Failed to instantiate: {e}")
        return False

    # Try to synthesize
    test_text = "Hello, this is a test."
    print(f"\n🔊 Synthesizing: \"{test_text}\"")

    try:
        audio_bytes = await provider.synthesize(test_text)

        if not audio_bytes or len(audio_bytes) == 0:
            print(f"❌ Synthesis returned EMPTY audio")
            return False

        print(f"✅ Synthesis successful: {len(audio_bytes)} bytes")
        print(f"   └─ Latency estimate: {provider.get_latency_ms()}ms")
        print(f"   └─ Cost per minute: ${provider.get_cost_per_minute()}")
        return True

    except Exception as e:
        print(f"❌ Synthesis failed: {e}")
        import traceback
        traceback.print_exc()
        return False

async def main():
    """Test all TTS providers"""
    print("\n" + "="*60)
    print("TTS PROVIDER DIAGNOSTIC TEST")
    print("="*60)

    results = {}

    # Test Cartesia
    results['Cartesia'] = await test_provider(
        "Cartesia",
        CartesiaTTS,
        "CARTESIA_API_KEY",
        "sonic"
    )

    # Test ElevenLabs
    results['ElevenLabs'] = await test_provider(
        "ElevenLabs",
        ElevenLabsTTS,
        "ELEVENLABS_API_KEY",
        "rachel"
    )

    # Test OpenAI TTS
    results['OpenAI TTS'] = await test_provider(
        "OpenAI TTS",
        OpenAITTS,
        "OPENAI_API_KEY",
        "alloy"
    )

    # Summary
    print("\n" + "="*60)
    print("SUMMARY")
    print("="*60)
    for provider, success in results.items():
        status = "✅ WORKING" if success else "❌ FAILED"
        print(f"{provider:20} {status}")

    print("\n")

if __name__ == "__main__":
    asyncio.run(main())
