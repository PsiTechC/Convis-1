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
from fastapi import WebSocket, WebSocketDisconnect
from bson import ObjectId

from app.config.database import Database
from app.providers.factory import ProviderFactory

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
        openai_api_key: str,
        call_id: str
    ):
        self.websocket = websocket
        self.assistant_config = assistant_config
        self.openai_api_key = openai_api_key
        self.call_id = call_id

        # Provider instances
        self.asr_provider = None
        self.tts_provider = None
        self.llm_client = None

        # Conversation state
        self.conversation_history = []
        self.is_running = False
        self.audio_buffer = bytearray()

        # Configuration
        self.asr_provider_name = assistant_config.get('asr_provider', 'openai')
        self.tts_provider_name = assistant_config.get('tts_provider', 'openai')
        self.voice = assistant_config.get('voice', 'alloy')
        self.tts_voice = assistant_config.get('tts_voice', self.voice)
        self.temperature = assistant_config.get('temperature', 0.8)
        self.system_message = assistant_config.get('system_message', 'You are a helpful AI assistant.')
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
            # Initialize ASR provider
            logger.info(f"[CUSTOM] Initializing ASR provider: {self.asr_provider_name}")
            # Determine ASR model based on provider and config
            asr_model = self.asr_model
            if not asr_model:
                asr_model = 'nova-2' if self.asr_provider_name == 'deepgram' else 'whisper-1'

            if self.asr_provider_name == 'deepgram' and not os.getenv("DEEPGRAM_API_KEY"):
                logger.warning("[CUSTOM] DEEPGRAM_API_KEY not configured. Falling back to OpenAI Whisper for ASR.")
                self.asr_provider_name = 'openai'
                asr_model = 'whisper-1'

            try:
                self.asr_provider = ProviderFactory.create_asr_provider(
                    provider_name=self.asr_provider_name,
                    api_key=self.openai_api_key if self.asr_provider_name == 'openai' else None,
                    model=asr_model,
                    language=self.asr_language
                )
            except Exception as asr_error:
                logger.error(f"[CUSTOM] Failed to initialize ASR provider '{self.asr_provider_name}': {asr_error}", exc_info=True)
                if self.asr_provider_name != 'openai':
                    logger.warning("[CUSTOM] Falling back to OpenAI Whisper for ASR")
                    self.asr_provider_name = 'openai'
                    self.asr_model = 'whisper-1'
                    self.asr_provider = ProviderFactory.create_asr_provider(
                        provider_name='openai',
                        api_key=self.openai_api_key,
                        model='whisper-1',
                        language=self.asr_language
                    )
                else:
                    raise

            # Initialize TTS provider
            logger.info(f"[CUSTOM] Initializing TTS provider: {self.tts_provider_name}")
            # Determine TTS model based on provider and config
            tts_model = self.tts_model
            if not tts_model:
                tts_model = 'tts-1' if self.tts_provider_name == 'openai' else None

            if self.tts_provider_name == 'cartesia' and not os.getenv("CARTESIA_API_KEY"):
                logger.warning("[CUSTOM] CARTESIA_API_KEY not configured. Falling back to OpenAI TTS.")
                self.tts_provider_name = 'openai'
                tts_model = 'tts-1'
            elif self.tts_provider_name == 'elevenlabs' and not os.getenv("ELEVENLABS_API_KEY"):
                logger.warning("[CUSTOM] ELEVENLABS_API_KEY not configured. Falling back to OpenAI TTS.")
                self.tts_provider_name = 'openai'
                tts_model = 'tts-1'

            try:
                self.tts_provider = ProviderFactory.create_tts_provider(
                    provider_name=self.tts_provider_name,
                    api_key=self.openai_api_key if self.tts_provider_name == 'openai' else None,
                    voice=self.tts_voice or self.voice
                )
            except Exception as tts_error:
                logger.error(f"[CUSTOM] Failed to initialize TTS provider '{self.tts_provider_name}': {tts_error}", exc_info=True)
                if self.tts_provider_name != 'openai':
                    logger.warning("[CUSTOM] Falling back to OpenAI TTS")
                    self.tts_provider_name = 'openai'
                    self.tts_model = 'tts-1'
                    self.tts_provider = ProviderFactory.create_tts_provider(
                        provider_name='openai',
                        api_key=self.openai_api_key,
                        voice=self.voice
                    )
                else:
                    raise

            # Initialize LLM client based on provider
            logger.info(f"[CUSTOM] Initializing LLM provider: {self.llm_provider}")
            llm_initialized = False
            if self.llm_provider == "openai":
                try:
                    import openai
                    self.llm_client = openai.AsyncOpenAI(api_key=self.openai_api_key)
                    llm_initialized = True
                except Exception as openai_error:
                    logger.error(f"[CUSTOM] Failed to initialize OpenAI LLM client: {openai_error}", exc_info=True)
            elif self.llm_provider == "anthropic":
                try:
                    import anthropic
                    api_key = os.getenv("ANTHROPIC_API_KEY")
                    if not api_key:
                        raise RuntimeError("ANTHROPIC_API_KEY is not configured")
                    self.llm_client = anthropic.AsyncAnthropic(api_key=api_key)
                    logger.warning("[CUSTOM] Anthropic client initialized but API responses are not yet supported. Falling back to OpenAI.")
                except Exception as anthropic_error:
                    logger.error(f"[CUSTOM] Failed to initialize Anthropic client: {anthropic_error}", exc_info=True)
            elif self.llm_provider == "groq":
                try:
                    from groq import AsyncGroq
                    api_key = os.getenv("GROQ_API_KEY")
                    if not api_key:
                        raise RuntimeError("GROQ_API_KEY is not configured")
                    self.llm_client = AsyncGroq(api_key=api_key)
                    logger.warning("[CUSTOM] Groq client initialized but API responses are not yet supported. Falling back to OpenAI.")
                except Exception as groq_error:
                    logger.error(f"[CUSTOM] Failed to initialize Groq client: {groq_error}", exc_info=True)

            if not llm_initialized:
                import openai
                self.llm_provider = "openai"
                self.llm_client = openai.AsyncOpenAI(api_key=self.openai_api_key)
                if not self.llm_model:
                    self.llm_model = "gpt-4o-mini"
                llm_initialized = True

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
            greeting_audio = await self.tts_provider.synthesize(self.greeting)

            # Convert audio if needed (FreJun expects 8kHz PCM)
            # Most TTS providers output at higher sample rates
            if len(greeting_audio) > 0:
                # Downsample to 8kHz if needed
                # audioop.ratecv parameters: (fragment, width, nchannels, inrate, outrate, state)
                # Assuming TTS output is 16kHz or 24kHz, downsample to 8kHz
                try:
                    # This is a simple approach - assume input is 16kHz
                    converted_audio, _ = audioop.ratecv(greeting_audio, 2, 1, 16000, 8000, None)
                except Exception as conv_error:
                    logger.warning(f"[CUSTOM] Audio conversion failed, using original: {conv_error}")
                    converted_audio = greeting_audio

                # Send to FreJun as base64
                audio_b64 = base64.b64encode(converted_audio).decode('utf-8')
                await self.websocket.send_json({
                    "event": "media",
                    "media": {
                        "payload": audio_b64
                    }
                })
                logger.info(f"[CUSTOM] Greeting sent ({len(converted_audio)} bytes)")

        except Exception as e:
            logger.error(f"[CUSTOM] Error sending greeting: {e}", exc_info=True)

    async def process_audio_chunk(self, audio_data: bytes):
        """
        Buffer audio and transcribe when we have enough data
        Uses simple VAD (Voice Activity Detection) based on buffer size
        """
        self.audio_buffer.extend(audio_data)

        # Process when we have ~1 second of audio (8000 samples * 2 bytes = 16000 bytes)
        if len(self.audio_buffer) >= 16000:
            await self.transcribe_and_respond()

    async def transcribe_and_respond(self):
        """
        Transcribe buffered audio and generate response
        """
        if len(self.audio_buffer) == 0:
            return

        try:
            # Copy buffer and clear it
            audio_to_process = bytes(self.audio_buffer)
            self.audio_buffer.clear()

            logger.info(f"[CUSTOM] Transcribing {len(audio_to_process)} bytes of audio")

            # Transcribe using ASR provider
            transcript = await self.asr_provider.transcribe(audio_to_process)

            if not transcript or len(transcript.strip()) == 0:
                logger.debug(f"[CUSTOM] Empty transcript, skipping")
                return

            logger.info(f"[CUSTOM] Transcribed: {transcript}")

            # Add user message to history
            self.conversation_history.append({
                "role": "user",
                "content": transcript
            })

            # Generate LLM response
            logger.info(f"[CUSTOM] Generating LLM response...")
            response_text = await self.generate_llm_response()

            if not response_text:
                logger.warning(f"[CUSTOM] Empty LLM response")
                return

            logger.info(f"[CUSTOM] LLM response: {response_text}")

            # Add assistant message to history
            self.conversation_history.append({
                "role": "assistant",
                "content": response_text
            })

            # Convert response to speech
            logger.info(f"[CUSTOM] Synthesizing speech...")
            response_audio = await self.tts_provider.synthesize(response_text)

            # Convert audio format if needed
            try:
                # Downsample to 8kHz for FreJun
                converted_audio, _ = audioop.ratecv(response_audio, 2, 1, 16000, 8000, None)
            except Exception as conv_error:
                logger.warning(f"[CUSTOM] Audio conversion failed: {conv_error}")
                converted_audio = response_audio

            # Send audio to FreJun
            audio_b64 = base64.b64encode(converted_audio).decode('utf-8')
            await self.websocket.send_json({
                "event": "media",
                "media": {
                    "payload": audio_b64
                }
            })

            logger.info(f"[CUSTOM] Response audio sent ({len(converted_audio)} bytes)")

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
        """Main handler for WebSocket streaming"""
        self.is_running = True

        try:
            # Initialize providers
            if not await self.initialize_providers():
                logger.error(f"[CUSTOM] Failed to initialize providers")
                await self.websocket.close(code=1011, reason="Provider initialization failed")
                return

            # Send greeting
            await self.send_greeting()

            # Main message loop
            while self.is_running:
                try:
                    # Receive message from FreJun
                    message = await asyncio.wait_for(
                        self.websocket.receive_json(),
                        timeout=30.0
                    )

                    event = message.get("event")

                    if event == "media":
                        # Audio data from caller
                        media = message.get("media", {})
                        payload = media.get("payload")

                        if payload:
                            # Decode base64 audio
                            audio_data = base64.b64decode(payload)
                            await self.process_audio_chunk(audio_data)

                    elif event == "start":
                        logger.info(f"[CUSTOM] Stream started: {message}")

                    elif event == "stop":
                        logger.info(f"[CUSTOM] Stream stopped")
                        self.is_running = False
                        break

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

        openai_api_key = user.get("openai_key")
        if not openai_api_key:
            logger.error(f"[CUSTOM] OpenAI API key not configured for user")
            await websocket.close(code=1008, reason="API key not configured")
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
        }

        logger.info(f"[CUSTOM] Starting stream with providers: ASR={assistant_config['asr_provider']}, TTS={assistant_config['tts_provider']}")

        # Create and run stream handler
        handler = CustomProviderStreamHandler(
            websocket=websocket,
            assistant_config=assistant_config,
            openai_api_key=openai_api_key,
            call_id=call_id
        )

        await handler.handle_stream()

    except Exception as e:
        logger.error(f"[CUSTOM] Error in custom provider stream: {e}", exc_info=True)
        try:
            await websocket.close(code=1011, reason="Internal error")
        except:
            pass

    logger.info(f"[CUSTOM] Custom provider stream ended for assistant {assistant_id}")
