import os
import logging
from pathlib import Path
from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Load .env file from the project root
env_path = Path(__file__).resolve().parent.parent / ".env"
load_dotenv(dotenv_path=env_path)

from app.routes.register import registration_router, verify_email_router, check_user_router
from app.routes.forgot_password import send_otp_router, verify_otp_router, reset_password_router
from app.routes.access import login_router, logout_router
from app.routes.user import update_profile_router
from app.routes.api_keys import router as api_keys_router
from app.routes.ai_assistant import assistants_router
from app.routes.ai_assistant import knowledge_base as knowledge_base_router
from app.routes.ai_assistant import database as database_router
from app.routes.inbound_calls import inbound_calls_router
from app.routes.outbound_calls import outbound_calls_router
from app.routes.phone_numbers import phone_numbers_router, twilio_management_router, subaccounts_router, messaging_services_router
from app.routes.calendar import router as calendar_router
from app.routes.campaigns import router as campaigns_router
from app.routes.twilio_webhooks import router as twilio_webhooks_router
from app.routes.campaign_twilio_callbacks import router as campaign_twilio_router
from app.routes.dashboard import router as dashboard_router
from app.routes.frejun import router as frejun_router
from app.routes.whatsapp import credentials_router, messages_router, webhooks_router
from app.routes.transcription import transcription_router
from app.config.database import Database
from app.config.settings import settings
from app.services.campaign_scheduler import campaign_scheduler

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# Enable DEBUG logging for campaign_scheduler to troubleshoot dispatcher issues
logging.getLogger('app.services.campaign_scheduler').setLevel(logging.DEBUG)

# Create FastAPI app
app = FastAPI(
    title="Convis Labs Registration API",
    description="Python backend for user registration with OTP verification",
    version="1.0.0"
)

# Configure CORS
# Build list of allowed origins from environment
allowed_origins = []

# Add frontend URL from settings
if settings.frontend_url:
    allowed_origins.append(settings.frontend_url)

# Add any additional origins from CORS_ORIGINS env var (comma-separated)
cors_origins_env = os.getenv("CORS_ORIGINS", "")
if cors_origins_env:
    additional_origins = [origin.strip() for origin in cors_origins_env.split(",") if origin.strip()]
    allowed_origins.extend(additional_origins)

# Fallback to production URLs if no origins configured
if not allowed_origins:
    allowed_origins = ["https://webapp.convis.ai", "https://api.convis.ai"]

logging.info(f"CORS allowed origins: {allowed_origins}")

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
)

# Include routers
app.include_router(registration_router, prefix="/api/register", tags=["Registration"])
app.include_router(verify_email_router, prefix="/api/register", tags=["Registration"])
app.include_router(check_user_router, prefix="/api/register", tags=["Registration"])

# Forgot password routers
app.include_router(send_otp_router, prefix="/api/forgot_password", tags=["Forgot Password"])
app.include_router(verify_otp_router, prefix="/api/forgot_password", tags=["Forgot Password"])
app.include_router(reset_password_router, prefix="/api/forgot_password", tags=["Forgot Password"])

# Access routers
app.include_router(login_router, prefix="/api/access", tags=["Access"])
app.include_router(logout_router, prefix="/api/access", tags=["Access"])

# User routers
app.include_router(update_profile_router, prefix="/api/users", tags=["Users"])
app.include_router(api_keys_router, prefix="/api/ai-keys", tags=["AI API Keys"])
app.include_router(campaigns_router, prefix="/api/campaigns", tags=["Campaigns"])
app.include_router(dashboard_router, prefix="/api/dashboard", tags=["Dashboard"])

# AI Assistant routers
app.include_router(assistants_router, prefix="/api/ai-assistants", tags=["AI Assistants"])
app.include_router(knowledge_base_router.router, prefix="/api/ai-assistants/knowledge-base", tags=["Knowledge Base"])
app.include_router(database_router.router, prefix="/api/ai-assistants/database", tags=["Database Integration"])

# Inbound Calls routers
app.include_router(inbound_calls_router, prefix="/api/inbound-calls", tags=["Inbound Calls"])

