import datetime
import requests
from typing import Dict, Any, Optional, Union

class AltertableError(Exception):
    pass

class ApiError(AltertableError):
    def __init__(self, status: int, message: str, details: Any = None):
        super().__init__(message)
        self.status = status
        self.details = details

class NetworkError(AltertableError):
    def __init__(self, message: str, cause: Exception):
        super().__init__(message)
        self.cause = cause

class Altertable:
    def __init__(self, api_key: str, server_url: str = "https://api.altertable.ai", environment: str = "production", timeout: int = 10000):
        self.api_key = api_key
        self.server_url = server_url.rstrip("/")
        self.environment = environment
        self.timeout = timeout / 1000.0
        self.session = requests.Session()
        self.session.headers.update({"X-API-Key": self.api_key, "Content-Type": "application/json"})

    def _get_timestamp(self, timestamp: Optional[Union[str, int]] = None) -> str:
        if timestamp is None:
            return datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")
        if isinstance(timestamp, int):
            return datetime.datetime.fromtimestamp(timestamp, datetime.timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")
        return timestamp

    def _post(self, endpoint: str, payload: Dict[str, Any]):
        try:
            response = self.session.post(f"{self.server_url}{endpoint}", json=payload, timeout=self.timeout)
            if not response.ok:
                try:
                    error_data = response.json()
                    raise ApiError(response.status_code, error_data.get("message", "API Error"), error_data)
                except ValueError:
                    raise ApiError(response.status_code, response.text)
            return response.json()
        except requests.exceptions.RequestException as e:
            raise NetworkError("Network request failed", e)

    def track(self, event: str, distinct_id: str, options: Optional[Dict[str, Any]] = None):
        options = options or {}
        payload = {
            "timestamp": self._get_timestamp(options.get("timestamp")),
            "event": event,
            "environment": options.get("environment", self.environment),
            "distinct_id": distinct_id,
            "properties": options.get("properties", {})
        }
        if "anonymous_id" in options:
            payload["anonymous_id"] = options["anonymous_id"]
        if "device_id" in options:
            payload["device_id"] = options["device_id"]
            
        return self._post("/track", payload)

    def identify(self, distinct_id: str, options: Optional[Dict[str, Any]] = None):
        options = options or {}
        payload = {
            "timestamp": self._get_timestamp(options.get("timestamp")),
            "environment": options.get("environment", self.environment),
            "distinct_id": distinct_id,
        }
        if "traits" in options:
            payload["traits"] = options["traits"]
        if "anonymous_id" in options:
            payload["anonymous_id"] = options["anonymous_id"]
        if "device_id" in options:
            payload["device_id"] = options["device_id"]

        return self._post("/identify", payload)

    def alias(self, distinct_id: str, new_user_id: str, options: Optional[Dict[str, Any]] = None):
        options = options or {}
        payload = {
            "timestamp": self._get_timestamp(options.get("timestamp")),
            "environment": options.get("environment", self.environment),
            "distinct_id": distinct_id,
            "new_user_id": new_user_id,
        }

        return self._post("/alias", payload)
