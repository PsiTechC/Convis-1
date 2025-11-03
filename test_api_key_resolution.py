#!/usr/bin/env python3
"""Test API key resolution for the Appointment Scheduler assistant"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'convis-api'))

from app.config.database import Database
from app.utils.assistant_keys import resolve_assistant_api_key
from bson import ObjectId
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_api_key_resolution():
    """Test if the API key for Appointment Scheduler can be resolved"""
    try:
        # Connect to database
        db = Database.get_db()

        # Get the assistant
        assistant_id = ObjectId("69089beae08051c5c8b0170e")
        assistant = db.assistants.find_one({"_id": assistant_id})

        if not assistant:
            print("❌ Assistant not found!")
            return False

        print(f"✓ Found assistant: {assistant['name']}")
        print(f"  - API Key ID: {assistant.get('api_key_id')}")
        print(f"  - Legacy Key: {assistant.get('openai_api_key', 'None')}")

        # Try to resolve the API key
        try:
            api_key, provider = resolve_assistant_api_key(db, assistant, required_provider="openai")
            print(f"✓ API key resolved successfully!")
            print(f"  - Provider: {provider}")
            print(f"  - Key starts with: {api_key[:10]}...")
            print(f"  - Key length: {len(api_key)}")

            # Verify it's a valid OpenAI key format
            if api_key.startswith('sk-'):
                print("✓ Valid OpenAI API key format (sk-...)")
                return True
            else:
                print(f"⚠️  Warning: Key doesn't start with 'sk-': {api_key[:20]}...")
                return False

        except Exception as e:
            print(f"❌ Failed to resolve API key: {e}")
            return False

    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_api_key_resolution()
    sys.exit(0 if success else 1)
