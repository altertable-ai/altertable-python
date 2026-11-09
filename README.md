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

### Audience measurement

With an environment-bound API key, pass `mode="audience"` to send events without
identity or environment fields:

```python
audience = Altertable("your_api_key", mode="audience")
audience.track("docs_opened", options={"properties": {"page": "install"}})
```

Mode is fixed for each client. Audience events contain only `mode`, `event`,
`timestamp`, and `properties`, including in batches; `identify()` and `alias()`
return `None` without sending a request. Product clients drop any top-level
`mode` field from batch entries.

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
