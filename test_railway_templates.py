#!/usr/bin/env python3
"""
Test script to check Railway WhatsApp API template response format
"""
import requests
import json

# Get credentials from your database
# For now, you'll need to provide these manually
API_KEY = input("Enter your x-api-key: ")
BEARER_TOKEN = input("Enter your Bearer token: ")
API_URL = "https://whatsapp-api-backend-production.up.railway.app"

headers = {
    "Content-Type": "application/json",
    "x-api-key": API_KEY,
    "Authorization": f"Bearer {BEARER_TOKEN}"
}

print(f"\n🔍 Testing Railway API: {API_URL}/api/sync-templates")
print("=" * 60)

try:
    response = requests.get(f"{API_URL}/api/sync-templates", headers=headers, timeout=30)

    print(f"\n📊 Response Status: {response.status_code}")
    print(f"📋 Response Headers: {dict(response.headers)}")

    if response.status_code == 200:
        result = response.json()
        print(f"\n✅ SUCCESS!")
        print(f"\n📦 Response Structure:")
        print(json.dumps(result, indent=2))

        # Try to identify template structure
        if isinstance(result, dict):
            print(f"\n🔑 Top-level keys: {list(result.keys())}")

            for key in ['templates', 'data', 'message_templates']:
                if key in result:
                    templates = result[key]
                    print(f"\n📝 Found templates in '{key}': {len(templates) if isinstance(templates, list) else 'not a list'}")
                    if isinstance(templates, list) and len(templates) > 0:
                        print(f"\n🎯 First template structure:")
                        print(json.dumps(templates[0], indent=2))
                    break
        elif isinstance(result, list):
            print(f"\n📝 Response is a list with {len(result)} items")
            if len(result) > 0:
                print(f"\n🎯 First item structure:")
                print(json.dumps(result[0], indent=2))
    else:
        print(f"\n❌ ERROR!")
        print(f"Response: {response.text}")

except Exception as e:
    print(f"\n❌ Exception occurred: {str(e)}")
    print(f"Error type: {type(e).__name__}")

print("\n" + "=" * 60)
