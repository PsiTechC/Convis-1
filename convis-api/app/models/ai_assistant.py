from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime

from app.constants import DEFAULT_CALL_GREETING

class AIAssistantCreate(BaseModel):
    user_id: str
    name: str
    system_message: str
    voice: str = "alloy"
    temperature: float = Field(default=0.6, ge=0.0, le=2.0)
    api_key_id: Optional[str] = None  # Reference to stored API key
    openai_api_key: Optional[str] = None  # Legacy direct key support
    call_greeting: Optional[str] = Field(default=None)
    calendar_account_id: Optional[str] = None  # Reference to calendar account for scheduling (deprecated, use calendar_account_ids)
    calendar_account_ids: Optional[List[str]] = []  # Multiple calendar accounts for availability checking and scheduling
    calendar_enabled: Optional[bool] = False  # Enable calendar functionality

    # Provider selection
    asr_provider: Optional[str] = "openai"  # openai, deepgram, groq
    tts_provider: Optional[str] = "openai"  # openai, cartesia, elevenlabs

    # ASR Configuration
    asr_language: Optional[str] = "en"  # Language code for ASR
    asr_model: Optional[str] = None  # Model for ASR (e.g., nova-2 for Deepgram, whisper-1 for OpenAI)
    asr_keywords: Optional[List[str]] = []  # Keywords to boost in ASR

    # TTS Configuration
    tts_model: Optional[str] = None  # Model for TTS
    tts_speed: Optional[float] = Field(default=1.0, ge=0.25, le=4.0)  # Speech speed multiplier
    tts_voice: Optional[str] = None  # Voice identifier for TTS engines

    # Transcription & Interruptions
    enable_precise_transcript: Optional[bool] = False  # Generate more precise transcripts during interruptions
    interruption_threshold: Optional[int] = Field(default=2, ge=1, le=10)  # Number of words before allowing interruption

    # Voice Response Rate
    response_rate: Optional[str] = "balanced"  # rapid, balanced, relaxed

    # User Online Detection
    check_user_online: Optional[bool] = True  # Check if user is online during call

    # Buffer & Latency Settings
    audio_buffer_size: Optional[int] = Field(default=200, ge=50, le=1000)  # Audio buffer size in ms

    # LLM Configuration
    llm_provider: Optional[str] = "openai"  # openai, anthropic, groq
    llm_model: Optional[str] = None  # e.g., gpt-4o, gpt-4o-mini, claude-3-5-sonnet
    llm_max_tokens: Optional[int] = Field(default=150, ge=50, le=4000)  # Max tokens in response

    # Language Configuration
    bot_language: Optional[str] = "en"  # Language for bot responses (en, hi, es, fr, de, etc.)

class AIAssistantUpdate(BaseModel):
    name: Optional[str] = None
    system_message: Optional[str] = None
    voice: Optional[str] = None
    temperature: Optional[float] = Field(default=None, ge=0.0, le=2.0)
    api_key_id: Optional[str] = None  # Update to a stored API key
    openai_api_key: Optional[str] = None  # Legacy direct key update
    call_greeting: Optional[str] = Field(default=None)
    calendar_account_id: Optional[str] = None  # Update calendar account reference (deprecated, use calendar_account_ids)
    calendar_account_ids: Optional[List[str]] = None  # Update multiple calendar accounts
    calendar_enabled: Optional[bool] = None  # Enable/disable calendar functionality

    # Provider selection
    asr_provider: Optional[str] = None  # openai, deepgram, groq
    tts_provider: Optional[str] = None  # openai, cartesia, elevenlabs

    # ASR Configuration
    asr_language: Optional[str] = None
    asr_model: Optional[str] = None
    asr_keywords: Optional[List[str]] = None

    # TTS Configuration
    tts_model: Optional[str] = None
    tts_speed: Optional[float] = Field(default=None, ge=0.25, le=4.0)
    tts_voice: Optional[str] = None

    # Transcription & Interruptions
    enable_precise_transcript: Optional[bool] = None
    interruption_threshold: Optional[int] = Field(default=None, ge=1, le=10)

    # Voice Response Rate
    response_rate: Optional[str] = None  # rapid, balanced, relaxed

    # User Online Detection
    check_user_online: Optional[bool] = None

    # Buffer & Latency Settings
    audio_buffer_size: Optional[int] = Field(default=None, ge=50, le=1000)

    # LLM Configuration
    llm_provider: Optional[str] = None  # openai, anthropic, groq
    llm_model: Optional[str] = None  # e.g., gpt-4o, gpt-4o-mini, claude-3-5-sonnet
    llm_max_tokens: Optional[int] = Field(default=None, ge=50, le=4000)  # Max tokens in response

    # Language Configuration
    bot_language: Optional[str] = None  # Language for bot responses

