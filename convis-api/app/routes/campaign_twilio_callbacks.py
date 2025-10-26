from fastapi import APIRouter, Request, Form, HTTPException
from typing import Optional
import logging

from app.services.call_status_processor import process_call_status

logger = logging.getLogger(__name__)

router = APIRouter()


@router.api_route("/webhooks/twilio/calls", methods=["GET", "POST"])
async def universal_twilio_call_webhook(
    request: Request,
    CallSid: Optional[str] = Form(None),
    CallStatus: Optional[str] = Form(None),
    CallDuration: Optional[str] = Form(None),
    leadId: Optional[str] = Form(None),
    campaignId: Optional[str] = Form(None)
):
    """
    Public-facing webhook endpoint that Twilio can call directly.

    This mirrors /api/twilio-webhooks/call-status but exposes a simplified path
    that matches the product specification (`/webhooks/twilio/calls`).
    """
    try:
        if not CallSid:
            CallSid = request.query_params.get("CallSid")
            CallStatus = request.query_params.get("CallStatus", CallStatus)
            CallDuration = request.query_params.get("CallDuration", CallDuration)
            leadId = request.query_params.get("leadId", leadId)
            campaignId = request.query_params.get("campaignId", campaignId)

        if not CallSid or not CallStatus:
            raise HTTPException(status_code=400, detail="CallSid and CallStatus are required")

        logger.info(
            "Webhook /webhooks/twilio/calls received status=%s sid=%s lead=%s campaign=%s",
            CallStatus,
            CallSid,
            leadId,
            campaignId
        )

        process_call_status(CallSid, CallStatus, CallDuration, leadId, campaignId)
        return {"message": "Status processed"}

    except HTTPException:
        raise
    except Exception as error:
        logger.error("Error handling /webhooks/twilio/calls: %s", error)
        raise HTTPException(status_code=500, detail="Failed to process call status")
