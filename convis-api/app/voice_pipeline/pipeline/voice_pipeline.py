"""
Advanced Voice Pipeline for Convis
Real-time voice processing with WebSocket streaming for minimal latency
Orchestrates: Twilio Audio → Deepgram → OpenAI LLM → ElevenLabs/Cartesia → Twilio
"""
import asyncio
import base64
import json
import uuid
from typing import Dict, Any
from datetime import datetime
from app.voice_pipeline.helpers.logger_config import configure_logger
from app.voice_pipeline.helpers.utils import create_ws_data_packet, timestamp_ms
from app.voice_pipeline.helpers.mark_event_meta_data import MarkEventMetaData
from app.voice_pipeline.transcriber import DeepgramTranscriber, SarvamTranscriber, GoogleTranscriber, OpenAITranscriber
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

    def __init__(self, assistant_config: Dict[str, Any], api_keys: Dict[str, str], twilio_ws, call_sid=None, stream_sid=None, db=None, conversation_history=None):
        self.assistant_config = assistant_config
        self.api_keys = api_keys
        self.twilio_ws = twilio_ws
        self.call_sid = call_sid
        self.stream_sid = stream_sid
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

        # Mark event tracking for audio playback monitoring
        self.mark_event_meta_data = MarkEventMetaData()
        self.is_audio_being_played = False
        self.response_heard_by_user = ""

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
        elif transcriber_provider == 'openai':
            logger.info("[VOICE_PIPELINE] Creating OpenAI Whisper transcriber (buffered with VAD)")
            return OpenAITranscriber(
                telephony_provider='twilio',  # Twilio uses μ-law 8kHz
                input_queue=self.audio_input_queue,
                output_queue=self.transcriber_output_queue,
                model=self.assistant_config.get('transcriber', {}).get('model', 'whisper-1'),
                language=self.assistant_config.get('transcriber', {}).get('language', 'en'),
                endpointing='400',  # 400ms silence detection for VAD
                transcriber_key=self.api_keys.get('openai')
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
                voice=self.assistant_config.get('synthesizer', {}).get('voice', 'default'),
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

            # Send greeting message if configured
            greeting = self.assistant_config.get('greeting_message')
            if greeting:
                await self._send_greeting(greeting)

        except Exception as e:
            logger.error(f"[VOICE_PIPELINE] Failed to start pipeline: {e}", exc_info=True)
            await self.stop()
            raise

    async def _send_greeting(self, greeting_text: str):
        """
        Send greeting message through the pipeline
        Synthesizes greeting and sends to Twilio immediately after pipeline starts

        Args:
            greeting_text: The greeting message to synthesize and play
        """
        try:
            logger.info(f"[VOICE_PIPELINE] 👋 Sending greeting: '{greeting_text}'")

            # Add greeting to conversation history
            self.conversation_history.append({
                "role": "assistant",
                "text": greeting_text
            })

            # Create metadata for greeting
            meta_info = {
                'sequence_id': str(timestamp_ms()),
                'message_category': 'agent_welcome_message',
                'is_greeting': True
            }

            # Queue greeting text to LLM output (which goes to synthesizer)
            await self.llm_output_queue.put({
                'text': greeting_text,
                'meta_info': meta_info,
                'is_final': True
            })

            logger.info("[VOICE_PIPELINE] ✅ Greeting queued for synthesis")

        except Exception as e:
            logger.error(f"[VOICE_PIPELINE] Failed to send greeting: {e}", exc_info=True)

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
                    is_final = transcript_data.get('is_final', True)

                    if transcript:
                        logger.info(f"[VOICE_PIPELINE] 📝 Transcript ({'final' if is_final else 'interim'}): {transcript}")

                        # BARGE-IN DETECTION
                        # If audio is playing and user speaks, trigger interruption
                        if self.is_audio_being_played and is_final:
                            word_count = len(transcript.split())
                            # Simple threshold: 2+ words = real interruption
                            # (Avoid false positives from single-word ASR artifacts)
                            if word_count >= 2:
                                logger.warning(f"[VOICE_PIPELINE] 🛑 Interruption detected! User said: '{transcript}' while audio was playing")
                                await self.handle_interruption()
                            else:
                                logger.info(f"[VOICE_PIPELINE] Ignoring single-word potential false positive: '{transcript}'")
                                continue

                        # Only process final transcripts (ignore interim results)
                        if not is_final:
                            logger.debug(f"[VOICE_PIPELINE] Skipping interim transcript: {transcript}")
                            continue

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

            # Track current synthesis metadata
            current_meta_info = {}
            current_text_parts = []

            # Start receiver task to get audio from synthesizer and forward to Twilio
            async def synthesizer_receiver():
                try:
                    async for audio_chunk, text_spoken in self.synthesizer.receiver():
                        if audio_chunk and len(audio_chunk) > 0 and audio_chunk != b'\x00':
                            # Attach metadata to audio chunk
                            audio_message = {
                                'data': audio_chunk,
                                'meta_info': {
                                    'text_synthesized': text_spoken or '',
                                    'sequence_id': current_meta_info.get('sequence_id', ''),
                                    'is_final_chunk': False  # Will be updated on end_of_llm_stream
                                }
                            }
                            # Forward audio with metadata to Twilio output queue
                            await self.synthesizer_output_queue.put(audio_message)
                            logger.debug(f"[VOICE_PIPELINE] 🎵 Audio chunk received ({len(audio_chunk)} bytes, text: '{text_spoken or ''}')")
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

                # Update shared metadata for the receiver task
                current_meta_info.update(meta_info)
                if is_final:
                    current_meta_info['is_final_chunk'] = True

                if text and len(text.strip()) > 0:
                    logger.info(f"[VOICE_PIPELINE] 🔊 Synthesizing: {text[:50]}...")
                    current_text_parts.append(text)

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

                # Reset metadata after final chunk
                if is_final:
                    current_meta_info = {}
                    current_text_parts = []

            # Cleanup
            monitor_task.cancel()
            receiver_task.cancel()

        except Exception as e:
            logger.error(f"[VOICE_PIPELINE] Synthesizer error: {e}", exc_info=True)

    async def _send_mark_message(self, mark_id: str):
        """Send mark event to Twilio for audio playback tracking"""
        if not self.stream_sid:
            logger.warning("[VOICE_PIPELINE] Missing streamSid, cannot send mark event")
            return

        mark_message = {
            'event': 'mark',
            'streamSid': self.stream_sid,
            'mark': {
                'name': mark_id
            }
        }
        await self.twilio_ws.send_text(json.dumps(mark_message))
        logger.debug(f"[VOICE_PIPELINE] Sent mark event: {mark_id}")

    async def _send_audio_to_twilio(self):
        """
        Send synthesized audio back to Twilio WebSocket with mark events
        Pattern: Pre-Mark → Media → Post-Mark (like Bolna)
        """
        try:
            logger.info("[VOICE_PIPELINE] Twilio audio sender task started")
            chunk_counter = 0

            while self.running:
                # Get audio from synthesizer queue
                # Audio comes with metadata attached by synthesizer
                message = await self.synthesizer_output_queue.get()

                # Handle different message formats
                if isinstance(message, bytes):
                    # Simple byte format (backward compatibility)
                    audio_chunk = message
                    meta_info = {'sequence_id': str(timestamp_ms()), 'chunk_id': chunk_counter}
                    text_synthesized = ""
                    is_final_chunk = False
                elif isinstance(message, dict):
                    # Rich format with metadata
                    audio_chunk = message.get('data', message.get('audio', b''))
                    meta_info = message.get('meta_info', {})
                    text_synthesized = meta_info.get('text_synthesized', '')
                    is_final_chunk = meta_info.get('is_final_chunk', False)
                else:
                    logger.warning(f"[VOICE_PIPELINE] Unknown message format: {type(message)}")
                    continue

                if not self.stream_sid:
                    logger.warning("[VOICE_PIPELINE] Missing streamSid, cannot send audio to Twilio")
                    continue

                if not audio_chunk or len(audio_chunk) == 0:
                    logger.debug("[VOICE_PIPELINE] Skipping empty audio chunk")
                    continue

                # Calculate audio duration (mulaw @ 8kHz)
                duration = len(audio_chunk) / 8000.0

                # Send Pre-Mark
                pre_mark_id = str(uuid.uuid4())
                pre_mark_metadata = {
                    'type': 'pre_mark_message',
                    'counter': chunk_counter
                }
                self.mark_event_meta_data.update_data(pre_mark_id, pre_mark_metadata)
                await self._send_mark_message(pre_mark_id)

                # Send Media (audio payload)
                media_message = {
                    'event': 'media',
                    'streamSid': self.stream_sid,
                    'media': {
                        'payload': base64.b64encode(audio_chunk).decode('utf-8')
                    }
                }
                await self.twilio_ws.send_text(json.dumps(media_message))

                # Send Post-Mark with metadata
                post_mark_id = str(uuid.uuid4())
                post_mark_metadata = {
                    'type': 'agent_response',
                    'text_synthesized': text_synthesized,
                    'is_final_chunk': is_final_chunk,
                    'sequence_id': meta_info.get('sequence_id', ''),
                    'duration': duration,
                    'counter': chunk_counter
                }
                self.mark_event_meta_data.update_data(post_mark_id, post_mark_metadata)
                await self._send_mark_message(post_mark_id)

                logger.debug(f"[VOICE_PIPELINE] ✅ Sent audio chunk #{chunk_counter} ({len(audio_chunk)} bytes, {duration:.2f}s)")
                chunk_counter += 1

        except Exception as e:
            logger.error(f"[VOICE_PIPELINE] Twilio sender error: {e}", exc_info=True)

    async def handle_interruption(self):
        """
        Handle user interruption (barge-in)
        Sends clear event to Twilio to stop current audio playback
        """
        logger.info("[VOICE_PIPELINE] ⚠️ Handling interruption - user spoke while audio was playing")

        if not self.stream_sid:
            logger.warning("[VOICE_PIPELINE] Missing streamSid, cannot send clear event")
            return

        # Send clear event to Twilio
        clear_message = {
            'event': 'clear',
            'streamSid': self.stream_sid
        }
        await self.twilio_ws.send_text(json.dumps(clear_message))
        logger.info("[VOICE_PIPELINE] 🧹 Clear event sent to Twilio")

        # Clear mark event metadata
        self.mark_event_meta_data.clear_data()

        # Reset audio playback state
        self.is_audio_being_played = False

        # TODO: Implement full interruption handling:
        # - Cancel ongoing LLM generation
        # - Flush synthesizer stream
        # - Update conversation history with partial text heard
        # For now, this basic clear is sufficient to stop audio playback

    def process_mark_event(self, mark_id: str):
        """
        Process mark event received from Twilio
        Called when Twilio acknowledges audio playback

        Args:
            mark_id: UUID of the mark event
        """
        mark_data = self.mark_event_meta_data.fetch_data(mark_id)
        if not mark_data:
            logger.debug(f"[VOICE_PIPELINE] Mark {mark_id} not found (may have been cleared)")
            return

        mark_type = mark_data.get('type')

        if mark_type == 'pre_mark_message':
            # Audio chunk started playing
            self.is_audio_being_played = True
            logger.debug(f"[VOICE_PIPELINE] Audio playback started (chunk #{mark_data.get('counter')})")

        elif mark_type == 'agent_response':
            # Audio chunk finished playing
            text_synthesized = mark_data.get('text_synthesized', '')
            if text_synthesized:
                self.response_heard_by_user += text_synthesized

            if mark_data.get('is_final_chunk'):
                self.is_audio_being_played = False
                logger.info(f"[VOICE_PIPELINE] ✅ Final audio chunk played, user heard: '{self.response_heard_by_user}'")
                self.response_heard_by_user = ""  # Reset for next response

            logger.debug(f"[VOICE_PIPELINE] Audio chunk #{mark_data.get('counter')} played ({mark_data.get('duration', 0):.2f}s)")

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
