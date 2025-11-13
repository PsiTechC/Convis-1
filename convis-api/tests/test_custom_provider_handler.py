"""
Unit tests for Custom Provider Handler
Tests all ASR, LLM, and TTS provider integrations
"""
import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch, MagicMock
import json
import base64

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.utils.custom_provider_handler import CustomProviderHandler


class TestCustomProviderHandler:
    """Test suite for CustomProviderHandler"""

    @pytest.fixture
    def mock_websocket(self):
        """Create mock WebSocket"""
        ws = AsyncMock()
        ws.send = AsyncMock()
        return ws

    @pytest.fixture
    def assistant_config(self):
        """Base assistant configuration"""
        return {
            'system_message': 'You are a helpful assistant',
            'call_greeting': 'Hello!',
            'temperature': 0.8,
            'asr_provider': 'deepgram',
            'asr_model': 'nova-3',
            'asr_language': 'en',
            'llm_provider': 'openai',
            'llm_model': 'gpt-4o-mini',
            'llm_max_tokens': 150,
            'tts_provider': 'sarvam',
            'tts_model': 'bulbul:v2',
            'tts_voice': 'Manisha',
            'tts_speed': 1.0
        }

    @pytest.fixture
    def api_keys(self):
        """Mock API keys"""
        return {
            'openai': 'test-openai-key',
            'deepgram': 'test-deepgram-key',
            'sarvam': 'test-sarvam-key',
            'azure': 'test-azure-key',
            'assembly': 'test-assembly-key',
            'google': 'test-google-key',
            'cartesia': 'test-cartesia-key',
            'elevenlabs': 'test-elevenlabs-key',
            'anthropic': 'test-anthropic-key',
            'deepseek': 'test-deepseek-key',
            'openrouter': 'test-openrouter-key',
            'groq': 'test-groq-key'
        }

    @pytest.fixture
    def handler(self, mock_websocket, assistant_config, api_keys):
        """Create handler instance"""
        return CustomProviderHandler(mock_websocket, assistant_config, api_keys)

    # ==================== ASR Provider Tests ====================

    def test_asr_provider_routing(self, handler):
        """Test ASR provider routing logic"""
        # Test that handler initializes with correct provider
        assert handler.asr_provider == 'deepgram'
        assert handler.asr_model == 'nova-3'
        assert handler.asr_language == 'en'

    @pytest.mark.asyncio
    async def test_transcribe_deepgram_success(self, handler):
        """Test Deepgram transcription success"""
        mock_response = {
            'results': {
                'channels': [{
                    'alternatives': [{
                        'transcript': 'Hello world'
                    }]
                }]
            }
        }

        with patch('httpx.AsyncClient') as mock_client:
            mock_post = AsyncMock()
            mock_post.return_value.status_code = 200
            mock_post.return_value.json.return_value = mock_response
            mock_client.return_value.__aenter__.return_value.post = mock_post

            result = await handler.transcribe_deepgram(b'test_audio_data')
            assert result == 'Hello world'

    @pytest.mark.asyncio
    async def test_transcribe_openai_whisper_success(self, handler):
        """Test OpenAI Whisper transcription success"""
        mock_response = {
            'text': 'Hello from whisper'
        }

        with patch('httpx.AsyncClient') as mock_client:
            mock_post = AsyncMock()
            mock_post.return_value.status_code = 200
            mock_post.return_value.json.return_value = mock_response
            mock_client.return_value.__aenter__.return_value.post = mock_post

            result = await handler.transcribe_openai(b'test_audio_data')
            assert result == 'Hello from whisper'

    @pytest.mark.asyncio
    async def test_transcribe_azure_success(self, handler):
        """Test Azure Speech Services transcription success"""
        mock_response = {
            'DisplayText': 'Azure transcription'
        }

        with patch('httpx.AsyncClient') as mock_client:
            mock_post = AsyncMock()
            mock_post.return_value.status_code = 200
            mock_post.return_value.json.return_value = mock_response
            mock_client.return_value.__aenter__.return_value.post = mock_post

            result = await handler.transcribe_azure(b'test_audio_data')
            assert result == 'Azure transcription'

    @pytest.mark.asyncio
    async def test_transcribe_sarvam_success(self, handler):
        """Test Sarvam AI transcription success"""
        mock_response = {
            'transcript': 'Sarvam transcription'
        }

        with patch('httpx.AsyncClient') as mock_client:
            mock_post = AsyncMock()
            mock_post.return_value.status_code = 200
            mock_post.return_value.json.return_value = mock_response
            mock_client.return_value.__aenter__.return_value.post = mock_post

            result = await handler.transcribe_sarvam(b'test_audio_data')
            assert result == 'Sarvam transcription'

    @pytest.mark.asyncio
    async def test_transcribe_google_success(self, handler):
        """Test Google Speech-to-Text success"""
        mock_response = {
            'results': [{
                'alternatives': [{
                    'transcript': 'Google transcription'
                }]
            }]
        }

        with patch('httpx.AsyncClient') as mock_client:
            mock_post = AsyncMock()
            mock_post.return_value.status_code = 200
            mock_post.return_value.json.return_value = mock_response
            mock_client.return_value.__aenter__.return_value.post = mock_post

            result = await handler.transcribe_google(b'test_audio_data')
            assert result == 'Google transcription'

    @pytest.mark.asyncio
    async def test_transcribe_no_api_key(self, mock_websocket, assistant_config):
        """Test ASR without API key"""
        handler = CustomProviderHandler(mock_websocket, assistant_config, {})
        result = await handler.transcribe_deepgram(b'test_audio_data')
        assert result is None

    # ==================== LLM Provider Tests ====================

    def test_llm_provider_routing(self, handler):
        """Test LLM provider routing logic"""
        assert handler.llm_provider == 'openai'
        assert handler.llm_model == 'gpt-4o-mini'
        assert handler.llm_max_tokens == 150

    @pytest.mark.asyncio
    async def test_generate_openai_response_success(self, handler):
        """Test OpenAI LLM response generation"""
        mock_response = {
            'choices': [{
                'message': {
                    'content': 'OpenAI response'
                }
            }]
        }

        with patch('httpx.AsyncClient') as mock_client:
            mock_post = AsyncMock()
            mock_post.return_value.status_code = 200
            mock_post.return_value.json.return_value = mock_response
            mock_client.return_value.__aenter__.return_value.post = mock_post

            result = await handler.generate_openai_response()
            assert result == 'OpenAI response'

    @pytest.mark.asyncio
    async def test_generate_anthropic_response_success(self, handler):
        """Test Anthropic Claude response generation"""
        handler.llm_provider = 'anthropic'
        mock_response = {
            'content': [{
                'text': 'Claude response'
            }]
        }

        with patch('httpx.AsyncClient') as mock_client:
            mock_post = AsyncMock()
            mock_post.return_value.status_code = 200
            mock_post.return_value.json.return_value = mock_response
            mock_client.return_value.__aenter__.return_value.post = mock_post

            result = await handler.generate_anthropic_response()
            assert result == 'Claude response'

    @pytest.mark.asyncio
    async def test_generate_deepseek_response_success(self, handler):
        """Test Deepseek response generation"""
        mock_response = {
            'choices': [{
                'message': {
                    'content': 'Deepseek response'
                }
            }]
        }

        with patch('httpx.AsyncClient') as mock_client:
            mock_post = AsyncMock()
            mock_post.return_value.status_code = 200
            mock_post.return_value.json.return_value = mock_response
            mock_client.return_value.__aenter__.return_value.post = mock_post

            result = await handler.generate_deepseek_response()
            assert result == 'Deepseek response'

    @pytest.mark.asyncio
    async def test_generate_groq_response_success(self, handler):
        """Test Groq response generation"""
        mock_response = {
            'choices': [{
                'message': {
                    'content': 'Groq response'
                }
            }]
        }

        with patch('httpx.AsyncClient') as mock_client:
            mock_post = AsyncMock()
            mock_post.return_value.status_code = 200
            mock_post.return_value.json.return_value = mock_response
            mock_client.return_value.__aenter__.return_value.post = mock_post

            result = await handler.generate_groq_response()
            assert result == 'Groq response'

    # ==================== TTS Provider Tests ====================

    def test_tts_provider_routing(self, handler):
        """Test TTS provider routing logic"""
        assert handler.tts_provider == 'sarvam'
        assert handler.tts_model == 'bulbul:v2'
        assert handler.tts_voice == 'Manisha'

    @pytest.mark.asyncio
    async def test_synthesize_openai_success(self, handler):
        """Test OpenAI TTS synthesis"""
        mock_audio = b'openai_audio_data'

        with patch('httpx.AsyncClient') as mock_client:
            mock_post = AsyncMock()
            mock_post.return_value.status_code = 200
            mock_post.return_value.content = mock_audio
            mock_client.return_value.__aenter__.return_value.post = mock_post

            result = await handler.synthesize_openai('Test text')
            assert result == mock_audio

    @pytest.mark.asyncio
    async def test_synthesize_cartesia_success(self, handler):
        """Test Cartesia TTS synthesis"""
        mock_audio = b'cartesia_audio_data'

        with patch('httpx.AsyncClient') as mock_client:
            mock_post = AsyncMock()
            mock_post.return_value.status_code = 200
            mock_post.return_value.content = mock_audio
            mock_client.return_value.__aenter__.return_value.post = mock_post

            result = await handler.synthesize_cartesia('Test text')
            assert result == mock_audio

    @pytest.mark.asyncio
    async def test_synthesize_sarvam_success(self, handler):
        """Test Sarvam TTS synthesis"""
        mock_audio_base64 = base64.b64encode(b'sarvam_audio').decode('utf-8')
        mock_response = {
            'audios': [mock_audio_base64]
        }

        with patch('httpx.AsyncClient') as mock_client:
            mock_post = AsyncMock()
            mock_post.return_value.status_code = 200
            mock_post.return_value.json.return_value = mock_response
            mock_client.return_value.__aenter__.return_value.post = mock_post

            result = await handler.synthesize_sarvam('Test text')
            assert result == b'sarvam_audio'

    @pytest.mark.asyncio
    async def test_synthesize_azuretts_success(self, handler):
        """Test Azure TTS synthesis"""
        mock_audio = b'azure_audio_data'

        with patch('httpx.AsyncClient') as mock_client:
            mock_post = AsyncMock()
            mock_post.return_value.status_code = 200
            mock_post.return_value.content = mock_audio
            mock_client.return_value.__aenter__.return_value.post = mock_post

            result = await handler.synthesize_azuretts('Test text')
            assert result == mock_audio

    @pytest.mark.asyncio
    async def test_synthesize_elevenlabs_success(self, handler):
        """Test ElevenLabs TTS synthesis"""
        mock_audio = b'elevenlabs_audio_data'

        with patch('httpx.AsyncClient') as mock_client:
            mock_post = AsyncMock()
            mock_post.return_value.status_code = 200
            mock_post.return_value.content = mock_audio
            mock_client.return_value.__aenter__.return_value.post = mock_post

            result = await handler.synthesize_elevenlabs('Test text')
            assert result == mock_audio

    # ==================== Integration Tests ====================

    @pytest.mark.asyncio
    async def test_handle_start_event(self, handler):
        """Test handling call start event"""
        start_message = {
            'event': 'start',
            'start': {
                'streamSid': 'test-stream-sid',
                'callSid': 'test-call-sid'
            }
        }

        with patch.object(handler, 'synthesize_and_send', new_callable=AsyncMock) as mock_synth:
            await handler.handle_start(start_message)

            assert handler.stream_sid == 'test-stream-sid'
            assert handler.call_sid == 'test-call-sid'
            mock_synth.assert_called_once()

    @pytest.mark.asyncio
    async def test_handle_media_event(self, handler):
        """Test handling media event"""
        audio_payload = base64.b64encode(b'test_audio').decode('utf-8')
        media_message = {
            'event': 'media',
            'media': {
                'payload': audio_payload
            }
        }

        await handler.handle_media(media_message)

        # Check that audio buffer was populated
        assert len(handler.audio_buffer) > 0

    @pytest.mark.asyncio
    async def test_process_audio_buffer_pipeline(self, handler):
        """Test complete pipeline: ASR -> LLM -> TTS"""
        handler.stream_sid = 'test-stream-sid'
        handler.audio_buffer = b'test_audio_data'

        # Mock all pipeline steps
        with patch.object(handler, 'transcribe_audio', new_callable=AsyncMock) as mock_asr, \
             patch.object(handler, 'generate_llm_response', new_callable=AsyncMock) as mock_llm, \
             patch.object(handler, 'synthesize_and_send', new_callable=AsyncMock) as mock_tts:

            mock_asr.return_value = 'Hello'
            mock_llm.return_value = 'Hi there!'

            await handler.process_audio_buffer()

            mock_asr.assert_called_once()
            mock_llm.assert_called_once_with('Hello')
            mock_tts.assert_called_once_with('Hi there!')

    @pytest.mark.asyncio
    async def test_conversation_history_tracking(self, handler):
        """Test that conversation history is maintained"""
        initial_length = len(handler.conversation_history)

        with patch('httpx.AsyncClient') as mock_client:
            mock_response = {
                'choices': [{
                    'message': {
                        'content': 'Response'
                    }
                }]
            }
            mock_post = AsyncMock()
            mock_post.return_value.status_code = 200
            mock_post.return_value.json.return_value = mock_response
            mock_client.return_value.__aenter__.return_value.post = mock_post

            await handler.generate_llm_response('User message')

        # Should have user message + assistant response
        assert len(handler.conversation_history) == initial_length + 2
        assert handler.conversation_history[-2]['role'] == 'user'
        assert handler.conversation_history[-1]['role'] == 'assistant'

    @pytest.mark.asyncio
    async def test_send_audio_to_twilio(self, handler):
        """Test sending audio to Twilio"""
        handler.stream_sid = 'test-stream-sid'
        test_audio = b'test_audio_data'

        await handler.send_audio_to_twilio(test_audio)

        # Verify WebSocket send was called
        assert handler.twilio_ws.send.called

    # ==================== Error Handling Tests ====================

    @pytest.mark.asyncio
    async def test_transcribe_with_error(self, handler):
        """Test ASR error handling"""
        with patch('httpx.AsyncClient') as mock_client:
            mock_post = AsyncMock()
            mock_post.return_value.status_code = 500
            mock_client.return_value.__aenter__.return_value.post = mock_post

            result = await handler.transcribe_deepgram(b'test_audio')
            assert result is None

    @pytest.mark.asyncio
    async def test_llm_with_error(self, handler):
        """Test LLM error handling"""
        with patch('httpx.AsyncClient') as mock_client:
            mock_post = AsyncMock()
            mock_post.return_value.status_code = 500
            mock_client.return_value.__aenter__.return_value.post = mock_post

            result = await handler.generate_openai_response()
            assert result is None

    @pytest.mark.asyncio
    async def test_tts_with_error(self, handler):
        """Test TTS error handling"""
        with patch('httpx.AsyncClient') as mock_client:
            mock_post = AsyncMock()
            mock_post.return_value.status_code = 500
            mock_client.return_value.__aenter__.return_value.post = mock_post

            result = await handler.synthesize_openai('Test')
            assert result is None

    @pytest.mark.asyncio
    async def test_unsupported_asr_provider(self, mock_websocket, assistant_config, api_keys):
        """Test unsupported ASR provider"""
        assistant_config['asr_provider'] = 'unsupported_provider'
        handler = CustomProviderHandler(mock_websocket, assistant_config, api_keys)

        result = await handler.transcribe_audio(b'test_audio')
        assert result is None

    @pytest.mark.asyncio
    async def test_unsupported_tts_provider(self, mock_websocket, assistant_config, api_keys):
        """Test unsupported TTS provider"""
        assistant_config['tts_provider'] = 'unsupported_provider'
        handler = CustomProviderHandler(mock_websocket, assistant_config, api_keys)

        with patch.object(handler, 'send_audio_to_twilio', new_callable=AsyncMock):
            await handler.synthesize_and_send('Test')
            # Should not crash, just log error


if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short'])
