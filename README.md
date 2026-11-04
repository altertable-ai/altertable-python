# Altertable Python SDK

Official Python SDK for Altertable Product Analytics.

## Installation

You can install the package via `pip`:

```bash
pip install altertable
```

Or using `poetry`:

```bash
poetry add altertable
```

## Usage

### Initialization

```python
from altertable import Altertable

client = Altertable("your_api_key")
```

### Tracking Events

```python
client.track(
    event="button_clicked",
    distinct_id="user_123",
    options={
        "properties": {
            "button_id": "signup_btn",
            "page": "home"
        }
    }
)
```

### Batch tracking

Server applications can submit a caller-managed batch directly. The SDK does
not impose a client-side batch-size limit.

```python
client.track([
    {"event": "button_clicked", "distinct_id": "user_123", "environment": "production"},
    {"event": "checkout_started", "distinct_id": "user_123", "environment": "production"},
])
```

Pass arrays to `identify` and `alias` for the same pass-through behavior.
The client owns the collection mode: top-level `mode` fields in product batches
are removed before sending, so a batch cannot switch to audience processing.

### Audience measurement

Use `mode="audience"` to collect events without client identity fields:

```python
audience = Altertable("your_api_key", mode="audience")
audience.track(
    "Docs Opened",
    options={"properties": {"$url": "https://example.com/docs?source=email", "section": "intro"}},
)
audience.track([
    {"event": "Install Copied", "properties": {"package": "python"}},
    {"event": "Docs Opened", "properties": {"$url": "https://example.com/docs"}},
])
```

Product mode remains the default. `mode` is read-only for a client's lifetime;
create a new client to change modes. Only `"product"` and `"audience"` are accepted.

Audience requests contain only `mode: "audience"`, `event`, `timestamp`, and
`properties`. Both single events and every event in a batch follow this policy,
even if the caller supplies identity, environment, or a conflicting mode.
Audience mode requires an API key bound to an environment; that key determines
the audience environment. Legacy unbound keys cannot select an audience
environment. Product mode continues to honor the existing `environment` argument and per-event overrides.

In audience properties, `$url` is reduced to origin plus path and `$referer` to
origin only. Credentials, query strings, and fragments are removed; invalid or
non-HTTP(S) URLs become `None`. `$viewport` is removed. Missing `$url` and
`$referer` are sent as `None`. Other caller properties are retained, including
custom identifiers or personal information: review your properties and URL paths
before sending them. The SDK does not automatically collect browser context or
extract query parameters. Sanitization copies properties without changing inputs.

`identify()` and `alias()` (including batch calls) return `None` without sending
requests in audience mode. The client emits a `RuntimeWarning` once when these
methods are used. HTTP transport adapters mounted on `client.session` remain
supported.

This is a synchronous server SDK. It does not persist identities or events,
buffer events, automatically retry requests, or replay failed events in a new
client. Failed sends raise the existing `ApiError` or `NetworkError`; applications
can retry explicitly. It has no consent API: applications must gate calls on their
own consent decisions, and audience mode does not override those decisions.

Audience visitor hashing on the backend uses the request IP and User-Agent.
With this server SDK, those describe your server and HTTP client, rather than the
end-user browser. Browser visitor counts therefore cannot be reconstructed
reliably from these server requests. The SDK does not forward end-user IP or
User-Agent headers automatically.

### Identifying Users

```python
client.identify(
    distinct_id="user_123",
    options={
        "traits": {
            "email": "user@example.com",
            "name": "John Doe"
        },
        "anonymous_id": "previous_anon_id"
    }
)
```

### Alias

```python
client.alias(
    distinct_id="previous_anonymous_id",
    new_user_id="new_user_id"
)
```

## License

The package is available as open source under the terms of the [MIT License](https://opensource.org/licenses/MIT).
