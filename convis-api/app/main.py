from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routes.register import registration_router, verify_email_router, check_user_router
from app.routes.forgot_password import send_otp_router, verify_otp_router, reset_password_router
from app.routes.access import login_router, logout_router
from app.routes.user import update_profile_router
from app.routes.api_keys import router as api_keys_router
from app.routes.ai_assistant import assistants_router
from app.routes.ai_assistant import knowledge_base as knowledge_base_router
from app.routes.inbound_calls import inbound_calls_router
from app.routes.outbound_calls import outbound_calls_router
from app.routes.phone_numbers import phone_numbers_router, twilio_management_router, subaccounts_router, messaging_services_router
from app.routes.twilio_webhooks import router as twilio_webhooks_router
from app.routes.dashboard import router as dashboard_router
from app.config.database import Database
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# Create FastAPI app
app = FastAPI(
    title="Convis Labs Registration API",
    description="Python backend for user registration with OTP verification",
    version="1.0.0"
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:3001", "http://localhost:3002"],  # Add your frontend URLs
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
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
app.include_router(dashboard_router, prefix="/api/dashboard", tags=["Dashboard"])

# AI Assistant routers
app.include_router(assistants_router, prefix="/api/ai-assistants", tags=["AI Assistants"])
app.include_router(knowledge_base_router.router, prefix="/api/ai-assistants/knowledge-base", tags=["Knowledge Base"])

# Inbound Calls routers
app.include_router(inbound_calls_router, prefix="/api/inbound-calls", tags=["Inbound Calls"])

# Outbound Calls routers
app.include_router(outbound_calls_router, prefix="/api/outbound-calls", tags=["Outbound Calls"])

# Phone Numbers routers
app.include_router(phone_numbers_router, prefix="/api/phone-numbers", tags=["Phone Numbers"])
app.include_router(twilio_management_router, prefix="/api/phone-numbers/twilio", tags=["Twilio Management"])
app.include_router(subaccounts_router, prefix="/api/phone-numbers/subaccounts", tags=["Subaccounts"])
app.include_router(messaging_services_router, prefix="/api/phone-numbers/messaging-services", tags=["Messaging Services"])

# Twilio Webhooks (dynamic routing)
app.include_router(twilio_webhooks_router, prefix="/api/twilio-webhooks", tags=["Twilio Webhooks"])

@app.on_event("startup")
async def startup_event():
    """Connect to database on startup"""    
    Database.connect()
    logging.info("Connected to MongoDB")

@app.on_event("shutdown")
async def shutdown_event():
    """Close database connection on shutdown"""
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
