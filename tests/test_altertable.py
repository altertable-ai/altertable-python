import copy
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

def test_environment_is_ignored_and_never_sent_from_product_requests():
    client = Altertable("test_pk_abc123", MOCK_BASE_URL, "staging")
    response = Mock(ok=True)
    response.json.return_value = {"ok": True}
    client.session.post = Mock(return_value=response)

    track_options = {
        "environment": "event-env",
        "properties": {"environment": "business-value"},
    }
    identify_options = {
        "environment": "identify-env",
        "traits": {"environment": "trait-business-value"},
    }
    original_track_options = copy.deepcopy(track_options)
    original_identify_options = copy.deepcopy(identify_options)
    client.track("tracked", "user-1", track_options)
    client.identify("user-1", identify_options)
    client.alias("user-1", "user-2", {"environment": "alias-env"})

    payloads = [call.kwargs["json"] for call in client.session.post.call_args_list]
    assert all("environment" not in payload for payload in payloads)
    assert payloads[0]["properties"]["environment"] == "business-value"
    assert payloads[1]["traits"]["environment"] == "trait-business-value"
    assert track_options == original_track_options
    assert identify_options == original_identify_options


def test_raw_batches_strip_environment_without_mutating_caller_payloads():
    client = Altertable("test_pk_abc123", server_url=MOCK_BASE_URL)
    response = Mock(ok=True)
    response.json.return_value = {"ok": True}
    client.session.post = Mock(return_value=response)
    payloads = [
        {"event": f"event-{index}", "distinct_id": f"user-{index}", "environment": "test"}
        for index in range(101)
    ]

    original = [payload.copy() for payload in payloads]
    assert client.track(payloads) == {"ok": True}
    client.session.post.assert_called_once()
    assert client.session.post.call_args.kwargs["json"] == [
        {"event": f"event-{index}", "distinct_id": f"user-{index}"}
        for index in range(101)
    ]
    assert payloads == original

@pytest.mark.parametrize("method_name, endpoint", [("identify", "/identify"), ("alias", "/alias")])
def test_identity_batches_strip_environment_without_mutating_caller(method_name, endpoint):
    client = Altertable("test_pk_abc123", server_url=MOCK_BASE_URL)
    response = Mock(ok=True)
    response.json.return_value = {"ok": True}
    client.session.post = Mock(return_value=response)
    payloads = [{"distinct_id": "user-1", "environment": "test"}]

    assert getattr(client, method_name)(payloads) == {"ok": True}
    assert client.session.post.call_args.args[0] == f"{MOCK_BASE_URL}{endpoint}"
    assert client.session.post.call_args.kwargs["json"] == [{"distinct_id": "user-1"}]
    assert payloads == [{"distinct_id": "user-1", "environment": "test"}]

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