class KnowledgeBaseFile(BaseModel):
    filename: str
    file_type: str
    file_size: int
    uploaded_at: str
    file_path: str

class DatabaseConfig(BaseModel):
    enabled: bool = False
    type: str = "postgresql"  # postgresql, mysql, mongodb
    host: str = ""
    port: str = "5432"
    database: str = ""
    username: str = ""
    password: str = ""
    table_name: str = ""
    search_columns: List[str] = []

class AIAssistantResponse(BaseModel):
    id: str
    user_id: str
    name: str
    system_message: str
    voice: str
    temperature: float
    call_greeting: str = Field(default=DEFAULT_CALL_GREETING)
    has_api_key: bool  # Indicates if OpenAI API key is configured
    api_key_id: Optional[str] = None
    api_key_label: Optional[str] = None
    api_key_provider: Optional[str] = None
    knowledge_base_files: List[KnowledgeBaseFile] = []
    has_knowledge_base: bool = False
    database_config: Optional[DatabaseConfig] = None
    calendar_account_id: Optional[str] = None  # Linked calendar account for scheduling (deprecated)
    calendar_account_email: Optional[str] = None  # Email of linked calendar for display (deprecated)
    calendar_account_ids: List[str] = []  # Multiple linked calendar accounts
    calendar_enabled: bool = False  # Calendar functionality enabled
    last_calendar_used_index: int = -1  # For round-robin scheduling
    frejun_flow_token: str
    frejun_flow_url: str

    # Provider selection
    asr_provider: str = "openai"  # openai, deepgram, groq
    tts_provider: str = "openai"  # openai, cartesia, elevenlabs

    # ASR Configuration
    asr_language: str = "en"
    asr_model: Optional[str] = None
    asr_keywords: List[str] = []

    # TTS Configuration
    tts_model: Optional[str] = None
    tts_speed: float = 1.0
    tts_voice: Optional[str] = None

    # Transcription & Interruptions
    enable_precise_transcript: bool = False
    interruption_threshold: int = 2

    # Voice Response Rate
    response_rate: str = "balanced"

    # User Online Detection
    check_user_online: bool = True

    # Buffer & Latency Settings
    audio_buffer_size: int = 200

    # LLM Configuration
    llm_provider: str = "openai"
    llm_model: Optional[str] = None
    llm_max_tokens: int = 150

    # Language Configuration
    bot_language: str = "en"  # Language for bot responses

    created_at: str
    updated_at: str

class AIAssistantListResponse(BaseModel):
    assistants: list[AIAssistantResponse]
    total: int

class DeleteResponse(BaseModel):
    message: str

class FileUploadResponse(BaseModel):
    message: str
    file: KnowledgeBaseFile
    total_files: int

class DatabaseConnectionTestRequest(BaseModel):
    enabled: bool
    type: str
    host: str
    port: str
    database: str
    username: str
    password: str
    table_name: str
    search_columns: List[str]

class DatabaseConnectionTestResponse(BaseModel):
    success: bool
    message: str
    record_count: Optional[int] = None
