"""
Advanced Voice Pipeline for Convis
Real-time voice processing with WebSocket streaming for minimal latency
Orchestrates: Twilio Audio → Deepgram → OpenAI LLM → ElevenLabs/Cartesia → Twilio
"""
import asyncio
import base64
import json
from typing import Dict, Any
from datetime import datetime
from app.voice_pipeline.helpers.logger_config import configure_logger
from app.voice_pipeline.helpers.utils import create_ws_data_packet, timestamp_ms
from app.voice_pipeline.transcriber import DeepgramTranscriber, SarvamTranscriber, GoogleTranscriber
from app.voice_pipeline.llm import OpenAiLLM
from app.voice_pipeline.synthesizer import ElevenlabsSynthesizer, CartesiaSynthesizer, OpenAISynthesizer, SarvamSynthesizer

logger = configure_logger(__name__)


class SimpleTaskManager:
    """Simple task manager for voice pipeline - allows all sequence IDs"""
    def is_sequence_id_in_current_ids(self, sequence_id):
        # For simple pipeline, always allow synthesis
        return True


class VoicePipeline:
    """
    Simplified pipeline orchestrator based on Bolna architecture
    Manages async queues between: Transcriber → LLM → Synthesizer → Twilio
    """

    def __init__(self, assistant_config: Dict[str, Any], api_keys: Dict[str, str], twilio_ws, call_sid=None, db=None, conversation_history=None):
        self.assistant_config = assistant_config
        self.api_keys = api_keys
        self.twilio_ws = twilio_ws
        self.call_sid = call_sid
        self.db = db
        self.conversation_history = conversation_history if conversation_history is not None else []

        # Async queues for inter-component communication
        self.audio_input_queue = asyncio.Queue()  # Twilio → Transcriber
        self.transcriber_output_queue = asyncio.Queue()  # Transcriber → LLM
        self.llm_output_queue = asyncio.Queue()  # LLM → Synthesizer
        self.synthesizer_output_queue = asyncio.Queue()  # Synthesizer → Twilio

        # Component instances
        self.transcriber = None
        self.llm = None
        self.synthesizer = None

        # Pipeline control
        self.running = False
        self.tasks = []

        logger.info(f"[VOICE_PIPELINE] Initialized with assistant: {assistant_config.get('assistant_name', 'Unknown')}")

    def _create_transcriber(self):
        """Create transcriber with WebSocket/gRPC streaming"""
        transcriber_provider = self.assistant_config.get('transcriber', {}).get('provider', 'deepgram')

        if transcriber_provider == 'deepgram':
            logger.info("[VOICE_PIPELINE] Creating Deepgram transcriber (WebSocket streaming)")
            return DeepgramTranscriber(
                telephony_provider='twilio',  # Twilio uses μ-law 8kHz
                input_queue=self.audio_input_queue,
                output_queue=self.transcriber_output_queue,
                model=self.assistant_config.get('transcriber', {}).get('model', 'nova-2'),
                language=self.assistant_config.get('transcriber', {}).get('language', 'en'),
                endpointing='400',  # 400ms VAD endpointing
                transcriber_key=self.api_keys.get('deepgram')
            )
        elif transcriber_provider == 'sarvam':
            logger.info("[VOICE_PIPELINE] Creating Sarvam transcriber (WebSocket streaming)")
            return SarvamTranscriber(
                telephony_provider='twilio',  # Twilio uses μ-law 8kHz
                input_queue=self.audio_input_queue,
                output_queue=self.transcriber_output_queue,
                model=self.assistant_config.get('transcriber', {}).get('model', 'saarika:v2'),
                language=self.assistant_config.get('transcriber', {}).get('language', 'en-IN'),
                endpointing='400',  # 400ms VAD endpointing
                transcriber_key=self.api_keys.get('sarvam')
            )
        elif transcriber_provider == 'google':
            logger.info("[VOICE_PIPELINE] Creating Google transcriber (gRPC streaming)")
            return GoogleTranscriber(
                telephony_provider='twilio',  # Twilio uses μ-law 8kHz
                input_queue=self.audio_input_queue,
                output_queue=self.transcriber_output_queue,
                model=self.assistant_config.get('transcriber', {}).get('model', 'latest_long'),
                language=self.assistant_config.get('transcriber', {}).get('language', 'en-US'),
                endpointing='400',  # 400ms VAD endpointing
                transcriber_key=self.api_keys.get('google')
            )
        else:
            raise ValueError(f"Unsupported transcriber provider: {transcriber_provider}")

    def _create_llm(self):
        """Create OpenAI LLM with streaming support"""
        llm_provider = self.assistant_config.get('llm', {}).get('provider', 'openai')

        if llm_provider == 'openai':
            model = self.assistant_config.get('llm', {}).get('model', 'gpt-4o-mini')
            logger.info(f"[VOICE_PIPELINE] Creating OpenAI LLM with model: {model}")
            return OpenAiLLM(
                model=model,
                max_tokens=self.assistant_config.get('llm', {}).get('max_tokens', 100),
                temperature=self.assistant_config.get('llm', {}).get('temperature', 0.7),
                llm_key=self.api_keys.get('openai')
            )
        else:
            raise ValueError(f"Unsupported LLM provider: {llm_provider}")

    def _create_synthesizer(self):
        """Create TTS synthesizer with WebSocket/HTTP streaming"""
        synthesizer_provider = self.assistant_config.get('synthesizer', {}).get('provider', 'elevenlabs')

        # Create simple task manager for synthesis control
        task_manager = SimpleTaskManager()

        if synthesizer_provider == 'elevenlabs':
            logger.info("[VOICE_PIPELINE] Creating ElevenLabs synthesizer (WebSocket streaming)")
            return ElevenlabsSynthesizer(
                voice=self.assistant_config.get('synthesizer', {}).get('voice', 'default'),
                voice_id=self.assistant_config.get('synthesizer', {}).get('voice_id'),
                model=self.assistant_config.get('synthesizer', {}).get('model', 'eleven_turbo_v2_5'),
                synthesizer_key=self.api_keys.get('elevenlabs'),
                stream=True,
                use_mulaw=True,  # Twilio requires μ-law
                task_manager_instance=task_manager
            )
        elif synthesizer_provider == 'cartesia':
            logger.info("[VOICE_PIPELINE] Creating Cartesia synthesizer (WebSocket streaming)")
            return CartesiaSynthesizer(
                voice_id=self.assistant_config.get('synthesizer', {}).get('voice_id'),
                model=self.assistant_config.get('synthesizer', {}).get('model', 'sonic-english'),
                synthesizer_key=self.api_keys.get('cartesia'),
                stream=True,
                use_mulaw=True,
                task_manager_instance=task_manager
            )
        elif synthesizer_provider == 'openai':
            logger.info("[VOICE_PIPELINE] Creating OpenAI TTS synthesizer (HTTP streaming)")
            return OpenAISynthesizer(
                voice=self.assistant_config.get('synthesizer', {}).get('voice', 'alloy'),
                model=self.assistant_config.get('synthesizer', {}).get('model', 'tts-1'),
                synthesizer_key=self.api_keys.get('openai'),
                stream=True,
                sampling_rate=8000,
                use_mulaw=True,  # Twilio requires μ-law
                task_manager_instance=task_manager
            )
        elif synthesizer_provider == 'sarvam':
            logger.info("[VOICE_PIPELINE] Creating Sarvam TTS synthesizer (WebSocket streaming)")
            return SarvamSynthesizer(
                voice_id=self.assistant_config.get('synthesizer', {}).get('voice', 'Manisha'),
                model=self.assistant_config.get('synthesizer', {}).get('model', 'bulbul:v1'),
                language=self.assistant_config.get('synthesizer', {}).get('language', 'hi-IN'),
                synthesizer_key=self.api_keys.get('sarvam'),
                stream=True,
                sampling_rate=8000,
                use_mulaw=True,  # Twilio requires μ-law
                task_manager_instance=task_manager
            )
        else:
            raise ValueError(f"Unsupported synthesizer provider: {synthesizer_provider}")

    async def start(self):
        """Initialize and start all pipeline components"""
        if self.running:
            logger.warning("[VOICE_PIPELINE] Pipeline already running")
            return

        try:
            logger.info("[VOICE_PIPELINE] Starting pipeline...")

            # Create components
            self.transcriber = self._create_transcriber()
            self.llm = self._create_llm()
            self.synthesizer = self._create_synthesizer()

            self.running = True

            # Start all components in parallel
            self.tasks = [
                asyncio.create_task(self._run_transcriber()),
                asyncio.create_task(self._run_llm()),
                asyncio.create_task(self._run_synthesizer()),
                asyncio.create_task(self._send_audio_to_twilio())
            ]

            logger.info("[VOICE_PIPELINE] ✅ Pipeline started successfully")
            logger.info(f"[VOICE_PIPELINE] Components: Deepgram → OpenAI → {self.assistant_config.get('synthesizer', {}).get('provider', 'ElevenLabs').title()} → Twilio")

        except Exception as e:
            logger.error(f"[VOICE_PIPELINE] Failed to start pipeline: {e}", exc_info=True)
            await self.stop()
            raise

    async def _run_transcriber(self):
        """Run transcriber and forward output to LLM"""
        try:
            logger.info("[VOICE_PIPELINE] Transcriber task started")
            await self.transcriber.run()
        except Exception as e:
            logger.error(f"[VOICE_PIPELINE] Transcriber error: {e}", exc_info=True)

    async def _save_transcript(self):
        """Save conversation transcript to database in real-time"""
        if not self.db or not self.call_sid:
            return

        try:
            # Build full transcript from conversation history
            full_transcript = "\n\n".join([
                f"{'User' if msg['role'] == 'user' else 'Assistant'}: {msg['text']}"
                for msg in self.conversation_history
            ])

            # Update call log with transcript
            self.db["call_logs"].update_one(
                {"call_sid": self.call_sid},
                {"$set": {
                    "transcript": full_transcript,
                    "transcript_updated_at": datetime.utcnow()
                }}
            )
            logger.debug(f"[VOICE_PIPELINE] 💾 Transcript saved to database (length: {len(full_transcript)} chars)")
        except Exception as e:
            logger.error(f"[VOICE_PIPELINE] Error saving transcript: {e}", exc_info=True)

    async def _run_llm(self):
        """Process transcripts through LLM and forward to synthesizer"""
        try:
            logger.info("[VOICE_PIPELINE] LLM task started")
            while self.running:
                # Get transcript from transcriber
                data_packet = await self.transcriber_output_queue.get()

                if data_packet.get('data') == 'transcriber_connection_closed':
                    logger.info("[VOICE_PIPELINE] Transcriber closed, stopping LLM")
                    break

                transcript_data = data_packet.get('data', {})
                if isinstance(transcript_data, dict) and transcript_data.get('type') == 'transcript':
                    transcript = transcript_data.get('content', '').strip()
                    if transcript:
                        logger.info(f"[VOICE_PIPELINE] 📝 Transcript: {transcript}")

                        # Add user message to conversation history
                        self.conversation_history.append({
                            "role": "user",
                            "text": transcript
                        })

                        # Build conversation messages for LLM
                        system_message = self.assistant_config.get('system_message', 'You are a helpful AI assistant.')
                        messages = [{"role": "system", "content": system_message}]

                        # Add conversation history
                        for msg in self.conversation_history:
                            messages.append({
                                "role": msg["role"],
                                "content": msg["text"]
                            })

                        # Generate LLM response using streaming
                        llm_response = ""
                        meta_info = data_packet.get('meta_info', {})
                        meta_info['sequence_id'] = meta_info.get('sequence_id', str(timestamp_ms()))
                        meta_info['turn_id'] = meta_info.get('turn_id', '1')

                        try:
                            async for chunk, is_final, latency, is_function_call, func_name, pre_call_msg in self.llm.generate_stream(
                                messages=messages,
                                synthesize=True,
                                request_json=False,
                                meta_info=meta_info
                            ):
                                if isinstance(chunk, dict):  # Function call
                                    continue

                                if chunk and len(chunk.strip()) > 0:
                                    llm_response += chunk
                                    # Forward chunk to synthesizer for streaming TTS
                                    await self.llm_output_queue.put({
                                        'text': chunk,
                                        'meta_info': meta_info,
                                        'is_final': is_final
                                    })
                                    logger.debug(f"[VOICE_PIPELINE] 🤖 LLM chunk: {chunk[:50]}...")
                        except Exception as e:
                            logger.error(f"[VOICE_PIPELINE] LLM generation error: {e}", exc_info=True)
                            llm_response = "I apologize, I'm having trouble processing that right now."
                            await self.llm_output_queue.put({
                                'text': llm_response,
                                'meta_info': meta_info,
                                'is_final': True
                            })

                        logger.info(f"[VOICE_PIPELINE] 🤖 Complete LLM response: {llm_response}")

                        # Add assistant response to conversation history
                        self.conversation_history.append({
                            "role": "assistant",
                            "text": llm_response
                        })

                        # Save transcript to database in real-time
                        await self._save_transcript()

        except Exception as e:
            logger.error(f"[VOICE_PIPELINE] LLM error: {e}", exc_info=True)

    async def _run_synthesizer(self):
        """Synthesize LLM responses to audio"""
        try:
            logger.info("[VOICE_PIPELINE] Synthesizer task started")

            # Establish WebSocket connection to synthesizer (ElevenLabs/Cartesia)
            self.synthesizer.websocket_holder["websocket"] = await self.synthesizer.establish_connection()

            # Start monitoring task to maintain connection
            monitor_task = asyncio.create_task(self.synthesizer.monitor_connection())

            # Start receiver task to get audio from synthesizer and forward to Twilio
            async def synthesizer_receiver():
                try:
                    async for audio_chunk, text_spoken in self.synthesizer.receiver():
                        if audio_chunk and len(audio_chunk) > 0 and audio_chunk != b'\x00':
                            # Forward audio to Twilio output queue
                            await self.synthesizer_output_queue.put(audio_chunk)
                            logger.debug(f"[VOICE_PIPELINE] 🎵 Audio chunk received ({len(audio_chunk)} bytes)")
                except Exception as e:
                    logger.error(f"[VOICE_PIPELINE] Synthesizer receiver error: {e}", exc_info=True)

            receiver_task = asyncio.create_task(synthesizer_receiver())

            # Process LLM text chunks
            while self.running:
                # Get text from LLM
                llm_output = await self.llm_output_queue.get()
                text = llm_output.get('text', '')
                meta_info = llm_output.get('meta_info', {})
                is_final = llm_output.get('is_final', False)

                if text and len(text.strip()) > 0:
                    logger.info(f"[VOICE_PIPELINE] 🔊 Synthesizing: {text[:50]}...")

                    try:
                        # Send text to synthesizer with sequence_id
                        sequence_id = meta_info.get('sequence_id', str(timestamp_ms()))
                        await self.synthesizer.sender(
                            text=text,
                            sequence_id=sequence_id,
                            end_of_llm_stream=is_final
                        )
                        logger.debug(f"[VOICE_PIPELINE] ✅ Audio synthesis queued for: {text[:30]}...")
                    except Exception as e:
                        logger.error(f"[VOICE_PIPELINE] Synthesizer sender error: {e}", exc_info=True)

            # Cleanup
            monitor_task.cancel()
            receiver_task.cancel()

        except Exception as e:
            logger.error(f"[VOICE_PIPELINE] Synthesizer error: {e}", exc_info=True)

    async def _send_audio_to_twilio(self):
        """Send synthesized audio back to Twilio WebSocket"""
        try:
            logger.info("[VOICE_PIPELINE] Twilio audio sender task started")
            while self.running:
                # Get audio from synthesizer
                audio_chunk = await self.synthesizer_output_queue.get()

                # Send to Twilio as media message
                media_message = {
                    'event': 'media',
                    'media': {
                        'payload': base64.b64encode(audio_chunk).decode('utf-8')
                    }
                }
                await self.twilio_ws.send_text(json.dumps(media_message))

        except Exception as e:
            logger.error(f"[VOICE_PIPELINE] Twilio sender error: {e}", exc_info=True)

    async def feed_audio(self, audio_chunk: bytes):
        """
        Feed audio from Twilio into the pipeline
        Called from WebSocket handler when receiving 'media' events
        """
        if not self.running:
            logger.warning("[VOICE_PIPELINE] Pipeline not running, ignoring audio")
            return

        # Create data packet with metadata
        data_packet = create_ws_data_packet(audio_chunk, meta_info={
            'timestamp': timestamp_ms(),
            'source': 'twilio'
        })

        # Feed to transcriber
        await self.audio_input_queue.put(data_packet)

    async def stop(self):
        """Stop all pipeline components gracefully"""
        if not self.running:
            return

        logger.info("[VOICE_PIPELINE] Stopping pipeline...")
        self.running = False

        # Cancel all tasks
        for task in self.tasks:
            if not task.done():
                task.cancel()

        # Wait for tasks to finish
        if self.tasks:
            await asyncio.gather(*self.tasks, return_exceptions=True)

        # Stop components
        if self.transcriber:
            await self.transcriber.toggle_connection()

        logger.info("[VOICE_PIPELINE] ❌ Pipeline stopped")
