"""
TTS (Text-to-Speech) Provider Abstraction
"""

import logging
import asyncio
from abc import ABC, abstractmethod
from typing import Optional, Dict
import os
import base64

logger = logging.getLogger(__name__)


class TTSProvider(ABC):
    """Base class for all TTS providers"""

    def __init__(self, api_key: str, voice: str = "default"):
        self.api_key = api_key
        self.voice = voice
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")

    @abstractmethod
    async def synthesize(self, text: str) -> bytes:
        """
        Convert text to speech

        Args:
            text: Text to convert to speech

        Returns:
            Audio bytes (PCM format)
        """
        pass

    @abstractmethod
    async def synthesize_stream(self, text: str) -> bytes:
        """
        Convert text to speech with streaming (for lower latency)

        Args:
            text: Text to convert to speech

        Returns:
            Audio bytes (PCM format)
        """
        pass

    @abstractmethod
    def get_latency_ms(self) -> int:
        """Get average latency in milliseconds"""
        pass

    @abstractmethod
    def get_cost_per_minute(self) -> float:
        """Get cost per minute of audio in USD"""
        pass

    @abstractmethod
    def get_available_voices(self) -> Dict[str, str]:
        """Get list of available voices"""
        pass


class CartesiaTTS(TTSProvider):
    """
    Cartesia Sonic TTS Provider

    Latency: 80-120ms (FASTEST)
    Cost: $0.005/min
    Best for: Ultra-low latency conversations
    """

    def __init__(self, api_key: Optional[str] = None, voice: str = "sonic"):
        super().__init__(
            api_key=api_key or os.getenv("CARTESIA_API_KEY"),
            voice=voice
        )
        self.client = None
        self._init_client()

    def _init_client(self):
        """Initialize Cartesia client"""
        try:
            from cartesia import Cartesia
            self.client = Cartesia(api_key=self.api_key)
            self.logger.info(f"Cartesia TTS initialized with voice: {self.voice}")
        except ImportError:
            self.logger.error("cartesia package not installed. Run: pip install cartesia")
            raise
        except Exception as e:
            self.logger.error(f"Failed to initialize Cartesia: {e}")
            raise

    async def synthesize(self, text: str) -> bytes:
        """Synthesize speech using Cartesia"""
        try:
            # Use Sonic English voice ID
            voice_id = "a0e99841-438c-4a64-b679-ae501e7d6091"  # Sonic (default fast voice)

            # Generate audio using bytes endpoint
            audio_chunks = []
            for chunk in self.client.tts.bytes(
                model_id="sonic-english",
                transcript=text,
                voice={
                    "mode": "id",
                    "id": voice_id
                },
                output_format={
                    "container": "raw",
                    "encoding": "pcm_s16le",
                    "sample_rate": 8000  # Match telephony sample rate
                }
            ):
                audio_chunks.append(chunk)

            return b''.join(audio_chunks)

        except Exception as e:
            self.logger.error(f"Cartesia synthesis error: {e}")
            raise

    async def synthesize_stream(self, text: str) -> bytes:
        """Cartesia streaming - just use bytes method (it's already fast)"""
        # The bytes method is already very fast, no need for separate streaming
        return await self.synthesize(text)

    def get_latency_ms(self) -> int:
        """Average latency: 80-120ms"""
        return 100

    def get_cost_per_minute(self) -> float:
        """Cost: $0.005/min"""
        return 0.005

    def get_available_voices(self) -> Dict[str, str]:
        """Available Cartesia voices"""
        return {
            "sonic": "Fast, natural voice",
            "stella": "Warm, friendly female voice",
            "marcus": "Professional male voice"
        }


