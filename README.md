# Altertable Python SDK

You can use this SDK to send Product Analytics events to Altertable from Python applications.

## Install

```bash
pip install altertable
```

## Quick start

```python
from altertable import Altertable

client = Altertable("your_api_key")

client.track(
    event="button_clicked",
    distinct_id="user_123",
    options={"properties": {"button_id": "signup_btn", "page": "home"}},
)
```

## API reference

### Initialization

`Altertable(api_key: str)`

Creates a client instance authenticated with your project API key.

```python
client = Altertable("your_api_key")
```

### Tracking

`track(event: str, distinct_id: str, options: dict | None = None)`

Sends an event for a user.

```python
client.track("purchase", "user_123", options={"properties": {"amount": 42}})
```

### Identity

`identify(distinct_id: str, options: dict | None = None)`

Associates traits with a user.

```python
client.identify("user_123", options={"traits": {"email": "user@example.com"}})
```

### Alias

`alias(distinct_id: str, new_user_id: str)`

Merges an anonymous identifier into a known user identifier.

```python
client.alias("anon_123", "user_123")
```

## Configuration

| Option | Type | Default | Description |
|---|---|---|---|
| `base_url` | `str` | `"https://api.altertable.ai"` | API base URL used for requests. |
| `environment` | `str` | `"production"` | Environment tag attached to events. |
| `request_timeout` | `int` | `5` | HTTP timeout in seconds. |
| `release` | `str \| None` | `None` | Application release version. |
| `debug` | `bool` | `False` | Enables debug logging output. |
| `on_error` | `callable \| None` | `None` | Callback invoked on SDK errors. |

## Development

Prerequisites: Python 3.9+ and `pip`.

```bash
pip install -e ".[dev]"
pytest
ruff check .
```

## License

See [LICENSE](LICENSE).