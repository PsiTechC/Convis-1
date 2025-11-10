"""
WhatsApp Webhooks Routes
Handles incoming webhook events from Meta WhatsApp Business API
"""

from fastapi import APIRouter, HTTPException, Request, Query, status
from typing import Dict, Any
from datetime import datetime
from bson import ObjectId
import logging

from app.config.database import Database
from app.config.settings import settings

router = APIRouter()
logger = logging.getLogger(__name__)


@router.get("/webhook")
async def verify_webhook(
    request: Request,
    mode: str = Query(None, alias="hub.mode"),
    token: str = Query(None, alias="hub.verify_token"),
    challenge: str = Query(None, alias="hub.challenge")
):
    """
    Webhook verification endpoint for Meta WhatsApp
    Meta will call this endpoint to verify the webhook URL
    """
    logger.info(f"Webhook verification request: mode={mode}, token={token}")

    # Verify token matches what you configured in Meta App Dashboard
    verify_token = getattr(settings, 'whatsapp_webhook_verify_token', 'your_verify_token_here')

    if mode == "subscribe" and token == verify_token:
        logger.info("Webhook verified successfully")
        return int(challenge)
    else:
        logger.warning(f"Webhook verification failed: mode={mode}, token={token}")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Verification failed"
        )


@router.post("/webhook")
async def handle_webhook(request: Request):
    """
    Handle incoming webhook events from WhatsApp

    Events include:
    - Message status updates (sent, delivered, read)
    - Incoming messages
    - Template status updates
    """
    try:
        body = await request.json()
        logger.info(f"Webhook received: {body}")

        # Process webhook data
        if body.get("object") == "whatsapp_business_account":
            entries = body.get("entry", [])

            for entry in entries:
                changes = entry.get("changes", [])

                for change in changes:
                    value = change.get("value", {})

                    # Handle message status updates
                    if "statuses" in value:
                        await handle_status_updates(value["statuses"])

                    # Handle incoming messages
                    if "messages" in value:
                        await handle_incoming_messages(value["messages"], value.get("metadata", {}))

                    # Handle message errors
                    if "errors" in value:
                        await handle_message_errors(value["errors"])

        return {"status": "success"}

    except Exception as e:
        logger.error(f"Error processing webhook: {str(e)}")
        # Return 200 to prevent Meta from retrying
        return {"status": "error", "message": str(e)}


async def handle_status_updates(statuses: list):
    """
    Handle message status updates (sent, delivered, read, failed)
    """
    db = Database.get_db()
    messages_collection = db["whatsapp_messages"]

    for status_update in statuses:
        message_id = status_update.get("id")
        status_value = status_update.get("status")
        timestamp = status_update.get("timestamp")

        if not message_id:
            continue

        logger.info(f"Status update for message {message_id}: {status_value}")

        update_data = {"status": status_value}

        # Update timestamp based on status
        if timestamp:
            ts_datetime = datetime.fromtimestamp(int(timestamp))

            if status_value == "delivered":
                update_data["delivered_at"] = ts_datetime
            elif status_value == "read":
                update_data["read_at"] = ts_datetime

        # Handle errors
        if "errors" in status_update:
            errors = status_update["errors"]
            if errors:
                update_data["error"] = errors[0].get("message", "Unknown error")
                update_data["status"] = "failed"

        # Update message in database
        result = messages_collection.update_one(
            {"message_id": message_id},
            {"$set": update_data}
        )

        if result.modified_count > 0:
            logger.info(f"Updated message {message_id} with status {status_value}")
        else:
            logger.warning(f"Message {message_id} not found in database")


async def handle_incoming_messages(messages: list, metadata: dict):
    """
    Handle incoming messages from customers
    """
    db = Database.get_db()
    incoming_messages_collection = db["whatsapp_incoming_messages"]

    phone_number_id = metadata.get("phone_number_id")

    for message in messages:
        message_id = message.get("id")
        from_number = message.get("from")
        timestamp = message.get("timestamp")
        message_type = message.get("type")

        logger.info(f"Incoming message {message_id} from {from_number}, type: {message_type}")

        # Extract message content based on type
        content = {}
        if message_type == "text":
            content = {"text": message.get("text", {}).get("body")}
        elif message_type == "image":
            content = message.get("image", {})
        elif message_type == "video":
            content = message.get("video", {})
        elif message_type == "document":
            content = message.get("document", {})
        elif message_type == "audio":
            content = message.get("audio", {})
        elif message_type == "location":
            content = message.get("location", {})
        elif message_type == "contacts":
            content = message.get("contacts", {})

        # Find the credential/user associated with this phone number
        credentials_collection = db["whatsapp_credentials"]

        # This is a simplified approach - you might need to decrypt and compare
        # For now, we'll store the message with phone_number_id reference
        credential = credentials_collection.find_one({"phone_number_id": phone_number_id})

        doc = {
            "message_id": message_id,
            "phone_number_id": phone_number_id,
            "from": from_number,
            "message_type": message_type,
            "content": content,
            "timestamp": datetime.fromtimestamp(int(timestamp)) if timestamp else datetime.utcnow(),
            "received_at": datetime.utcnow(),
            "processed": False
        }

        if credential:
            doc["user_id"] = credential["user_id"]
            doc["credential_id"] = credential["_id"]

        # Insert incoming message
        incoming_messages_collection.insert_one(doc)
        logger.info(f"Stored incoming message {message_id}")

        # TODO: Add logic to route message to appropriate assistant/handler
        # This could trigger an AI assistant to respond, create a ticket, etc.


async def handle_message_errors(errors: list):
    """
    Handle message errors from WhatsApp
    """
    logger.error(f"WhatsApp errors received: {errors}")

    db = Database.get_db()
    messages_collection = db["whatsapp_messages"]

    for error in errors:
        error_code = error.get("code")
        error_message = error.get("message")
        error_data = error.get("error_data", {})

        logger.error(f"WhatsApp error {error_code}: {error_message}")

        # Update message status if we have message reference
        # This depends on the error structure from Meta


@router.get("/incoming-messages")
async def get_incoming_messages(
    limit: int = 50,
    offset: int = 0,
    unprocessed_only: bool = False
):
    """
    Get incoming messages (requires authentication in production)
    """
    db = Database.get_db()
    incoming_messages_collection = db["whatsapp_incoming_messages"]

    query = {}
    if unprocessed_only:
        query["processed"] = False

    messages = incoming_messages_collection.find(query).sort("received_at", -1).skip(offset).limit(limit)

    result = []
    for msg in messages:
        result.append({
            "id": str(msg["_id"]),
            "message_id": msg.get("message_id"),
            "from": msg.get("from"),
            "message_type": msg.get("message_type"),
            "content": msg.get("content"),
            "timestamp": msg.get("timestamp").isoformat() if msg.get("timestamp") else None,
            "processed": msg.get("processed", False)
        })

    return result


@router.post("/incoming-messages/{message_id}/mark-processed")
async def mark_message_processed(message_id: str):
    """
    Mark an incoming message as processed
    """
    db = Database.get_db()
    incoming_messages_collection = db["whatsapp_incoming_messages"]

    try:
        result = incoming_messages_collection.update_one(
            {"_id": ObjectId(message_id)},
            {"$set": {"processed": True, "processed_at": datetime.utcnow()}}
        )
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid message ID format"
        )

    if result.modified_count == 0:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Message not found"
        )

    return {"status": "success"}
