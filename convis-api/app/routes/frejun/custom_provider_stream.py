"""
Custom Provider WebSocket Streaming Handler
Handles calls using separate ASR and TTS providers (not OpenAI Realtime API)
"""

import logging
import asyncio
import json
import base64
import audioop
import os
from datetime import datetime
from typing import Optional, Dict, Any
from fastapi import WebSocket, WebSocketDisconnect, HTTPException
from bson import ObjectId

from app.config.database import Database
from app.providers.factory import ProviderFactory
from app.utils.assistant_keys import resolve_provider_keys, resolve_assistant_api_key
from app.utils.twilio_mark_handler import TwilioMarkHandler

logger = logging.getLogger(__name__)


class CustomProviderStreamHandler:
    """
    Handles bidirectional audio streaming using custom ASR/TTS providers.

    Flow:
    1. Receive audio from FreJun (PCM 8kHz)
    2. Convert speech to text using ASR provider (Deepgram/OpenAI)
    3. Send text to LLM for response (OpenAI GPT-4/etc)
    4. Convert response to speech using TTS provider (Cartesia/ElevenLabs/OpenAI)
    5. Stream audio back to FreJun
    """

    def __init__(
        self,
        websocket: WebSocket,
        assistant_config: Dict[str, Any],
        openai_api_key: Optional[str],
        call_id: str,
        platform: str = "frejun",  # "frejun" or "twilio"
        provider_keys: Optional[Dict[str, str]] = None
    ):
        self.websocket = websocket
        self.assistant_config = assistant_config
        self.call_id = call_id
        self.platform = platform  # Track which platform we're on

        # Provider instances
        self.asr_provider = None
        self.tts_provider = None
        self.llm_client = None

        # Conversation state
        self.conversation_history = []
        self.is_running = False
        self.audio_buffer = bytearray()

        # Twilio-specific state
        self.stream_sid = None  # Required for Twilio audio streaming
        self.call_sid = None
        self.mark_handler = TwilioMarkHandler(websocket)  # Bolna-style mark event handler

        # API keys
        self.provider_keys = provider_keys or assistant_config.get("provider_keys") or {}
        if openai_api_key:
            self.provider_keys.setdefault("openai", openai_api_key)
        self.openai_api_key = (
            openai_api_key
            or self.provider_keys.get("openai")
            or os.getenv("OPENAI_API_KEY")
        )

        # Configuration
        self.asr_provider_name = assistant_config.get('asr_provider', 'openai')
        self.tts_provider_name = assistant_config.get('tts_provider', 'openai')
        self.voice = assistant_config.get('voice', 'alloy')
        self.tts_voice = assistant_config.get('tts_voice', self.voice)
        self.temperature = assistant_config.get('temperature', 0.8)
        self.system_message = assistant_config.get('system_message', 'You are a helpful AI assistant.')

        # Add language instruction to system message if not English
        bot_language = assistant_config.get('bot_language', 'en')
        if bot_language and bot_language != 'en':
            language_names = {
                'hi': 'Hindi', 'es': 'Spanish', 'fr': 'French', 'de': 'German',
                'pt': 'Portuguese', 'it': 'Italian', 'ja': 'Japanese', 'ko': 'Korean',
                'ar': 'Arabic', 'ru': 'Russian', 'zh': 'Chinese', 'nl': 'Dutch',
                'pl': 'Polish', 'tr': 'Turkish'
            }
            language_name = language_names.get(bot_language, bot_language.upper())
            self.system_message = f"{self.system_message}\n\nIMPORTANT: You MUST speak and respond ONLY in {language_name}. All your responses should be in {language_name} language."

        # Use greeting exactly as configured by user
        self.greeting = assistant_config.get('greeting', 'Hello! Thanks for calling. How can I help you today?')

        # ASR Configuration
        self.asr_language = assistant_config.get('asr_language', 'en')
        self.asr_model = assistant_config.get('asr_model')
        self.asr_keywords = assistant_config.get('asr_keywords', [])

        # TTS Configuration
        self.tts_model = assistant_config.get('tts_model')
        self.tts_speed = assistant_config.get('tts_speed', 1.0)

        # Transcription & Interruptions
        self.enable_precise_transcript = assistant_config.get('enable_precise_transcript', False)
        self.interruption_threshold = assistant_config.get('interruption_threshold', 2)

        # Voice Response Rate
        self.response_rate = assistant_config.get('response_rate', 'balanced')

        # User Online Detection
        self.check_user_online = assistant_config.get('check_user_online', True)

        # Buffer & Latency Settings
        self.audio_buffer_size = assistant_config.get('audio_buffer_size', 200)

        # LLM Configuration
        self.llm_provider = assistant_config.get('llm_provider', 'openai')
        self.llm_model = assistant_config.get('llm_model')
        self.llm_max_tokens = assistant_config.get('llm_max_tokens', 150)

    async def initialize_providers(self):
        """Initialize ASR, TTS, and LLM providers"""
        try:
            logger.info(f"[CUSTOM] 🔧 === PROVIDER INITIALIZATION START ===")
            logger.info(f"[CUSTOM] 📋 Configuration:")
            logger.info(f"[CUSTOM]   ├─ ASR: {self.asr_provider_name} (model: {self.asr_model}, lang: {self.asr_language})")
            logger.info(f"[CUSTOM]   ├─ TTS: {self.tts_provider_name} (model: {self.tts_model}, voice: {self.tts_voice})")
            logger.info(f"[CUSTOM]   └─ LLM: {self.llm_provider} (model: {self.llm_model})")

            # Initialize ASR provider
            logger.info(f"[CUSTOM] 🎤 Initializing ASR provider: {self.asr_provider_name}")
            # Determine ASR model based on provider and config
            asr_model = self.asr_model
            if not asr_model:
                asr_model = 'nova-2' if self.asr_provider_name == 'deepgram' else 'whisper-1'
                logger.info(f"[CUSTOM]   └─ No model specified, using default: {asr_model}")

            asr_api_key = self.provider_keys.get(self.asr_provider_name)
            if self.asr_provider_name == 'openai':
                asr_api_key = asr_api_key or self.openai_api_key
            elif self.asr_provider_name == 'deepgram':
                asr_api_key = asr_api_key or os.getenv("DEEPGRAM_API_KEY")

            logger.info(f"[CUSTOM]   └─ API key {'✓ found' if asr_api_key else '✗ missing'}")

            if self.asr_provider_name == 'deepgram' and not asr_api_key:
                logger.warning("[CUSTOM] ⚠️ Deepgram key not configured. Falling back to OpenAI Whisper for ASR.")
                self.asr_provider_name = 'openai'
                asr_model = 'whisper-1'
                asr_api_key = self.openai_api_key or os.getenv("OPENAI_API_KEY")

            try:
                logger.info(f"[CUSTOM]   └─ Creating ASR provider instance...")
                self.asr_provider = ProviderFactory.create_asr_provider(
                    provider_name=self.asr_provider_name,
                    api_key=asr_api_key,
                    model=asr_model,
                    language=self.asr_language
                )
                logger.info(f"[CUSTOM] ✅ ASR provider initialized: {self.asr_provider_name}/{asr_model}")
            except Exception as asr_error:
                logger.error(f"[CUSTOM] ❌ Failed to initialize ASR provider '{self.asr_provider_name}': {asr_error}", exc_info=True)
                if self.asr_provider_name != 'openai':
                    logger.warning("[CUSTOM] ⚠️ Falling back to OpenAI Whisper for ASR")
                    self.asr_provider_name = 'openai'
                    self.asr_model = 'whisper-1'
                    self.asr_provider = ProviderFactory.create_asr_provider(
                        provider_name='openai',
                        api_key=self.openai_api_key or os.getenv("OPENAI_API_KEY"),
                        model='whisper-1',
                        language=self.asr_language
                    )
                    logger.info(f"[CUSTOM] ✅ ASR fallback successful: openai/whisper-1")
                else:
                    raise

            # Initialize TTS provider
            logger.info(f"[CUSTOM] 🔊 Initializing TTS provider: {self.tts_provider_name}")
            # Determine TTS model based on provider and config
            tts_model = self.tts_model
            if not tts_model:
                tts_model = 'tts-1' if self.tts_provider_name == 'openai' else None
                if tts_model:
                    logger.info(f"[CUSTOM]   └─ No model specified, using default: {tts_model}")

            tts_api_key = self.provider_keys.get(self.tts_provider_name)
            if self.tts_provider_name == 'openai':
                tts_api_key = tts_api_key or self.openai_api_key
            elif self.tts_provider_name == 'cartesia':
                tts_api_key = tts_api_key or os.getenv("CARTESIA_API_KEY")
            elif self.tts_provider_name == 'elevenlabs':
                tts_api_key = tts_api_key or os.getenv("ELEVENLABS_API_KEY")
            elif self.tts_provider_name == 'sarvam':
                tts_api_key = tts_api_key or os.getenv("SARVAM_API_KEY")

            logger.info(f"[CUSTOM]   └─ API key {'✓ found' if tts_api_key else '✗ missing'}")

            if self.tts_provider_name == 'cartesia' and not tts_api_key:
                logger.warning("[CUSTOM] ⚠️ Cartesia key not configured. Falling back to OpenAI TTS.")
                self.tts_provider_name = 'openai'
                tts_model = 'tts-1'
                tts_api_key = self.openai_api_key or os.getenv("OPENAI_API_KEY")
            elif self.tts_provider_name == 'elevenlabs' and not tts_api_key:
                logger.warning("[CUSTOM] ⚠️ ElevenLabs key not configured. Falling back to OpenAI TTS.")
                self.tts_provider_name = 'openai'
                tts_model = 'tts-1'
                tts_api_key = self.openai_api_key or os.getenv("OPENAI_API_KEY")

            try:
                logger.info(f"[CUSTOM]   └─ Creating TTS provider instance...")
                # Prepare kwargs for provider-specific parameters
                tts_kwargs = {}
                if self.tts_provider_name == 'sarvam':
                    # Sarvam needs language parameter
                    tts_kwargs['language'] = self.language or 'hi-IN'
                    logger.info(f"[CUSTOM]   └─ Sarvam language: {tts_kwargs['language']}")

                self.tts_provider = ProviderFactory.create_tts_provider(
                    provider_name=self.tts_provider_name,
                    api_key=tts_api_key,
                    voice=self.tts_voice or self.voice,
                    **tts_kwargs
                )
                logger.info(f"[CUSTOM] ✅ TTS provider initialized: {self.tts_provider_name}/{tts_model or 'default'} (voice: {self.tts_voice or self.voice})")
            except Exception as tts_error:
                logger.error(f"[CUSTOM] ❌ Failed to initialize TTS provider '{self.tts_provider_name}': {tts_error}", exc_info=True)
                if self.tts_provider_name != 'openai':
                    logger.warning("[CUSTOM] ⚠️ Falling back to OpenAI TTS")
                    self.tts_provider_name = 'openai'
                    self.tts_model = 'tts-1'
                    self.tts_provider = ProviderFactory.create_tts_provider(
                        provider_name='openai',
                        api_key=self.openai_api_key or os.getenv("OPENAI_API_KEY"),
                        voice=self.voice
                    )
                    logger.info(f"[CUSTOM] ✅ TTS fallback successful: openai/tts-1")
                else:
                    raise

            # Initialize LLM client based on provider
            logger.info(f"[CUSTOM] 🤖 Initializing LLM provider: {self.llm_provider}")
            llm_initialized = False
            if self.llm_provider == "openai":
                try:
                    import openai
                    openai_key = self.provider_keys.get('openai') or self.openai_api_key or os.getenv("OPENAI_API_KEY")
                    logger.info(f"[CUSTOM]   └─ API key {'✓ found' if openai_key else '✗ missing'}")
                    if not openai_key:
                        raise RuntimeError("OpenAI API key is not configured")
                    self.llm_client = openai.AsyncOpenAI(api_key=openai_key)
                    llm_initialized = True
                    logger.info(f"[CUSTOM] ✅ LLM initialized: openai/{self.llm_model or 'gpt-4o-mini'}")
                except Exception as openai_error:
                    logger.error(f"[CUSTOM] ❌ Failed to initialize OpenAI LLM client: {openai_error}", exc_info=True)
            elif self.llm_provider == "anthropic":
                try:
                    import anthropic
                    api_key = self.provider_keys.get('anthropic') or os.getenv("ANTHROPIC_API_KEY")
                    if not api_key:
                        raise RuntimeError("ANTHROPIC_API_KEY is not configured")
                    self.llm_client = anthropic.AsyncAnthropic(api_key=api_key)
                    logger.warning("[CUSTOM] ⚠️ Anthropic client initialized but API responses are not yet supported. Falling back to OpenAI.")
                except Exception as anthropic_error:
                    logger.error(f"[CUSTOM] ❌ Failed to initialize Anthropic client: {anthropic_error}", exc_info=True)
            elif self.llm_provider == "groq":
                try:
                    from groq import AsyncGroq
                    api_key = self.provider_keys.get('groq') or os.getenv("GROQ_API_KEY")
                    if not api_key:
                        raise RuntimeError("GROQ_API_KEY is not configured")
                    self.llm_client = AsyncGroq(api_key=api_key)
                    logger.warning("[CUSTOM] ⚠️ Groq client initialized but API responses are not yet supported. Falling back to OpenAI.")
                except Exception as groq_error:
                    logger.error(f"[CUSTOM] ❌ Failed to initialize Groq client: {groq_error}", exc_info=True)

            if not llm_initialized:
                logger.warning("[CUSTOM] ⚠️ LLM provider not initialized, falling back to OpenAI")
                import openai
                fallback_key = self.provider_keys.get('openai') or self.openai_api_key or os.getenv("OPENAI_API_KEY")
                if not fallback_key:
                    raise RuntimeError("No supported LLM provider could be initialized (missing API keys)")
                self.llm_provider = "openai"
                self.llm_client = openai.AsyncOpenAI(api_key=fallback_key)
                if not self.llm_model:
                    self.llm_model = "gpt-4o-mini"
                llm_initialized = True
                logger.info(f"[CUSTOM] ✅ LLM fallback successful: openai/{self.llm_model}")

            # Add system message to conversation history
            self.conversation_history.append({
                "role": "system",
                "content": self.system_message
            })

            logger.info(f"[CUSTOM] Providers initialized successfully (LLM: {self.llm_provider}, Model: {self.llm_model or 'default'})")
            return True

        except Exception as e:
            logger.error(f"[CUSTOM] Error initializing providers: {e}", exc_info=True)
            return False

    async def send_greeting(self):
        """Send initial greeting to caller"""
        try:
            logger.info(f"[CUSTOM] Sending greeting: {self.greeting}")

            # Generate greeting audio
            logger.info(f"[CUSTOM] 🔊 Calling TTS provider to synthesize greeting...")
            greeting_audio = await self.tts_provider.synthesize(self.greeting)
            logger.info(f"[CUSTOM] 🔊 TTS provider returned {len(greeting_audio) if greeting_audio else 0} bytes of audio")

            # Convert audio if needed
            if greeting_audio and len(greeting_audio) > 0:
                # Determine input sample rate based on TTS provider
                input_sample_rate = 8000  # Default for Cartesia
                is_wav_format = False

                if self.tts_provider_name == 'elevenlabs':
                    input_sample_rate = 16000
                elif self.tts_provider_name == 'openai':
                    input_sample_rate = 24000  # OpenAI TTS outputs 24kHz
                elif self.tts_provider_name == 'sarvam':
                    input_sample_rate = 8000
                    is_wav_format = True

                # Step 0: Extract PCM from WAV if needed (for Sarvam)
                if is_wav_format:
                    try:
                        from app.voice_pipeline.helpers.utils import wav_bytes_to_pcm
                        greeting_audio = wav_bytes_to_pcm(greeting_audio)
                        logger.info(f"[CUSTOM] Extracted PCM from WAV: {len(greeting_audio)} bytes")
                    except Exception as wav_error:
                        logger.error(f"[CUSTOM] WAV extraction failed: {wav_error}")

                # Step 1: Resample to 8kHz if needed
                if input_sample_rate != 8000:
                    try:
                        converted_audio, _ = audioop.ratecv(greeting_audio, 2, 1, input_sample_rate, 8000, None)
                        logger.info(f"[CUSTOM] Resampled audio from {input_sample_rate}Hz to 8kHz")
                    except Exception as conv_error:
                        logger.warning(f"[CUSTOM] Audio resampling failed: {conv_error}")
                        converted_audio = greeting_audio
                else:
                    converted_audio = greeting_audio

                # Step 2: Encode to μ-law for Twilio, keep PCM for FreJun
                if self.platform == "twilio":
                    try:
                        # Convert PCM to μ-law (G.711) for Twilio
                        converted_audio = audioop.lin2ulaw(converted_audio, 2)
                        logger.info(f"[CUSTOM] Encoded audio to μ-law for Twilio ({len(converted_audio)} bytes)")
                    except Exception as enc_error:
                        logger.error(f"[CUSTOM] μ-law encoding failed: {enc_error}")
                        # Fall back to PCM (won't work but at least won't crash)
                        pass

                # Send audio in platform-specific format
                if self.platform == "frejun":
                    # FreJun format
                    audio_b64 = base64.b64encode(converted_audio).decode('utf-8')
                    await self.websocket.send_json({
                        "type": "audio",
                        "audio_b64": audio_b64
                    })
                else:
                    # Twilio format with mark events (Bolna-style)
                    if not self.stream_sid:
                        logger.warning("[CUSTOM] Missing streamSid for Twilio audio, waiting for start event")
                    else:
                        await self.mark_handler.send_audio_with_marks(
                            converted_audio,
                            self.greeting,
                            is_final=True
                        )

                logger.info(f"[CUSTOM] Greeting sent to {self.platform} ({len(converted_audio)} bytes)")
            else:
                logger.error(f"[CUSTOM] ❌ TTS returned NO AUDIO for greeting! Provider: {self.tts_provider_name}")
                logger.error(f"[CUSTOM] ❌ Greeting text was: \"{self.greeting}\"")
                logger.error(f"[CUSTOM] ❌ This means the TTS provider failed silently!")

        except Exception as e:
            logger.error(f"[CUSTOM] Error sending greeting: {e}", exc_info=True)

    async def process_audio_chunk(self, audio_data: bytes):
        """
        Buffer audio and transcribe when we have enough data
        Uses simple VAD (Voice Activity Detection) based on buffer size
        Bolna-style: 100ms buffering for optimal latency
        """
        self.audio_buffer.extend(audio_data)
        logger.debug(f"[CUSTOM] 🎙️ Buffered audio: {len(self.audio_buffer)} bytes total")

        # Process when we have ~100ms of audio (8000 samples/sec * 0.1sec * 2 bytes = 1600 bytes)
        # Twilio sends 20ms chunks (320 bytes), so we buffer 5 chunks = 100ms
        # This matches Bolna's optimal buffering strategy
        if len(self.audio_buffer) >= 1600:
            logger.info(f"[CUSTOM] 🎯 Buffer threshold reached ({len(self.audio_buffer)} bytes), processing...")
            await self.transcribe_and_respond()

    async def transcribe_and_respond(self):
        """
        Transcribe buffered audio and generate response
        """
        if len(self.audio_buffer) == 0:
            logger.debug(f"[CUSTOM] ℹ️ Empty buffer, skipping transcription")
            return

        try:
            # Copy buffer and clear it
            audio_to_process = bytes(self.audio_buffer)
            self.audio_buffer.clear()

            logger.info(f"[CUSTOM] 🎤 === TRANSCRIPTION START === ({len(audio_to_process)} bytes)")

            # Transcribe using ASR provider
            logger.info(f"[CUSTOM] 🔄 Calling ASR provider: {self.asr_provider_name}")
            transcript = await self.asr_provider.transcribe(audio_to_process)

            if not transcript or len(transcript.strip()) == 0:
                logger.debug(f"[CUSTOM] ℹ️ Empty transcript from ASR, skipping")
                return

            logger.info(f"[CUSTOM] ✅ Transcribed ({len(transcript)} chars): \"{transcript}\"")

            # Add user message to history
            self.conversation_history.append({
                "role": "user",
                "content": transcript
            })
            logger.info(f"[CUSTOM] 💬 Added user message to conversation history (total: {len(self.conversation_history)} messages)")

            # Generate LLM response
            logger.info(f"[CUSTOM] 🤖 === LLM GENERATION START ===")
            logger.info(f"[CUSTOM] 🔄 Calling LLM provider: {self.llm_provider}/{self.llm_model}")
            response_text = await self.generate_llm_response()

            if not response_text:
                logger.warning(f"[CUSTOM] ⚠️ Empty LLM response, skipping")
                return

            logger.info(f"[CUSTOM] ✅ LLM response ({len(response_text)} chars): \"{response_text}\"")

            # Add assistant message to history
            self.conversation_history.append({
                "role": "assistant",
                "content": response_text
            })
            logger.info(f"[CUSTOM] 💬 Added assistant message to conversation history")

            # Convert response to speech
            logger.info(f"[CUSTOM] 🔊 === TTS SYNTHESIS START ===")
            logger.info(f"[CUSTOM] 🔄 Calling TTS provider: {self.tts_provider_name}")
            response_audio = await self.tts_provider.synthesize(response_text)

            if not response_audio:
                logger.error(f"[CUSTOM] ❌ TTS synthesis returned no audio!")
                return

            logger.info(f"[CUSTOM] ✅ TTS synthesized {len(response_audio)} bytes of audio")

            # Convert audio format if needed
            logger.info(f"[CUSTOM] 🔄 === AUDIO CONVERSION START ===")
            # Determine input sample rate based on TTS provider
            input_sample_rate = 8000  # Default for Cartesia
            is_wav_format = False  # Flag for WAV-encoded audio

            if self.tts_provider_name == 'elevenlabs':
                input_sample_rate = 16000
            elif self.tts_provider_name == 'openai':
                input_sample_rate = 24000  # OpenAI TTS outputs 24kHz
            elif self.tts_provider_name == 'sarvam':
                # Sarvam returns WAV format @ 8kHz
                input_sample_rate = 8000
                is_wav_format = True

            logger.info(f"[CUSTOM]   └─ Input sample rate: {input_sample_rate}Hz, Target: 8000Hz (Twilio requirement)")
            logger.info(f"[CUSTOM]   └─ Is WAV format: {is_wav_format}")

            # Step 0: Extract PCM from WAV if needed (for Sarvam)
            if is_wav_format:
                try:
                    from app.voice_pipeline.helpers.utils import wav_bytes_to_pcm
                    logger.info(f"[CUSTOM]   └─ Extracting PCM from WAV container...")
                    response_audio = wav_bytes_to_pcm(response_audio)
                    logger.info(f"[CUSTOM] ✅ Extracted PCM: {len(response_audio)} bytes")
                except Exception as wav_error:
                    logger.error(f"[CUSTOM] ❌ WAV extraction failed: {wav_error}")

            # Step 1: Resample to 8kHz if needed
            if input_sample_rate != 8000:
                try:
                    logger.info(f"[CUSTOM]   └─ Resampling from {input_sample_rate}Hz to 8000Hz...")
                    converted_audio, _ = audioop.ratecv(response_audio, 2, 1, input_sample_rate, 8000, None)
                    logger.info(f"[CUSTOM] ✅ Resampled audio: {len(converted_audio)} bytes")
                except Exception as conv_error:
                    logger.error(f"[CUSTOM] ❌ Audio resampling failed: {conv_error}")
                    converted_audio = response_audio
            else:
                logger.info(f"[CUSTOM]   └─ No resampling needed (already 8kHz)")
                converted_audio = response_audio

            # Step 2: Encode to μ-law for Twilio, keep PCM for FreJun
            if self.platform == "twilio":
                try:
                    logger.info(f"[CUSTOM]   └─ Converting PCM to μ-law for Twilio...")
                    # Convert PCM to μ-law (G.711) for Twilio
                    converted_audio = audioop.lin2ulaw(converted_audio, 2)
                    logger.info(f"[CUSTOM] ✅ Encoded to μ-law: {len(converted_audio)} bytes")
                except Exception as enc_error:
                    logger.error(f"[CUSTOM] ❌ μ-law encoding failed: {enc_error}")
                    # Fall back to PCM (won't work but at least won't crash)
                    pass

            # Send audio in platform-specific format
            logger.info(f"[CUSTOM] 📤 === SENDING AUDIO TO {self.platform.upper()} ===")
            if self.platform == "frejun":
                # FreJun format
                audio_b64 = base64.b64encode(converted_audio).decode('utf-8')
                logger.info(f"[CUSTOM]   └─ Sending FreJun format audio ({len(audio_b64)} chars base64)")
                await self.websocket.send_json({
                    "type": "audio",
                    "audio_b64": audio_b64
                })
                logger.info(f"[CUSTOM] ✅ Audio sent to FreJun successfully")
            else:
                # Twilio format with mark events (Bolna-style)
                if not self.stream_sid:
                    logger.error("[CUSTOM] ❌ Missing streamSid for Twilio audio! Cannot send.")
                    logger.error("[CUSTOM]   └─ This usually means 'start' event was not received properly")
                    return
                else:
                    logger.info(f"[CUSTOM]   └─ Sending Twilio format audio with mark events (streamSid: {self.stream_sid})")
                    logger.info(f"[CUSTOM]   └─ Audio size: {len(converted_audio)} bytes")
                    await self.mark_handler.send_audio_with_marks(
                        converted_audio,
                        response_text,
                        is_final=True
                    )
                    logger.info(f"[CUSTOM] ✅ Audio sent to Twilio with mark events")

            logger.info(f"[CUSTOM] 🎉 === RESPONSE PIPELINE COMPLETE === ({len(converted_audio)} bytes sent)")

            # Log to database
            await self.log_interaction(transcript, response_text)

        except Exception as e:
            logger.error(f"[CUSTOM] Error in transcribe_and_respond: {e}", exc_info=True)

    async def generate_llm_response(self) -> str:
        """Generate response using LLM (OpenAI GPT-4)"""
        try:
            # Keep last 10 messages to avoid token limits
            messages = self.conversation_history[-10:]

            # Determine model to use
            llm_model = self.llm_model
            if not llm_model:
                # Default models based on provider
                if self.llm_provider == "openai":
                    llm_model = "gpt-4o-mini"
                elif self.llm_provider == "anthropic":
                    llm_model = "claude-3-5-sonnet-20241022"
                elif self.llm_provider == "groq":
                    llm_model = "llama-3.3-70b-versatile"
                else:
                    llm_model = "gpt-4o-mini"

            response = await self.llm_client.chat.completions.create(
                model=llm_model,
                messages=messages,
                temperature=self.temperature,
                max_tokens=self.llm_max_tokens,  # Use configured max tokens
            )

            return response.choices[0].message.content

        except Exception as e:
            logger.error(f"[CUSTOM] Error generating LLM response: {e}", exc_info=True)
            return "I apologize, I'm having trouble processing that right now."

    async def log_interaction(self, user_text: str, assistant_text: str):
        """Log conversation to database"""
        try:
            db = Database.get_db()
            call_logs_collection = db['call_logs']

            # Update call log with transcript
            call_logs_collection.update_one(
                {"frejun_call_id": self.call_id},
                {
                    "$push": {
                        "transcript": {
                            "timestamp": datetime.utcnow().isoformat(),
                            "user": user_text,
                            "assistant": assistant_text
                        }
                    },
                    "$set": {
                        "updated_at": datetime.utcnow()
                    }
                }
            )

        except Exception as e:
            logger.error(f"[CUSTOM] Error logging interaction: {e}")

    async def handle_stream(self):
        """Main handler for WebSocket streaming - Bolna-style internal loop"""
        self.is_running = True
        logger.info(f"[CUSTOM] 🎬 Starting handle_stream() for platform: {self.platform}")

        try:
            # Initialize providers
            logger.info(f"[CUSTOM] 🔧 Initializing providers...")
            if not await self.initialize_providers():
                logger.error(f"[CUSTOM] ❌ Failed to initialize providers")
                await self.websocket.close(code=1011, reason="Provider initialization failed")
                return

            logger.info(f"[CUSTOM] ✅ Providers initialized successfully")

            # For Twilio, wait for start event before sending greeting
            # For FreJun, send greeting immediately
            greeting_sent = False
            if self.platform != "twilio":
                logger.info(f"[CUSTOM] 📢 Sending greeting immediately (platform: {self.platform})")
                await self.send_greeting()
                greeting_sent = True
            else:
                logger.info(f"[CUSTOM] ⏳ Waiting for Twilio 'start' event before sending greeting")

            # Main message loop (Bolna-style: internal WebSocket loop)
            logger.info(f"[CUSTOM] 🔄 Entering main WebSocket message loop...")
            message_count = 0
            while self.is_running:
                try:
                    # Receive message from platform (FreJun or Twilio)
                    message = await asyncio.wait_for(
                        self.websocket.receive_json(),
                        timeout=30.0
                    )
                    message_count += 1
                    logger.debug(f"[CUSTOM] 📨 Received message #{message_count}: {message.get('event', message.get('type', 'unknown'))}")

                    # Handle platform-specific message formats
                    if self.platform == "frejun":
                        # FreJun format: {"type": "audio", "data": {"audio_b64": "..."}}
                        msg_type = message.get("type")

                        if msg_type == "audio":
                            # Audio data from caller
                            data_obj = message.get("data", {})
                            audio_b64 = data_obj.get("audio_b64")

                            if audio_b64:
                                # Decode base64 audio
                                audio_data = base64.b64decode(audio_b64)
                                await self.process_audio_chunk(audio_data)

                        elif msg_type == "start":
                            logger.info(f"[CUSTOM] FreJun stream started: {message}")

                        elif msg_type == "stop":
                            logger.info(f"[CUSTOM] FreJun stream stopped")
                            self.is_running = False
                            break

                    else:
                        # Twilio format: {"event": "media", "media": {"payload": "..."}}
                        event = message.get("event")

                        if event == "media":
                            # Audio data from caller
                            media = message.get("media", {})
                            payload = media.get("payload")

                            if payload:
                                # Decode base64 audio (Twilio sends μ-law encoded)
                                audio_data = base64.b64decode(payload)
                                logger.debug(f"[CUSTOM] 🎤 Received audio chunk: {len(audio_data)} bytes (μ-law)")

                                # Convert μ-law to PCM for ASR processing
                                try:
                                    audio_data = audioop.ulaw2lin(audio_data, 2)
                                    logger.debug(f"[CUSTOM] ✅ Decoded μ-law to PCM ({len(audio_data)} bytes)")
                                except Exception as decode_error:
                                    logger.error(f"[CUSTOM] ❌ Failed to decode μ-law audio: {decode_error}")
                                    continue

                                await self.process_audio_chunk(audio_data)
                            else:
                                logger.warning(f"[CUSTOM] ⚠️ Received media event with no payload")

                        elif event == "start":
                            # Extract streamSid and callSid from start event
                            start_data = message.get("start", {})
                            self.stream_sid = start_data.get("streamSid")
                            self.call_sid = start_data.get("callSid")
                            media_format = start_data.get("mediaFormat", {})

                            logger.info(f"[CUSTOM] 📞 Twilio stream START event received")
                            logger.info(f"[CUSTOM]   └─ StreamSID: {self.stream_sid}")
                            logger.info(f"[CUSTOM]   └─ CallSID: {self.call_sid}")
                            logger.info(f"[CUSTOM]   └─ Media Format: {media_format}")

                            # Update mark handler with stream_sid
                            self.mark_handler.set_stream_sid(self.stream_sid)
                            logger.info(f"[CUSTOM] ✅ Mark handler configured with stream_sid")

                            # Send greeting now that we have streamSid
                            if not greeting_sent:
                                logger.info(f"[CUSTOM] 📢 Sending greeting to caller...")
                                await self.send_greeting()
                                greeting_sent = True
                                logger.info(f"[CUSTOM] ✅ Greeting sent successfully")
                            else:
                                logger.info(f"[CUSTOM] ℹ️ Greeting already sent, skipping")

                        elif event == "mark":
                            # Handle mark event confirmation from Twilio
                            mark_data = message.get("mark", {})
                            mark_id = mark_data.get("name")
                            if mark_id:
                                logger.debug(f"[CUSTOM] ✔️ Mark event received: {mark_id}")
                                self.mark_handler.process_mark_received(mark_id)
                            else:
                                logger.warning(f"[CUSTOM] ⚠️ Mark event with no name")

                        elif event == "stop":
                            logger.info(f"[CUSTOM] 🛑 Twilio stream STOP event received")
                            self.is_running = False
                            break

                        else:
                            logger.debug(f"[CUSTOM] ℹ️ Unhandled Twilio event: {event}")

                except asyncio.TimeoutError:
                    # No message received, continue
                    continue

                except WebSocketDisconnect:
                    logger.info(f"[CUSTOM] WebSocket disconnected")
                    self.is_running = False
                    break

        except Exception as e:
            logger.error(f"[CUSTOM] Error in stream handler: {e}", exc_info=True)

        finally:
            # Process any remaining audio
            if len(self.audio_buffer) > 0:
                await self.transcribe_and_respond()

            logger.info(f"[CUSTOM] Stream handler finished for call {self.call_id}")


