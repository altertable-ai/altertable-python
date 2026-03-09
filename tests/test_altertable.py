import os
import pytest
from altertable.client import Altertable, ApiError

MOCK_PORT = os.environ.get("ALTERTABLE_MOCK_PORT", "15001")
MOCK_BASE_URL = f"http://localhost:{MOCK_PORT}"

@pytest.fixture
def client():
    return Altertable("test_pk_abc123", server_url=MOCK_BASE_URL)

def test_track(client):
    response = client.track(
        event="test_event",
        distinct_id="user_123",
        options={"properties": {"key": "value"}}
    )
    assert response.get("ok") is True

def test_identify(client):
    response = client.identify(
        user_id="user_123",
        options={"traits": {"email": "test@example.com"}}
    )
    assert response.get("ok") is True

def test_alias(client):
    response = client.alias(
        distinct_id="old_id",
        new_user_id="new_id"
    )
    assert response.get("ok") is True

def test_authentication_error():
    client = Altertable("wrong_api_key", server_url=MOCK_BASE_URL)
    with pytest.raises(ApiError):
        client.track(
            event="test_event",
            distinct_id="user_123",
            options={"properties": {"key": "value"}}
        )

def test_has_version_number():
    import altertable
    assert altertable.__version__ is not None
