from pydantic_settings import BaseSettings
from typing import Optional
import os
import logging

logger = logging.getLogger(__name__)

class Settings(BaseSettings):
    # MongoDB Configuration
    mongodb_uri: str
    database_name: str

    # Email Configuration
    email_user: str
    email_pass: str
    smtp_host: str = "p1432.use1.mysecurecloudhost.com"
    smtp_port: int = 465
    smtp_use_ssl: bool = True

    # Application Configuration
    frontend_url: str = "http://localhost:3000"
    jwt_secret: str = "default_secret_change_in_production"

    # OpenAI Configuration
    openai_api_key: Optional[str] = None

    # Encryption Configuration (for production)
    encryption_key: Optional[str] = None

    # Environment
    environment: str = "development"  # development, staging, production

    # API Configuration
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    api_base_url: Optional[str] = None  # For webhook URLs in production

    # Twilio Configuration (optional defaults)
    twilio_account_sid: Optional[str] = None
    twilio_auth_token: Optional[str] = None

    class Config:
        env_file = ".env"
        case_sensitive = False
        extra = "ignore"  # Ignore extra fields in .env file

    def validate_production_settings(self):
        """Validate critical settings for production environment"""
        if self.environment == "production":
            errors = []

            if self.jwt_secret == "default_secret_change_in_production":
                errors.append("JWT_SECRET must be changed for production")

            if not self.encryption_key:
                errors.append("ENCRYPTION_KEY is required for production")

            if not self.openai_api_key:
                logger.warning("OPENAI_API_KEY not set - inbound calls will not work")

            if not self.api_base_url:
                errors.append("API_BASE_URL is required for production (webhook URLs)")

            if self.frontend_url == "http://localhost:3000":
                logger.warning("FRONTEND_URL still set to localhost - update for production")

            if errors:
                raise ValueError(f"Production configuration errors: {', '.join(errors)}")

        logger.info(f"Running in {self.environment} mode")

settings = Settings()

# Validate settings on startup
try:
    settings.validate_production_settings()
except ValueError as e:
    logger.error(f"Configuration validation failed: {e}")
    if settings.environment == "production":
        raise