# Outbound Calls routers
app.include_router(outbound_calls_router, prefix="/api/outbound-calls", tags=["Outbound Calls"])

# Phone Numbers routers
app.include_router(phone_numbers_router, prefix="/api/phone-numbers", tags=["Phone Numbers"])
app.include_router(twilio_management_router, prefix="/api/phone-numbers/twilio", tags=["Twilio Management"])
app.include_router(subaccounts_router, prefix="/api/phone-numbers/subaccounts", tags=["Subaccounts"])
app.include_router(messaging_services_router, prefix="/api/phone-numbers/messaging-services", tags=["Messaging Services"])
app.include_router(calendar_router, prefix="/api/calendar", tags=["Calendar"])

# Twilio Webhooks (dynamic routing)
app.include_router(twilio_webhooks_router, prefix="/api/twilio-webhooks", tags=["Twilio Webhooks"])
app.include_router(campaign_twilio_router, tags=["Campaign Webhooks"])

# FreJun Integration
app.include_router(frejun_router, prefix="/api/frejun", tags=["FreJun Calls"])

# WhatsApp Integration
app.include_router(credentials_router, prefix="/api/whatsapp", tags=["WhatsApp"])
app.include_router(messages_router, prefix="/api/whatsapp", tags=["WhatsApp"])
app.include_router(webhooks_router, prefix="/api/whatsapp", tags=["WhatsApp Webhooks"])

# Transcription Management
app.include_router(transcription_router, prefix="/api/transcription", tags=["Transcription"])


async def transcribe_existing_recordings():
    """Background task to transcribe all existing recordings on startup"""
    import asyncio
    await asyncio.sleep(10)  # Wait 10 seconds for server to fully start

    try:
        from app.services.post_call_processor import PostCallProcessor

        db = Database.get_db()
        call_logs = db['call_logs']

        # Find calls with recordings but no transcripts (or failed transcriptions)
        query = {
            'recording_url': {'$ne': None, '$exists': True},
            '$or': [
                {'transcript': {'$exists': False}},
                {'transcript': None},
                {'transcript': ''},
                {'transcript': '[Transcription unavailable]'}
            ]
        }

        calls_to_transcribe = list(call_logs.find(query).limit(50))  # Limit to 50 at a time

        if len(calls_to_transcribe) > 0:
            logging.info(f"🎙️  Found {len(calls_to_transcribe)} calls to transcribe - starting background transcription...")

            processor = PostCallProcessor()
            for call in calls_to_transcribe:
                try:
                    await processor.transcribe_and_update_call(
                        call['call_sid'],
                        call['recording_url']
                    )
                    logging.info(f"✓ Transcribed {call['call_sid']}")
                    await asyncio.sleep(2)  # Rate limiting
                except Exception as e:
                    logging.error(f"Failed to transcribe {call.get('call_sid')}: {e}")

            logging.info(f"✓ Background transcription complete!")
    except Exception as e:
        logging.error(f"Error in background transcription: {e}")


@app.on_event("startup")
async def startup_event():
    """Connect to database on startup"""
    Database.connect()
    logging.info("Connected to MongoDB")
    await campaign_scheduler.start()

    # Start background transcription task
    import asyncio
    asyncio.create_task(transcribe_existing_recordings())

@app.on_event("shutdown")
async def shutdown_event():
    """Close database connection on shutdown"""
    await campaign_scheduler.shutdown()
    Database.close()
    logging.info("Closed MongoDB connection")

@app.get("/health")
async def health_check():
    """
    Health check endpoint for monitoring and load balancers
    """
    try:
        # Check database connection
        db = Database.get_db()
        db.command('ping')
        db_status = "healthy"
    except Exception as e:
        logging.error(f"Database health check failed: {e}")
        db_status = "unhealthy"

    return {
        "status": "running" if db_status == "healthy" else "degraded",
        "database": db_status,
        "version": "1.0.0"
    }

@app.get("/")
async def root():
    """Health check endpoint"""
    return {
        "status": "running",
        "message": "Convis Labs Registration API",
        "version": "1.0.0"
    }

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy"}
