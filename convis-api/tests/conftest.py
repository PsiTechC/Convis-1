"""
Pytest configuration and fixtures for integration tests
"""
import pytest
from fastapi.testclient import TestClient
from unittest.mock import MagicMock, AsyncMock
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

@pytest.fixture
def client():
    """
    Create a FastAPI TestClient for integration tests
    Note: These tests require MongoDB to be running
    """
    from app.main import app

    # Create test client
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def mock_mongo_db():
    """
    Mock MongoDB for tests that don't need the full API
    """
    mock_db = MagicMock()
    mock_collection = MagicMock()

    # In-memory storage
    mock_storage = {}

    async def mock_insert_one(data):
        from bson import ObjectId
        doc_id = str(ObjectId())
        mock_storage[doc_id] = {**data, "_id": doc_id}
        result = MagicMock()
        result.inserted_id = doc_id
        return result

    async def mock_find_one(query):
        doc_id = query.get("_id")
        return mock_storage.get(doc_id)

    mock_collection.insert_one = mock_insert_one
    mock_collection.find_one = mock_find_one
    mock_db.__getitem__ = lambda self, name: mock_collection

    return mock_db


@pytest.fixture
def mock_twilio_ws():
    """
    Mock Twilio WebSocket for tests
    """
    mock_ws = AsyncMock()
    mock_ws.send = AsyncMock()
    mock_ws.recv = AsyncMock()
    return mock_ws


# Register custom marks
def pytest_configure(config):
    config.addinivalue_line(
        "markers", "integration: mark test as integration test"
    )
    config.addinivalue_line(
        "markers", "unit: mark test as unit test"
    )
