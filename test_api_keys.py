"""
Test Cartesia and Sarvam API Keys
"""
import asyncio
import sys
sys.path.insert(0, '/media/shubham/Shubham/PSITECH/Convis-main/convis-api')

from app.providers.tts import CartesiaTTS, SarvamTTS

async def test_cartesia():
    """Test Cartesia API"""
    print("\n" + "="*60)
    print("Testing Cartesia TTS")
    print("="*60)

    api_key = "sk_car_SmAtAJmg3vK1NwWKhQmz5o"

    try:
        provider = CartesiaTTS(api_key=api_key, voice="sonic")
        print("✓ Cartesia provider instantiated")

        text = "Hello, this is a test."
        print(f"\n🔊 Synthesizing: \"{text}\"")

        audio = await provider.synthesize(text)

        if audio and len(audio) > 0:
            print(f"✅ SUCCESS: Generated {len(audio)} bytes of audio")
            return True
        else:
            print(f"❌ FAILED: No audio generated")
            return False

    except Exception as e:
        print(f"❌ FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False

async def test_sarvam():
    """Test Sarvam API"""
    print("\n" + "="*60)
    print("Testing Sarvam TTS")
    print("="*60)

    api_key = "sk_gy9i2lrl_bzSNgiKo3KxjqgNYcBf58CBS"

    try:
        provider = SarvamTTS(api_key=api_key, voice="manisha", language="hi-IN")
        print("✓ Sarvam provider instantiated")

        text = "नमस्ते! यह एक परीक्षण है।"  # "Hello! This is a test." in Hindi
        print(f"\n🔊 Synthesizing: \"{text}\"")

        audio = await provider.synthesize(text)

        if audio and len(audio) > 0:
            print(f"✅ SUCCESS: Generated {len(audio)} bytes of audio")
            return True
        else:
            print(f"❌ FAILED: No audio generated")
            return False

    except Exception as e:
        print(f"❌ FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False

async def main():
    print("\n" + "="*60)
    print("API KEY VALIDATION TEST")
    print("="*60)

    cartesia_ok = await test_cartesia()
    sarvam_ok = await test_sarvam()

    print("\n" + "="*60)
    print("RESULTS")
    print("="*60)
    print(f"Cartesia: {'✅ WORKING' if cartesia_ok else '❌ FAILED'}")
    print(f"Sarvam:   {'✅ WORKING' if sarvam_ok else '❌ FAILED'}")
    print()

if __name__ == "__main__":
    asyncio.run(main())