class ElevenLabsTTS(TTSProvider):
    """
    ElevenLabs TTS Provider

    Latency: 100-200ms
    Cost: $0.018/min (Turbo) or $0.06/min (Standard)
    Best for: High-quality, natural voices
    """

    def __init__(self, api_key: Optional[str] = None, voice: str = "rachel"):
        super().__init__(
            api_key=api_key or os.getenv("ELEVENLABS_API_KEY"),
            voice=voice
        )
        self.client = None
        self._init_client()

    def _init_client(self):
        """Initialize ElevenLabs client"""
        try:
            from elevenlabs import ElevenLabs
            self.client = ElevenLabs(api_key=self.api_key)
            self.logger.info(f"ElevenLabs TTS initialized with voice: {self.voice}")
        except ImportError:
            self.logger.error("elevenlabs package not installed. Run: pip install elevenlabs")
            raise
        except Exception as e:
            self.logger.error(f"Failed to initialize ElevenLabs: {e}")
            raise

    async def synthesize(self, text: str) -> bytes:
        """Synthesize speech using ElevenLabs"""
        try:
            audio = await self.client.generate(
                text=text,
                voice=self.voice,
                model="eleven_turbo_v2",  # Fastest model
                output_format="pcm_16000"
            )

            return audio

        except Exception as e:
            self.logger.error(f"ElevenLabs synthesis error: {e}")
            raise

    async def synthesize_stream(self, text: str) -> bytes:
        """ElevenLabs streaming for lower latency"""
        try:
            audio_chunks = []

            async for chunk in self.client.stream(
                text=text,
                voice=self.voice,
                model="eleven_turbo_v2"
            ):
                audio_chunks.append(chunk)

            return b''.join(audio_chunks)

        except Exception as e:
            self.logger.error(f"ElevenLabs streaming error: {e}")
            return await self.synthesize(text)

    def get_latency_ms(self) -> int:
        """Average latency: 100-200ms"""
        return 150

    def get_cost_per_minute(self) -> float:
        """Cost: $0.018/min (Turbo model)"""
        return 0.018

    def get_available_voices(self) -> Dict[str, str]:
        """Available ElevenLabs voices"""
        return {
            "rachel": "Young female American voice",
            "domi": "Strong female American voice",
            "bella": "Soft young American female",
            "antoni": "Well-rounded male voice",
            "josh": "Deep American male voice",
            "arnold": "Crisp American male"
        }


class OpenAITTS(TTSProvider):
    """
    OpenAI TTS Provider

    Latency: 200-300ms
    Cost: $0.015/min (tts-1) or $0.030/min (tts-1-hd)
    Best for: Good quality, reliable
    """

    def __init__(self, api_key: Optional[str] = None, voice: str = "alloy"):
        super().__init__(
            api_key=api_key or os.getenv("OPENAI_API_KEY"),
            voice=voice
        )
        self.client = None
        self._init_client()

    def _init_client(self):
        """Initialize OpenAI client"""
        try:
            import openai
            self.client = openai.AsyncOpenAI(api_key=self.api_key)
            self.logger.info(f"OpenAI TTS initialized with voice: {self.voice}")
        except ImportError:
            self.logger.error("openai package not installed. Run: pip install openai")
            raise
        except Exception as e:
            self.logger.error(f"Failed to initialize OpenAI: {e}")
            raise

    async def synthesize(self, text: str) -> bytes:
        """Synthesize speech using OpenAI"""
        try:
            response = await self.client.audio.speech.create(
                model="tts-1",  # Faster model
                voice=self.voice,
                input=text,
                response_format="pcm"
            )

            return response.content

        except Exception as e:
            self.logger.error(f"OpenAI synthesis error: {e}")
            raise

    async def synthesize_stream(self, text: str) -> bytes:
        """OpenAI TTS with streaming response"""
        try:
            response = await self.client.audio.speech.create(
                model="tts-1",
                voice=self.voice,
                input=text,
                response_format="pcm"
            )

            return response.content

        except Exception as e:
            self.logger.error(f"OpenAI streaming error: {e}")
            return await self.synthesize(text)

    def get_latency_ms(self) -> int:
        """Average latency: 200-300ms"""
        return 250

    def get_cost_per_minute(self) -> float:
        """Cost: $0.015/min (tts-1 model)"""
        return 0.015

    def get_available_voices(self) -> Dict[str, str]:
        """Available OpenAI voices"""
        return {
            "alloy": "Neutral, balanced voice",
            "echo": "Male voice",
            "fable": "British male voice",
            "onyx": "Deep male voice",
            "nova": "Female voice",
            "shimmer": "Soft female voice"
        }
