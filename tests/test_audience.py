"""Applicable audience contracts from altertable-js/test/audience.test.ts.

This server SDK has no browser storage, automatic context, consent queue, hooks,
analytics-source adapters, or built-in retry loop. Inspect serialized requests
through an ordinary HTTP transport adapter, including caller-managed retries.
"""

import copy
import datetime
import json
import threading
import warnings
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import pytest
import requests
from requests.adapters import BaseAdapter

from altertable import Altertable
from altertable.client import ApiError, NetworkError


class RecordingAdapter(BaseAdapter):
    def __init__(self):
        super().__init__()
        self.payloads = []
        self.status = 200
        self.error = None

    def send(self, request, **kwargs):
        self.payloads.append(json.loads(request.body))
        if self.error:
            raise self.error
        response = requests.Response()
        response.status_code = self.status
        response._content = b'{"ok": true}'
        return response

    def close(self):
        pass


@pytest.fixture
def cookie_server():
    requests_seen = []

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, format, *args):
            pass

        def _record(self):
            requests_seen.append(
                (
                    self.path,
                    self.headers.get("Cookie"),
                    self.headers.get("Cookie2"),
                    self.headers.get("Authorization"),
                )
            )

        def _respond(self):
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(b'{"ok": true}')

        def do_POST(self):
            self._record()
            content_length = int(self.headers.get("Content-Length", 0))
            payload = json.loads(self.rfile.read(content_length))
            if payload["event"] == "Redirect":
                self.send_response(302)
                self.send_header("Location", "/redirected")
                self.send_header("Set-Cookie", "server=redirect")
                self.end_headers()
                return
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Set-Cookie", "server=sequential")
            self.end_headers()
            self.wfile.write(b'{"ok": true}')

        def do_GET(self):
            self._record()
            self._respond()

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever)
    thread.start()
    try:
        yield f"http://127.0.0.1:{server.server_port}", requests_seen
    finally:
        server.shutdown()
        thread.join()
        server.server_close()


@pytest.fixture
def audience():
    client = Altertable("key", environment="ignored", mode="audience")
    adapter = RecordingAdapter()
    client.session.mount("https://", adapter)
    yield client, adapter
    client.session.close()


def assert_audience(payload):
    assert set(payload) == {"mode", "event", "timestamp", "properties"}
    assert payload["mode"] == "audience"
    datetime.datetime.fromisoformat(payload["timestamp"].replace("Z", "+00:00"))
    assert "$viewport" not in payload["properties"]


def test_track_without_identity(audience):
    client, adapter = audience
    assert client.track("Opened", options={"properties": {"section": "docs"}}) == {
        "ok": True
    }
    payload = adapter.payloads[0]
    assert_audience(payload)
    assert payload["properties"] == {"section": "docs", "$url": None, "$referer": None}


def test_audience_transport_does_not_store_or_replay_cookies(cookie_server):
    server_url, requests_seen = cookie_server
    client = Altertable("key", server_url=server_url, mode="audience")
    client.session.headers["Cookie"] = "caller=header"
    client.session.headers["Cookie2"] = "caller=legacy-header"
    client.session.headers["Authorization"] = "Bearer caller-token"
    client.session.cookies.set("caller", "jar", domain="127.0.0.1", path="/")

    client.track("First")
    client.track("Second")

    assert requests_seen == [("/track", None, None, None), ("/track", None, None, None)]
    assert not list(client.session.cookies)
    client.session.close()


def test_audience_transport_does_not_replay_redirect_cookies(cookie_server):
    server_url, requests_seen = cookie_server
    client = Altertable("key", server_url=server_url, mode="audience")

    client.track("Redirect")

    assert requests_seen == [
        ("/track", None, None, None),
        ("/redirected", None, None, None),
    ]
    assert not list(client.session.cookies)
    client.session.close()


def test_product_transport_keeps_its_cookie_behavior(cookie_server):
    server_url, requests_seen = cookie_server
    client = Altertable("key", server_url=server_url)

    client.track("First", "user")
    client.track("Second", "user")

    assert requests_seen == [
        ("/track", None, None, None),
        ("/track", "server=sequential", None, None),
    ]
    client.session.close()


