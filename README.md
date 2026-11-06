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

Use an environment-bound Product Analytics API key and `mode="audience"` to collect events without client identity fields:

```python
audience = Altertable("your_api_key", mode="audience")
audience.track(
    "Docs Opened",
    options={"properties": {"$url": "https://example.com/docs?source=email"}},
)
audience.track([
    {"event": "Install Copied", "properties": {"package": "python"}},
])
```

Product mode is the default. Mode is fixed for each client; create a new client to
change it. Audience events omit user, anonymous, device, session, and environment
fields, including caller-supplied batch fields. The API key selects the environment;
legacy unbound keys cannot be used. `identify()` and `alias()` return `None` without
sending requests and emit a `RuntimeWarning` once per client.

Audience mode removes `$viewport`, reduces `$url` to HTTP(S) origin plus path, and
reduces `$referer` to origin. Invalid URLs become `None`. Custom properties and URL
paths can still contain personal information; choose them accordingly.

Gate calls on your application's consent decisions. Events are sent synchronously;
failed sends raise `ApiError` or `NetworkError` without automatic retries or replay.

The backend derives audience visitors from the request IP and User-Agent. For this
server SDK, those identify your server and HTTP client, so these events cannot
reliably measure distinct browser visitors. End-user request headers are not
forwarded automatically.

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
