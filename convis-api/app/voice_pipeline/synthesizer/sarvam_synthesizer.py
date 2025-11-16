"""
Sarvam AI TTS Synthesizer for Convis
Adapted from Bolna architecture
Uses Sarvam's text-to-speech WebSocket API for Indian voices
"""
import aiohttp
import asyncio
import os
import websockets
from websockets.exceptions import InvalidHandshake
import copy
import time
import uuid
import traceback
import json
import base64
from collections import deque

from .base_synthesizer import BaseSynthesizer
from app.voice_pipeline.helpers.logger_config import configure_logger
from app.voice_pipeline.helpers.utils import (
    create_ws_data_packet,
    resample,
    wav_bytes_to_pcm,
    pcm16_to_mulaw,
)

logger = configure_logger(__name__)


class SarvamSynthesizer(BaseSynthesizer):
    """
    Sarvam AI TTS synthesizer using WebSocket streaming
    Supports: Hindi and other Indian languages
    Models: bulbul:v2, bulbul:v3-beta (default: bulbul:v2)
    Valid Speakers: anushka, abhilash, manisha, vidya, arya, karun, hitesh, aditya,
                   isha, ritu, chirag, harsh, sakshi, priya, neha, rahul, pooja,
                   rohan, simran, kavya, anjali, sneha, kiran, vikram, rajesh,
                   sunita, tara, anirudh, kriti, ishaan
    """

    def __init__(
        self,
        voice_id,
        model,
        language,
        sampling_rate="8000",
        stream=False,
        buffer_size=400,
        speed=1.0,
        synthesizer_key=None,
        use_mulaw=False,
        **kwargs
    ):
        super().__init__(kwargs.get("task_manager_instance", None), stream)

        self.api_key = (synthesizer_key or os.environ.get("SARVAM_API_KEY", "")).strip()
        if not self.api_key:
            raise ValueError("SARVAM_API_KEY not found in environment or parameters")

        self.voice_id = voice_id
        self.model = model
        self.stream = stream
        self.use_mulaw = use_mulaw
        self.buffer_size = buffer_size
        if self.buffer_size < 30 or self.buffer_size > 200:
            self.buffer_size = 200

        self.sampling_rate = int(sampling_rate)
        self.api_url = "https://api.sarvam.ai/text-to-speech"
        self.ws_url = f"wss://api.sarvam.ai/text-to-speech/ws?model={model}"

        # Sarvam-specific parameters
        self.language = language
        self.loudness = 1.0
        self.pitch = 0.0
        self.pace = speed
        self.enable_preprocessing = True

        # Streaming state
        self.first_chunk_generated = False
        self.last_text_sent = False
        self.meta_info = None
        self.synthesized_characters = 0
        self.previous_request_ids = []
        self.websocket_holder = {"websocket": None}
        self.sender_task = None
        self.conversation_ended = False

        # Turn latency tracking
        self.current_turn_start_time = None
        self.current_turn_id = None
        self.text_queue = deque()
        self.current_text = ""

        logger.info(f"[SARVAM_TTS] Initialized with voice={voice_id}, model={model}, language={language}")

    def get_engine(self):
        return self.model

    def supports_websocket(self):
        return True

    async def __send_payload(self, payload):
        """
        Send HTTP request to Sarvam TTS API
        """
        headers = self._build_auth_headers()
        headers['Content-Type'] = 'application/json'

        async with aiohttp.ClientSession() as session:
            if payload is not None:
                try:
                    async with session.post(self.api_url, headers=headers, json=payload) as response:
                        if response.status == 200:
                            data = await response.json()
                            if data and data.get('audios', []) and isinstance(data.get('audios', []), list):
                                return data.get('audios')[0]
                        else:
                            logger.error(f"[SARVAM_TTS] Error: {response.status} - {await response.text()}")
                except Exception as e:
                    logger.error(f"[SARVAM_TTS] HTTP request error: {e}")
            else:
                logger.info("[SARVAM_TTS] Payload was null")

    async def synthesize(self, text):
        """
        One-off synthesis for non-streaming use cases
        """
        audio = await self.__generate_http(text)
        return audio

    async def __generate_http(self, text):
        """
        Generate audio using HTTP API (non-streaming)
        """
        payload = {
            "target_language_code": self.language,
            "text": text,
            "speaker": self.voice_id,
            "pitch": self.pitch,
            "loudness": self.loudness,
            "speech_sample_rate": self.sampling_rate,
            "enable_preprocessing": self.enable_preprocessing,
            "model": self.model
        }
        response = await self.__send_payload(payload)
        return response

    async def sender(self, text, sequence_id, end_of_llm_stream=False):
        """
        Send text chunks to Sarvam WebSocket
        """
        try:
            if self.conversation_ended:
                return

            if not self.should_synthesize_response(sequence_id):
                logger.info(
                    f"[SARVAM_TTS] Not synthesizing - sequence_id {sequence_id} not in current_ids"
                )
                return

            # Ensure the WebSocket connection is established
            while (self.websocket_holder["websocket"] is None or
                   self.websocket_holder["websocket"].state is websockets.protocol.State.CLOSED):
                logger.info("[SARVAM_TTS] Waiting for WebSocket connection...")
                await asyncio.sleep(1)

            if text and text.strip():
                try:
                    await self.websocket_holder["websocket"].send(
                        json.dumps({"type": "text", "data": {"text": text}})
                    )
                    logger.info(f"[SARVAM_TTS] Sent text chunk: {text[:50]}...")
                except Exception as e:
                    logger.error(f"[SARVAM_TTS] Error sending chunk: {e}")
                    return

            # Send flush signal at end of LLM stream
            if end_of_llm_stream:
                self.last_text_sent = True

            try:
                await self.websocket_holder["websocket"].send(json.dumps({"type": "flush"}))
                logger.info("[SARVAM_TTS] Sent flush signal")
            except Exception as e:
                logger.info(f"[SARVAM_TTS] Error sending flush signal: {e}")

        except asyncio.CancelledError:
            logger.info("[SARVAM_TTS] Sender task was cancelled")
        except Exception as e:
            logger.error(f"[SARVAM_TTS] Unexpected error in sender: {e}", exc_info=True)

    def form_payload(self, text):
        """
        Form payload for WebSocket config or HTTP request
        """
        payload = {
            "target_language_code": self.language,
            "text": text,
            "speaker": self.voice_id,
            "pitch": self.pitch,
            "loudness": self.loudness,
            "speech_sample_rate": self.sampling_rate,
            "enable_preprocessing": self.enable_preprocessing,
            "model": self.model
        }
        return payload

    async def receiver(self):
        """
        Receive audio chunks from Sarvam WebSocket
        """
        while True:
            try:
                if self.conversation_ended:
                    return

                if (self.websocket_holder["websocket"] is None or
                        self.websocket_holder["websocket"].state is websockets.protocol.State.CLOSED):
                    logger.info("[SARVAM_TTS] WebSocket is not connected, skipping receive")
                    await asyncio.sleep(5)
                    continue

                response = await self.websocket_holder["websocket"].recv()
                data = json.loads(response)

                if "type" in data and data["type"] == 'audio':
                    chunk = base64.b64decode(data["data"]["audio"])
                    logger.debug(f"[SARVAM_TTS] Received audio chunk ({len(chunk)} bytes)")
                    yield chunk, None

                if self.last_text_sent:
                    yield b'\x00', None

            except websockets.exceptions.ConnectionClosed:
                logger.info("[SARVAM_TTS] WebSocket connection closed")
                break
            except Exception as e:
                logger.error(f"[SARVAM_TTS] Error in receiver: {e}")

    async def establish_connection(self):
        """
        Establish WebSocket connection to Sarvam TTS
        """
        try:
            start_time = time.perf_counter()
            additional_headers = self._build_auth_headers()

            websocket = await asyncio.wait_for(
                websockets.connect(self.ws_url, additional_headers=additional_headers),
                timeout=10.0
            )

            # Send initial config message
            config_message = {
                "type": "config",
                "data": {
                    "target_language_code": self.language,
                    "speaker": self.voice_id,
                    "pitch": self.pitch,
                    "pace": self.pace,
                    "loudness": self.loudness,
                    "enable_preprocessing": self.enable_preprocessing,
                    "output_audio_codec": "wav",
                    "output_audio_bitrate": "32k",
                    "max_chunk_length": 250,
                    "min_buffer_size": self.buffer_size
                }
            }
            await websocket.send(json.dumps(config_message))

            if not self.connection_time:
                self.connection_time = round((time.perf_counter() - start_time) * 1000)

            logger.info(f"[SARVAM_TTS] Connected to {self.ws_url} (latency: {self.connection_time}ms)")
            return websocket

        except asyncio.TimeoutError:
            logger.error("[SARVAM_TTS] Timeout while connecting to WebSocket")
            return None
        except InvalidHandshake as e:
            error_msg = str(e)
            if '401' in error_msg or '403' in error_msg:
                logger.error(f"[SARVAM_TTS] Authentication failed: Invalid or expired API key - {e}")
            elif '404' in error_msg:
                logger.error(f"[SARVAM_TTS] Endpoint not found: {e}")
            else:
                logger.error(f"[SARVAM_TTS] Handshake failed: {e}")
            return None
        except Exception as e:
            logger.error(f"[SARVAM_TTS] Failed to connect: {e}", exc_info=True)
            return None

    async def monitor_connection(self):
        """
        Monitor and maintain WebSocket connection
        """
        consecutive_failures = 0
        max_failures = 3

        while consecutive_failures < max_failures:
            if (self.websocket_holder["websocket"] is None or
                    self.websocket_holder["websocket"].state is websockets.protocol.State.CLOSED):
                logger.info("[SARVAM_TTS] Re-establishing connection...")
                result = await self.establish_connection()
                if result is None:
                    consecutive_failures += 1
                    logger.warning(f"[SARVAM_TTS] Connection failed (attempt {consecutive_failures}/{max_failures})")
                    if consecutive_failures >= max_failures:
                        logger.error("[SARVAM_TTS] Max connection failures reached - stopping reconnection")
                        break
                else:
                    self.websocket_holder["websocket"] = result
                    consecutive_failures = 0  # Reset on success
            await asyncio.sleep(1)

    def get_synthesized_characters(self):
        return self.synthesized_characters

    async def get_sender_task(self):
        return self.sender_task

    async def generate(self):
        """
        Main synthesis loop - receives audio from WebSocket receiver
        """
        try:
            if self.stream:
                async for message, text_spoken in self.receiver():
                    logger.debug(f"[SARVAM_TTS] Received audio message")

                    if len(self.text_queue) > 0:
                        self.meta_info = self.text_queue.popleft()
                        # Compute first-result latency on first audio chunk
                        try:
                            if self.current_turn_start_time is not None:
                                first_result_latency = time.perf_counter() - self.current_turn_start_time
                                self.meta_info['synthesizer_latency'] = first_result_latency
                        except Exception:
                            pass

                    audio = message

                    if not self.first_chunk_generated:
                        self.meta_info["is_first_chunk"] = True
                        self.first_chunk_generated = True
                    else:
                        self.meta_info["is_first_chunk"] = False

                    if self.last_text_sent:
                        # Reset for next turn
                        self.first_chunk_generated = False
                        self.last_text_sent = True

                    if message == b'\x00':
                        logger.info("[SARVAM_TTS] Received null byte - end of stream")
                        self.meta_info["end_of_synthesizer_stream"] = True
                        self.first_chunk_generated = False

                        # Compute total stream duration
                        try:
                            if self.current_turn_start_time is not None:
                                total_stream_duration = time.perf_counter() - self.current_turn_start_time
                                self.turn_latencies.append({
                                    'turn_id': self.current_turn_id,
                                    'sequence_id': self.current_turn_id,
                                    'first_result_latency_ms': round((self.meta_info.get('synthesizer_latency', 0)) * 1000),
                                    'total_stream_duration_ms': round(total_stream_duration * 1000)
                                })
                                self.current_turn_start_time = None
                                self.current_turn_id = None
                        except Exception:
                            pass
                    else:
                        # Resample and convert audio
                        resampled_audio = resample(audio, int(self.sampling_rate), format="wav")
                        pcm_audio = wav_bytes_to_pcm(resampled_audio)

                        if self.use_mulaw:
                            audio = pcm16_to_mulaw(pcm_audio)
                            self.meta_info['format'] = 'mulaw'
                        else:
                            audio = pcm_audio
                            self.meta_info['format'] = 'pcm'

                    self.meta_info["mark_id"] = str(uuid.uuid4())
                    yield create_ws_data_packet(audio, self.meta_info)

        except Exception as e:
            traceback.print_exc()
            logger.error(f"[SARVAM_TTS] Error in generate: {e}")

    async def push(self, message):
        """
        Push text to synthesis queue
        """
        if self.stream:
            meta_info = message.get("meta_info", {})
            text = message.get("data", "")
            self.current_text = text

            self.synthesized_characters += len(text) if text is not None else 0
            end_of_llm_stream = "end_of_llm_stream" in meta_info and meta_info["end_of_llm_stream"]

            self.meta_info = copy.deepcopy(meta_info)
            meta_info["text"] = text

            # Stamp synthesizer turn start time
            try:
                self.current_turn_start_time = time.perf_counter()
                self.current_turn_id = meta_info.get('turn_id') or meta_info.get('sequence_id')
            except Exception:
                pass

            self.sender_task = asyncio.create_task(
                self.sender(text, meta_info.get("sequence_id"), end_of_llm_stream)
            )
            self.text_queue.append(meta_info)
        else:
            await self.internal_queue.put(message)

    async def cleanup(self):
        """
        Cleanup resources and close connections
        """
        self.conversation_ended = True
        logger.info("[SARVAM_TTS] Cleaning up synthesizer tasks")

        if self.sender_task:
            try:
                self.sender_task.cancel()
                await self.sender_task
            except asyncio.CancelledError:
                logger.info("[SARVAM_TTS] Sender task cancelled successfully")

        if self.websocket_holder["websocket"]:
            await self.websocket_holder["websocket"].close()
        self.websocket_holder["websocket"] = None
        logger.info("[SARVAM_TTS] WebSocket connection closed")
    def _build_auth_headers(self):
        """Return headers required for Sarvam authentication."""
        return {
            'api-subscription-key': self.api_key,
            'api-key': self.api_key,
            'x-api-key': self.api_key,
            'authorization': f"Bearer {self.api_key}"
        }