async def handle_custom_provider_stream(
    websocket: WebSocket,
    assistant_id: str,
    call_id: str
):
    """
    WebSocket endpoint handler for custom provider streaming

    This is called when an AI assistant is configured with custom providers
    (not using OpenAI Realtime API)
    """
    await websocket.accept()
    logger.info(f"[CUSTOM] WebSocket connected for assistant {assistant_id}")

    try:
        # Get assistant configuration
        db = Database.get_db()
        assistants_collection = db['assistants']

        if not ObjectId.is_valid(assistant_id):
            logger.error(f"[CUSTOM] Invalid assistant ID: {assistant_id}")
            await websocket.close(code=1008, reason="Invalid assistant ID")
            return

        assistant = assistants_collection.find_one({"_id": ObjectId(assistant_id)})

        if not assistant:
            logger.error(f"[CUSTOM] Assistant {assistant_id} not found")
            await websocket.close(code=1008, reason="Assistant not found")
            return

        # Get user and OpenAI API key
        user_id = assistant.get("user_id")
        if not user_id or not ObjectId.is_valid(str(user_id)):
            logger.error(f"[CUSTOM] Invalid user ID for assistant {assistant_id}")
            await websocket.close(code=1008, reason="Invalid user configuration")
            return

        users_collection = db['users']
        user = users_collection.find_one({"_id": ObjectId(str(user_id))})

        if not user:
            logger.error(f"[CUSTOM] User not found for assistant {assistant_id}")
            await websocket.close(code=1008, reason="User not found")
            return

        user_obj_id = ObjectId(str(user_id))

        # Resolve provider keys (ASR/TTS/LLM)
        provider_keys = resolve_provider_keys(db, assistant, user_obj_id)

        # Ensure we have an OpenAI key available for fallbacks
        openai_api_key = provider_keys.get("openai")
        if not openai_api_key:
            try:
                openai_api_key, _ = resolve_assistant_api_key(db, assistant, required_provider="openai")
                provider_keys['openai'] = openai_api_key
            except HTTPException as key_error:
                env_openai_key = os.getenv("OPENAI_API_KEY")
                if env_openai_key:
                    provider_keys['openai'] = env_openai_key
                    openai_api_key = env_openai_key
                else:
                    logger.error(f"[CUSTOM] OpenAI API key not configured for assistant: {key_error.detail}")
                    await websocket.close(code=1008, reason="OpenAI API key not configured")
                    return

        # Build assistant config
        assistant_config = {
            "assistant_id": str(assistant["_id"]),
            "system_message": assistant.get("system_message", "You are a helpful AI assistant."),
            "voice": assistant.get("voice", "alloy"),
            "temperature": assistant.get("temperature", 0.8),
            # Use call_greeting if available, otherwise fallback to greeting field
            "greeting": assistant.get("call_greeting") or assistant.get("greeting", "Hello! Thanks for calling. How can I help you today?"),
            "asr_provider": assistant.get("asr_provider", "openai"),
            "tts_provider": assistant.get("tts_provider", "openai"),
            "asr_language": assistant.get("asr_language", "en"),
            "asr_model": assistant.get("asr_model"),
            "tts_model": assistant.get("tts_model"),
            "tts_voice": assistant.get("tts_voice") or assistant.get("voice", "alloy"),
            "tts_speed": assistant.get("tts_speed", 1.0),
            "enable_precise_transcript": assistant.get("enable_precise_transcript", False),
            "interruption_threshold": assistant.get("interruption_threshold", 2),
            "response_rate": assistant.get("response_rate", "balanced"),
            "check_user_online": assistant.get("check_user_online", True),
            "audio_buffer_size": assistant.get("audio_buffer_size", 200),
            "llm_provider": assistant.get("llm_provider", "openai"),
            "llm_model": assistant.get("llm_model"),
            "llm_max_tokens": assistant.get("llm_max_tokens", 150),
            "bot_language": assistant.get("bot_language", "en"),
            "provider_keys": provider_keys,
        }

        logger.info(f"[CUSTOM] Starting stream with providers: ASR={assistant_config['asr_provider']}, TTS={assistant_config['tts_provider']}")

        # Create and run stream handler (FreJun platform)
        handler = CustomProviderStreamHandler(
            websocket=websocket,
            assistant_config=assistant_config,
            openai_api_key=openai_api_key,
            call_id=call_id,
            platform="frejun",
            provider_keys=provider_keys
        )

        await handler.handle_stream()

    except Exception as e:
        logger.error(f"[CUSTOM] Error in custom provider stream: {e}", exc_info=True)
        try:
            await websocket.close(code=1011, reason="Internal error")
        except:
            pass

    logger.info(f"[CUSTOM] Custom provider stream ended for assistant {assistant_id}")