def test_single_track_reduces_context_without_mutating_caller(audience):
    client, adapter = audience
    options = {
        "mode": "product",
        "environment": "private-env",
        "anonymous_id": "private-anon",
        "device_id": "private-device",
        "session_id": "private-session",
        "timestamp": "2026-11-04T12:00:00.000Z",
        "properties": {
            "$url": "https://user:password@Site.Example:443/docs?token=secret#hash",
            "$referer": "https://search.example/private?token=secret",
            "$viewport": "1234x987",
            "section": "docs",
            "custom_email": "caller@example.com",
        },
    }
    original = copy.deepcopy(options)
    client.track("Opened", "private-user", options)
    payload = adapter.payloads[0]
    assert_audience(payload)
    assert payload["timestamp"] == options["timestamp"]
    assert payload["properties"] == {
        "$url": "https://site.example/docs",
        "$referer": "https://search.example",
        "section": "docs",
        "custom_email": "caller@example.com",
    }
    assert options == original
    assert "secret" not in json.dumps(payload)
    assert "private-" not in json.dumps(payload)


def test_null_properties_are_normalized_without_mutating_scalar_or_batch_input(audience):
    client, adapter = audience
    scalar_options = {"properties": None}
    batch = [{"event": "Batch", "properties": None}]
    original_scalar_options = copy.deepcopy(scalar_options)
    original_batch = copy.deepcopy(batch)

    client.track("Scalar", options=scalar_options)
    client.track(batch)

    scalar_payload = adapter.payloads[0]
    batch_payload = adapter.payloads[1][0]
    assert_audience(scalar_payload)
    assert_audience(batch_payload)
    assert scalar_payload["event"] == "Scalar"
    assert batch_payload["event"] == "Batch"
    assert scalar_payload["properties"] == {"$url": None, "$referer": None}
    assert batch_payload["properties"] == {"$url": None, "$referer": None}
    assert scalar_options == original_scalar_options
    assert batch == original_batch


def test_every_batch_event_is_normalized_without_chunking(audience):
    client, adapter = audience
    events = [
        {
            "event": f"event-{index}",
            "mode": "product",
            "distinct_id": "private-user",
            "anonymous_id": "private-anon",
            "device_id": "private-device",
            "session_id": "private-session",
            "environment": "private-env",
            "extra": "private-extra",
            "timestamp": 0,
            "properties": {
                "$url": "https://site.example/docs?email=secret#code",
                "$referer": "https://search.example/private?token=secret",
                "$viewport": "1234x987",
                "section": "docs",
            },
        }
        for index in range(101)
    ]
    events.append({"event": "Defaults"})
    original = copy.deepcopy(events)
    client.track(events)
    assert len(adapter.payloads) == 1
    assert len(adapter.payloads[0]) == 102
    for payload in adapter.payloads[0]:
        assert_audience(payload)
    assert adapter.payloads[0][0]["timestamp"] == "1970-01-01T00:00:00.000Z"
    assert adapter.payloads[0][0]["properties"] == {
        "$url": "https://site.example/docs",
        "$referer": "https://search.example",
        "section": "docs",
    }
    assert "private-" not in json.dumps(adapter.payloads)
    assert events == original


@pytest.mark.parametrize(
    "value",
    [
        "not a URL?token=secret",
        "javascript:secret",
        "/relative?token=secret",
        "https://[invalid",
        "https://example.com:invalid/path",
        None,
        42,
        "https://example.com\\@private/path",
        "https://bad host/private",
    ],
)
def test_invalid_urls_are_discarded_in_singles_and_batches(audience, value):
    client, adapter = audience
    properties = {"$url": value, "$referer": value}
    client.track("Single", options={"properties": properties})
    client.track([{"event": "Batch", "properties": properties}])
    for payload in [adapter.payloads[0], adapter.payloads[1][0]]:
        assert payload["properties"] == {"$url": None, "$referer": None}


