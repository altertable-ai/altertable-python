import copy
import warnings
from unittest.mock import Mock

import pytest

from altertable import Altertable

AUDIENCE_FIELDS = {"mode", "event", "timestamp", "properties"}


def make_client(**kwargs):
    client = Altertable("key", **kwargs)
    response = Mock(ok=True)
    response.json.return_value = {"ok": True}
    client.session.post = Mock(return_value=response)
    return client


def sent_payloads(client):
    return [call.kwargs["json"] for call in client.session.post.call_args_list]


def test_track_sends_only_audience_fields_and_leaves_properties_unchanged():
    client = make_client(environment="ignored", mode="audience")
    properties = {
        "section": "docs",
        "environment": "business-value",
        "$url": "https://user:password@example.com/docs?token=private#secret",
        "$referer": "https://search.example/private?token=private",
        "$viewport": "1234x987",
    }
    options = {
        "mode": "product",
        "environment": "private-env",
        "anonymous_id": "private-anon",
        "device_id": "private-device",
        "timestamp": "2026-11-09T10:00:00.000Z",
        "properties": properties,
    }
    original = copy.deepcopy(options)

    assert client.track("Opened", "private-user", options) == {"ok": True}

    assert sent_payloads(client) == [
        {
            "mode": "audience",
            "event": "Opened",
            "timestamp": "2026-11-09T10:00:00.000Z",
            "properties": properties,
        }
    ]
    assert options == original


def test_track_does_not_require_distinct_id():
    client = make_client(mode="audience")

    client.track("Opened")

    [payload] = sent_payloads(client)
    assert set(payload) == AUDIENCE_FIELDS
    assert payload["properties"] == {}


def test_raw_batch_cannot_restore_identity_or_select_product_mode():
    client = make_client(mode="audience")
    events = [
        {
            "mode": "product",
            "event": "First",
            "timestamp": 0,
            "distinct_id": "legacy-user",
            "anonymous_id": "legacy-anonymous",
            "device_id": "legacy-device",
            "session_id": "legacy-session",
            "environment": "ignored",
            "properties": {"$url": "/relative?token=private", "environment": "business-value"},
        },
        {"event": "Second"},
    ]
    original = copy.deepcopy(events)

    client.track(events)

    [batch] = sent_payloads(client)
    assert batch[0] == {
        "mode": "audience",
        "event": "First",
        "timestamp": "1970-01-01T00:00:00.000Z",
        "properties": {"$url": "/relative?token=private", "environment": "business-value"},
    }
    assert set(batch[1]) == AUDIENCE_FIELDS
    assert batch[1]["properties"] == {}
    assert events == original


def test_identify_and_alias_are_ignored_silently():
    client = make_client(mode="audience")

    with warnings.catch_warnings():
        warnings.simplefilter("error")
        assert client.identify("user", {"traits": {"email": "private"}}) is None
        assert client.alias("user") is None
        assert client.identify([{"distinct_id": "user"}]) is None
        assert client.alias([{"distinct_id": "user", "new_user_id": "other"}]) is None

    client.session.post.assert_not_called()


def test_mode_is_validated_and_fixed():
    for invalid in ("anonymous", "", None):
        with pytest.raises(ValueError, match="Invalid tracking mode"):
            Altertable("key", mode=invalid)
    client = Altertable("key", mode="audience")
    with pytest.raises(AttributeError):
        client.mode = "product"
    assert client.mode == "audience"
    assert Altertable("key").mode == "product"


def test_product_batch_cannot_select_audience_mode():
    client = make_client()
    event = {
        "mode": "audience",
        "event": "Product",
        "distinct_id": "user",
        "properties": {"mode": "business-value"},
    }

    client.track([event])

    assert sent_payloads(client) == [
        [{"event": "Product", "distinct_id": "user", "properties": {"mode": "business-value"}}]
    ]
    assert event["mode"] == "audience"
