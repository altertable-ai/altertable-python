import os
import pytest
from unittest.mock import Mock
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
        distinct_id="user_123",
        options={"traits": {"email": "test@example.com"}}
    )
    assert response.get("ok") is True

def test_alias(client):
    response = client.alias(
        distinct_id="old_id",
        new_user_id="new_id"
    )
    assert response.get("ok") is True

def test_track_batch_passes_all_payloads_through_without_chunking():
    client = Altertable("test_pk_abc123", server_url=MOCK_BASE_URL)
    response = Mock(ok=True)
    response.json.return_value = {"ok": True}
    client.session.post = Mock(return_value=response)
    payloads = [
        {"event": f"event-{index}", "distinct_id": f"user-{index}", "environment": "test"}
        for index in range(101)
    ]

    assert client.track_batch(payloads) == {"ok": True}
    client.session.post.assert_called_once()
    assert client.session.post.call_args.kwargs["json"] == payloads

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
