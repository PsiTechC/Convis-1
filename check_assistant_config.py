#!/usr/bin/env python3
"""
Check assistant configuration in MongoDB
"""
import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
from bson import ObjectId

# MongoDB connection
MONGODB_URI = "mongodb+srv://psitech:Psitech123@pms.ijqbdmu.mongodb.net/?retryWrites=true&w=majority"
DATABASE_NAME = "convis_python"


async def check_assistants():
    """Check all assistants and their provider configuration"""
    client = AsyncIOMotorClient(MONGODB_URI)
    db = client[DATABASE_NAME]
    assistants_collection = db['assistants']

    print("\n" + "="*100)
    print(" ASSISTANT PROVIDER CONFIGURATIONS")
    print("="*100 + "\n")

    async for assistant in assistants_collection.find().sort("_id", -1).limit(10):
        print(f"Assistant: {assistant.get('name', 'Unnamed')}")
        print(f"  ID: {assistant['_id']}")
        print(f"  Created: {assistant.get('created_at', 'Unknown')}")
        print(f"  ASR Provider: {assistant.get('asr_provider', 'NOT SET')}")
        print(f"  ASR Model: {assistant.get('asr_model', 'NOT SET')}")
        print(f"  ASR Language: {assistant.get('asr_language', 'NOT SET')}")
        print(f"  TTS Provider: {assistant.get('tts_provider', 'NOT SET')}")
        print(f"  TTS Model: {assistant.get('tts_model', 'NOT SET')}")
        print(f"  TTS Voice: {assistant.get('tts_voice', 'NOT SET')}")
        print(f"  LLM Provider: {assistant.get('llm_provider', 'NOT SET')}")
        print(f"  LLM Model: {assistant.get('llm_model', 'NOT SET')}")
        print(f"  Voice: {assistant.get('voice', 'NOT SET')}")
        print(f"  API Key ID: {assistant.get('api_key_id', 'NOT SET')}")
        print("-" * 100)

    await client.close()


if __name__ == "__main__":
    asyncio.run(check_assistants())
