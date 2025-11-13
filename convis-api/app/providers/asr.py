"""
ASR (Automatic Speech Recognition) Provider Abstraction
"""

import logging
import asyncio
from abc import ABC, abstractmethod
from typing import AsyncIterator, Optional
import os

logger = logging.getLogger(__name__)


class ASRProvider(ABC):
    """Base class for all ASR providers"""

    def __init__(self, api_key: str, model: str = "default", language: str = "en"):
        self.api_key = api_key
        self.model = model
        self.language = language
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")

    @abstractmethod
    async def transcribe_stream(self, audio_stream: AsyncIterator[bytes]) -> AsyncIterator[str]:
        """
        Transcribe streaming audio in real-time

        Args:
            audio_stream: Async iterator of audio chunks (PCM bytes)

        Yields:
            Transcribed text chunks
        """
        pass

    @abstractmethod
    async def transcribe(self, audio_bytes: bytes) -> str:
        """
        Transcribe complete audio file

        Args:
            audio_bytes: Complete audio data (PCM bytes)

        Returns:
            Complete transcription text
        """
        pass

    @abstractmethod
    def get_latency_ms(self) -> int:
        """Get average latency in milliseconds"""
        pass

    @abstractmethod
    def get_cost_per_minute(self) -> float:
        """Get cost per minute in USD"""
        pass


class DeepgramASR(ASRProvider):
    """
    Deepgram Nova-2 ASR Provider

    Latency: 50-100ms
    Cost: $0.0043/min
    Best for: Fast, accurate transcription
    """

    def __init__(self, api_key: Optional[str] = None, model: str = "nova-2", language: str = "en"):
        super().__init__(
            api_key=api_key or os.getenv("DEEPGRAM_API_KEY"),
            model=model,
            language=language
        )
        self.deepgram = None
        self._init_client()

    def _init_client(self):
        """Initialize Deepgram client"""
        try:
            from deepgram import DeepgramClient
            self.deepgram = DeepgramClient(api_key=self.api_key)
            self.logger.info(f"Deepgram ASR initialized with model: {self.model}")
        except ImportError:
            self.logger.error("deepgram-sdk not installed. Run: pip install deepgram-sdk")
            raise
        except Exception as e:
            self.logger.error(f"Failed to initialize Deepgram: {e}")
            raise

    async def transcribe_stream(self, audio_stream: AsyncIterator[bytes]) -> AsyncIterator[str]:
        """
        Stream transcription using Deepgram Live API
        """
        try:
            # Deepgram live transcription options
            options = {
                'punctuate': True,
                'model': self.model,
                'language': self.language,
                'encoding': 'linear16',
                'sample_rate': 8000,  # FreJun/Twilio use 8kHz
                'channels': 1,
                'interim_results': False,  # Only final results
                'endpointing': 300  # End of speech detection (300ms)
            }

            # Create live transcription connection
            deepgramLive = await self.deepgram.transcription.live(options)

            # Handle transcription results
            async def handle_transcript(transcript):
                if transcript:
                    text = transcript.get('channel', {}).get('alternatives', [{}])[0].get('transcript', '')
                    if text:
                        yield text

            deepgramLive.registerHandler(
                deepgramLive.event.TRANSCRIPT_RECEIVED,
                handle_transcript
            )

            # Stream audio chunks
            async for audio_chunk in audio_stream:
                deepgramLive.send(audio_chunk)

            # Close connection
            deepgramLive.finish()

        except Exception as e:
            self.logger.error(f"Deepgram streaming error: {e}")
            raise

    async def transcribe(self, audio_bytes: bytes) -> str:
        """
        Transcribe complete audio using Deepgram Pre-recorded API
        """
        try:
            from deepgram import PrerecordedOptions, FileSource

            options = PrerecordedOptions(
                model=self.model,
                punctuate=True,
                language=self.language
            )

            payload = FileSource(buffer=audio_bytes)

            response = await self.deepgram.listen.asyncrest.v("1").transcribe_file(
                payload,
                options
            )

            transcript = response['results']['channels'][0]['alternatives'][0]['transcript']
            return transcript

        except Exception as e:
            self.logger.error(f"Deepgram transcription error: {e}")
            raise

    def get_latency_ms(self) -> int:
        """Average latency: 50-100ms"""
        return 75

    def get_cost_per_minute(self) -> float:
        """Cost: $0.0043/min"""
        return 0.0043


class OpenAIASR(ASRProvider):
    """
    OpenAI Whisper ASR Provider

    Latency: 200-300ms
    Cost: $0.006/min (Whisper API)
    Best for: High accuracy, multiple languages
    """

    def __init__(self, api_key: Optional[str] = None, model: str = "whisper-1", language: str = "en"):
        super().__init__(
            api_key=api_key or os.getenv("OPENAI_API_KEY"),
            model=model,
            language=language
        )
        self.client = None
        self._init_client()

    def _init_client(self):
        """Initialize OpenAI client"""
        try:
            import openai
            self.client = openai.AsyncOpenAI(api_key=self.api_key)
            self.logger.info(f"OpenAI ASR initialized with model: {self.model}")
        except ImportError:
            self.logger.error("openai package not installed. Run: pip install openai")
            raise
        except Exception as e:
            self.logger.error(f"Failed to initialize OpenAI: {e}")
            raise

    async def transcribe_stream(self, audio_stream: AsyncIterator[bytes]) -> AsyncIterator[str]:
        """
        OpenAI Whisper doesn't support true streaming,
        so we accumulate chunks and transcribe periodically
        """
        buffer = bytearray()
        chunk_size = 16000 * 2  # 1 second at 16kHz, 16-bit

        async for audio_chunk in audio_stream:
            buffer.extend(audio_chunk)

            # Transcribe every 1 second of audio
            if len(buffer) >= chunk_size:
                try:
                    # Save to temporary file (Whisper requires file)
                    import tempfile
                    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as temp_file:
                        temp_file.write(bytes(buffer))
                        temp_path = temp_file.name

                    # Transcribe
                    with open(temp_path, "rb") as audio_file:
                        transcript = await self.client.audio.transcriptions.create(
                            model=self.model,
                            file=audio_file,
                            language=self.language
                        )

                    # Clean up
                    os.unlink(temp_path)

                    if transcript.text:
                        yield transcript.text

                    buffer.clear()

                except Exception as e:
                    self.logger.error(f"OpenAI transcription error: {e}")

    async def transcribe(self, audio_bytes: bytes) -> str:
        """Transcribe complete audio"""
        try:
            import tempfile
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as temp_file:
                temp_file.write(audio_bytes)
                temp_path = temp_file.name

            with open(temp_path, "rb") as audio_file:
                transcript = await self.client.audio.transcriptions.create(
                    model=self.model,
                    file=audio_file,
                    language=self.language
                )

            os.unlink(temp_path)
            return transcript.text

        except Exception as e:
            self.logger.error(f"OpenAI transcription error: {e}")
            raise

    def get_latency_ms(self) -> int:
        """Average latency: 200-300ms"""
        return 250

    def get_cost_per_minute(self) -> float:
        """Cost: $0.006/min"""
        return 0.006