@pytest.mark.parametrize(
    "url, expected",
    [
        ("https://example.com?secret#hash", "https://example.com/"),
        (
            "http://user:password@example.com:8080/path?q#hash",
            "http://example.com:8080/path",
        ),
        ("https://[::1]:443/path?q#hash", "https://[::1]/path"),
        ("https://éxample.com/path?q#hash", "https://xn--xample-9ua.com/path"),
    ],
)
def test_url_origins_and_paths(audience, url, expected):
    client, adapter = audience
    client.track("Opened", options={"properties": {"$url": url}})
    assert adapter.payloads[0]["properties"]["$url"] == expected


def test_identity_calls_are_ignored_before_validation_and_warn_once(audience):
    client, adapter = audience
    with warnings.catch_warnings(record=True) as recorded:
        warnings.simplefilter("always")
        assert client.identify("user", {"traits": {"email": "secret"}}) is None
        assert client.alias("user") is None
        assert client.identify([{"distinct_id": "user"}]) is None
        assert client.alias([{"distinct_id": "user", "new_user_id": "secret"}]) is None
    assert len(recorded) == 1
    assert "ignored in audience mode" in str(recorded[0].message)
    assert not adapter.payloads
    client.track("After identity calls")
    assert_audience(adapter.payloads[0])


def test_mode_is_fixed_for_client_lifecycle(audience):
    client, adapter = audience
    with pytest.raises(AttributeError):
        client.mode = "product"
    for invalid in ("anonymous", "", None):
        with pytest.raises(ValueError, match="Invalid tracking mode"):
            Altertable("key", mode=invalid)
    client.track("Still active")
    assert_audience(adapter.payloads[0])
    product = Altertable("key")
    product.session.mount("https://", adapter)
    product.track("Product", "user")
    assert adapter.payloads[1]["distinct_id"] == "user"
    assert "mode" not in adapter.payloads[1]
    product.session.close()


def test_network_failure_is_not_queued_or_replayed_by_new_client(audience):
    client, adapter = audience
    adapter.error = requests.exceptions.ConnectionError("Offline")
    with pytest.raises(NetworkError):
        client.track("Offline")
    adapter.error = None
    other = Altertable("key", mode="audience")
    other.session.mount("https://", adapter)
    other.track("New client")
    assert [payload["event"] for payload in adapter.payloads] == [
        "Offline",
        "New client",
    ]
    for payload in adapter.payloads:
        assert_audience(payload)
    other.session.close()


def test_caller_retry_retains_audience_policy(audience):
    client, adapter = audience
    event = {"event": "Retry", "distinct_id": "private", "mode": "product"}
    adapter.status = 503
    with pytest.raises(ApiError) as exc:
        client.track([event])
    assert exc.value.status == 503
    assert len(adapter.payloads) == 1  # No implicit retry loop.
    adapter.status = 200
    client.track([event])
    for batch in adapter.payloads:
        assert_audience(batch[0])


@pytest.mark.parametrize("mode", ["product", None])
def test_product_tracking_preserves_context_and_requires_identity(mode):
    client = Altertable(
        "key", environment="staging", **({"mode": mode} if mode else {})
    )
    adapter = RecordingAdapter()
    client.session.mount("https://", adapter)
    with pytest.raises(TypeError, match="distinct_id is required"):
        client.track("Missing identity")
    properties = {"$url": "https://example.com/?secret#hash", "$viewport": "100x200"}
    client.track(
        "Product",
        "user",
        {"properties": properties, "anonymous_id": "anon", "device_id": "device"},
    )
    payload = adapter.payloads[0]
    assert payload["distinct_id"] == "user"
    assert payload["anonymous_id"] == "anon"
    assert payload["device_id"] == "device"
    assert payload["environment"] == "staging"
    assert payload["properties"] == properties
    assert "mode" not in payload
    client.session.close()


def test_product_batch_cannot_select_audience_processing():
    client = Altertable("key")
    adapter = RecordingAdapter()
    client.session.mount("https://", adapter)
    event = {
        "event": "Product",
        "mode": "audience",
        "distinct_id": "user",
        "environment": "staging",
        "properties": {"mode": "business-value"},
    }
    client.track([event])
    assert adapter.payloads == [
        [{key: value for key, value in event.items() if key != "mode"}]
    ]
    assert event["mode"] == "audience"
    client.session.close()
