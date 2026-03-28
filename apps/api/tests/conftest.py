"""
pytest configuration and shared fixtures
"""

import pytest
from fastapi.testclient import TestClient
import os

@pytest.fixture(scope="session", autouse=True)
def set_test_env():
    """Set environment variables for tests"""
    os.environ["DEV_MODE"] = "true"
    os.environ["SUPABASE_URL"] = "https://test.supabase.co"
    os.environ["SUPABASE_ANON_KEY"] = "test-key"
    os.environ["SUPABASE_SERVICE_KEY"] = "test-service-key"
    os.environ["JWT_SECRET"] = "test-secret"


@pytest.fixture
def test_client():
    """Create test client for API"""
    # Import here to ensure env vars are set first
    from main import app
    return TestClient(app)
