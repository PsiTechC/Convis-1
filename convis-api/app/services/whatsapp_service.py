"""
WhatsApp Service
Handles integration with Railway WhatsApp API Backend
"""

import requests
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime

logger = logging.getLogger(__name__)


class WhatsAppService:
    """Service for interacting with Railway WhatsApp API Backend"""

    def __init__(
        self,
        api_key: str,
        bearer_token: str,
        base_url: str = "https://whatsapp-api-backend-production.up.railway.app"
    ):
        """
        Initialize WhatsApp service for Railway API

        Args:
            api_key: x-api-key header value
            bearer_token: Authorization Bearer token
            base_url: Railway API base URL
        """
        self.api_key = api_key
        self.bearer_token = bearer_token
        self.base_url = base_url
        self.headers = {
            "Content-Type": "application/json",
            "x-api-key": api_key,
            "Authorization": f"Bearer {bearer_token}"
        }

    async def send_text_message(self, to: str, message: str) -> Dict[str, Any]:
        """
        Send a text message via WhatsApp
        Note: Railway API primarily uses templates, but we'll try to send as template

        Args:
            to: Recipient phone number with country code (e.g., +1234567890)
            message: Text message content

        Returns:
            API response with message ID
        """
        logger.warning("Railway WhatsApp API primarily supports templates. Consider using send_template_message instead.")

        # For text messages, we might need a simple text template
        # This is a fallback - check if your Railway API supports direct text
        url = f"{self.base_url}/api/send-message"

        payload = {
            "to_number": to,
            "whatsapp_request_type": "TEXT",  # Try TEXT type
            "message": message
        }

        try:
            response = requests.post(url, headers=self.headers, json=payload, timeout=30)
            response.raise_for_status()
            result = response.json()

            logger.info(f"Text message sent to {to}: {result}")

            # Extract message ID from Railway API response
            message_id = result.get("metaResponse", {}).get("messages", [{}])[0].get("id")

            return {
                "success": True,
                "message_id": message_id,
                "response": result
            }
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to send text message to {to}: {str(e)}")
            error_response = {}
            if hasattr(e, 'response') and e.response is not None:
                try:
                    error_response = e.response.json()
                except:
                    error_response = {"error": e.response.text}

            return {
                "success": False,
                "error": str(e),
                "response": error_response
            }

    async def send_template_message(
        self,
        to: str,
        template_name: str,
        parameters: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Send a template message via WhatsApp (Railway API)

        Args:
            to: Recipient phone number (e.g., +919131296862)
            template_name: Name of the approved template (e.g., "atithi_host_1")
            parameters: List of parameter values for template variables

        Returns:
            API response with message ID
        """
        url = f"{self.base_url}/api/send-message"

        payload = {
            "to_number": to,
            "template_name": template_name,
            "whatsapp_request_type": "TEMPLATE",
            "parameters": parameters or []
        }

        try:
            response = requests.post(url, headers=self.headers, json=payload, timeout=30)
            response.raise_for_status()
            result = response.json()

            logger.info(f"Template message '{template_name}' sent to {to}: {result}")

            # Extract message ID from Railway API response
            message_id = result.get("metaResponse", {}).get("messages", [{}])[0].get("id")

            return {
                "success": True,
                "message_id": message_id,
                "response": result
            }
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to send template message to {to}: {str(e)}")
            error_response = {}
            if hasattr(e, 'response') and e.response is not None:
                try:
                    error_response = e.response.json()
                except:
                    error_response = {"error": e.response.text}

            return {
                "success": False,
                "error": str(e),
                "response": error_response
            }

    async def sync_templates(self) -> Dict[str, Any]:
        """
        Sync/fetch available WhatsApp templates from Railway API

        Returns:
            List of available templates
        """
        url = f"{self.base_url}/api/sync-templates"

        try:
            response = requests.get(url, headers=self.headers, timeout=30)
            response.raise_for_status()
            result = response.json()

            logger.info(f"Templates synced: {result}")
            return {
                "success": True,
                "templates": result.get("templates", []),
                "response": result
            }
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to sync templates: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "templates": []
            }

    async def get_message_templates(self) -> Dict[str, Any]:
        """
        Get all message templates (alias for sync_templates)

        Returns:
            List of message templates
        """
        return await self.sync_templates()

    async def test_connection(self) -> Dict[str, Any]:
        """
        Test the Railway WhatsApp API connection by syncing templates

        Returns:
            Connection test results
        """
        result = await self.sync_templates()

        if result.get("success"):
            return {
                "success": True,
                "message": "Connection successful! Railway WhatsApp API is accessible.",
                "templates_count": len(result.get("templates", []))
            }
        else:
            return {
                "success": False,
                "message": "Connection failed",
                "error": result.get("error")
            }

    async def get_message_status(self, message_id: str) -> Dict[str, Any]:
        """
        Get status of a sent message
        Note: This may not be available in Railway API - check documentation

        Args:
            message_id: WhatsApp message ID

        Returns:
            Message status information
        """
        # Railway API may not have a direct status endpoint
        # You might need to rely on webhooks for status updates
        logger.warning("Message status endpoint not implemented for Railway API. Use webhooks for status updates.")
        return {
            "success": False,
            "error": "Status endpoint not available. Use webhooks for message status updates."
        }

    async def send_bulk_messages(
        self,
        recipients: List[str],
        template_name: str,
        parameters_per_recipient: Optional[Dict[str, List[str]]] = None
    ) -> Dict[str, Any]:
        """
        Send template messages to multiple recipients

        Args:
            recipients: List of phone numbers
            template_name: Template name to use
            parameters_per_recipient: Dict mapping phone number to parameters list

        Returns:
            Bulk send results
        """
        results = []
        success_count = 0
        failed_count = 0

        for recipient in recipients:
            params = parameters_per_recipient.get(recipient, []) if parameters_per_recipient else []

            result = await self.send_template_message(
                to=recipient,
                template_name=template_name,
                parameters=params
            )

            results.append({
                "to": recipient,
                "success": result.get("success"),
                "message_id": result.get("message_id"),
                "error": result.get("error")
            })

            if result.get("success"):
                success_count += 1
            else:
                failed_count += 1

        return {
            "success": True,
            "total": len(recipients),
            "successful": success_count,
            "failed": failed_count,
            "results": results
        }

    # Webhook-related methods can remain for handling incoming status updates
    async def verify_webhook_signature(self, payload: str, signature: str, app_secret: str) -> bool:
        """
        Verify webhook signature from WhatsApp

        Args:
            payload: Raw request body
            signature: X-Hub-Signature-256 header value
            app_secret: Your app secret

        Returns:
            True if signature is valid
        """
        import hmac
        import hashlib

        expected_signature = hmac.new(
            app_secret.encode('utf-8'),
            payload.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()

        return hmac.compare_digest(
            f"sha256={expected_signature}",
            signature
        )
