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
client.track_batch([
    {"event": "button_clicked", "distinct_id": "user_123", "environment": "production"},
    {"event": "checkout_started", "distinct_id": "user_123", "environment": "production"},
])
```

`identify_batch` and `alias_batch` provide the same pass-through behavior.

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
