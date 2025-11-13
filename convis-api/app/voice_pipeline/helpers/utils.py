"""
Voice Pipeline Utility Functions
Essential helper functions for WebSocket communication and audio processing
"""
import time
import json
import copy
import io
import base64
from app.voice_pipeline.helpers.logger_config import configure_logger
from app.voice_pipeline.constants import DEFAULT_LANGUAGE_CODE, PRE_FUNCTION_CALL_MESSAGE, TRANSFERING_CALL_FILLER

logger = configure_logger(__name__)


def create_ws_data_packet(data, meta_info=None, is_md5_hash=False, llm_generated=False):
    """Create WebSocket data packet with metadata"""
    metadata = copy.deepcopy(meta_info) if meta_info else {}
    if meta_info is not None:
        metadata["is_md5_hash"] = is_md5_hash
        metadata["llm_generated"] = llm_generated
    return {
        'data': data,
        'meta_info': metadata
    }


def timestamp_ms() -> float:
    """Get current timestamp in milliseconds"""
    return time.time() * 1000


def now_ms() -> float:
    """Get current time in milliseconds using perf_counter"""
    return time.perf_counter() * 1000


def convert_audio_to_wav(audio_bytes, source_format='flac'):
    """
    Simplified audio converter - for now just returns the audio bytes as-is
    In production, this would convert audio formats using pydub/AudioSegment
    """
    logger.info(f"Audio conversion requested from {source_format} to WAV")
    # For Twilio integration, we typically receive/send μ-law format directly
    # so we don't need complex conversion
    return audio_bytes


def resample(audio_bytes, target_sample_rate, format="mp3"):
    """
    Simplified audio resampler - for now returns audio as-is
    In production, this would resample using torchaudio
    """
    logger.info(f"Audio resampling requested to {target_sample_rate}Hz")
    # Twilio uses 8kHz μ-law, which our providers handle natively
    return audio_bytes


def convert_to_request_log(message, meta_info, model, component="transcriber", direction='response', is_cached=False, engine=None, run_id=None):
    """
    Create request log dictionary for tracking
    Simplified version - just returns basic structure
    """
    return {
        'message': message,
        'meta_info': meta_info,
        'model': model,
        'component': component,
        'direction': direction,
        'is_cached': is_cached,
        'engine': engine,
        'run_id': run_id,
        'timestamp': timestamp_ms()
    }


def compute_function_pre_call_message(language, function_name, api_tool_pre_call_message):
    """
    Get filler message to play while executing function call
    """
    default_filler = PRE_FUNCTION_CALL_MESSAGE.get(language, PRE_FUNCTION_CALL_MESSAGE.get(DEFAULT_LANGUAGE_CODE))
    if "transfer" in function_name.lower():
        default_filler = TRANSFERING_CALL_FILLER.get(language, TRANSFERING_CALL_FILLER.get(DEFAULT_LANGUAGE_CODE))
    return api_tool_pre_call_message or default_filler
