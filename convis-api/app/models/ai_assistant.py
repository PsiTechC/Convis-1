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

class AIAssistantUpdate(BaseModel):
    name: Optional[str] = None
    system_message: Optional[str] = None
    voice: Optional[str] = None
    temperature: Optional[float] = Field(default=None, ge=0.0, le=2.0)
    api_key_id: Optional[str] = None  # Update to a stored API key
    openai_api_key: Optional[str] = None  # Legacy direct key update
    call_greeting: Optional[str] = Field(default=None)

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
