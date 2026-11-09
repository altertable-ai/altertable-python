import datetime
import warnings
import requests
from typing import Dict, Any, List, Literal, Optional, Union

TrackingMode = Literal["product", "audience"]

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
    def __init__(self, api_key: str, server_url: str = "https://api.altertable.ai", environment: str = "production", timeout: int = 10000, *, mode: TrackingMode = "product"):
        """
        Initialize the Altertable client.

        :param api_key: API key used to authenticate with the Altertable API.
        :param server_url: Base URL of the Altertable API server.
        :param environment: Environment name (for example, "production" or "staging").
        :param mode: Collection mode, fixed for this client. Audience mode sends events
                     without identity or environment fields and ignores identify and alias.
        :param timeout: Request timeout in milliseconds. This value is converted to seconds
                        before being passed to the underlying `requests` session.
        """
        if mode not in ("product", "audience"):
            raise ValueError('Invalid tracking mode. Use "product" or "audience".')
        self._mode: TrackingMode = mode
        self._identity_warning_emitted = False
        self.api_key = api_key
        self.server_url = server_url.rstrip("/")
        self.environment = environment
        self.timeout = timeout / 1000.0
        self.session = requests.Session()
        self.session.headers.update({"X-API-Key": self.api_key, "Content-Type": "application/json"})

    @property
    def mode(self) -> TrackingMode:
        """Collection mode. Create a new client to change modes."""
        return self._mode

    def _ignore_identity(self) -> bool:
        if self._mode != "audience":
            return False
        if not self._identity_warning_emitted:
            warnings.warn("Altertable identify() and alias() calls are ignored in audience mode.", RuntimeWarning, stacklevel=3)
            self._identity_warning_emitted = True
        return True

    def _apply_mode(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        # The client owns the mode: raw batches and options cannot select another
        # mode or restore identity and environment fields.
        if self._mode == "product":
            return {key: value for key, value in payload.items() if key != "mode"}
        return {
            "mode": "audience",
            "event": payload["event"],
            "timestamp": self._get_timestamp(payload.get("timestamp")),
            "properties": payload.get("properties") or {},
        }

    def _get_timestamp(self, timestamp: Optional[Union[str, int]] = None) -> str:
        if timestamp is None:
            return datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")
        if isinstance(timestamp, int):
            return datetime.datetime.fromtimestamp(timestamp, datetime.timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")
        return timestamp

    def _post(self, endpoint: str, payload: Union[Dict[str, Any], List[Dict[str, Any]]]):
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

    def track(self, event: Union[str, List[Dict[str, Any]]], distinct_id: Optional[str] = None, options: Optional[Dict[str, Any]] = None):
        if isinstance(event, list):
            return self._post("/track", [self._apply_mode(payload) for payload in event])
        if distinct_id is None and self._mode == "product":
            raise TypeError("distinct_id is required when tracking one event")

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
            
        return self._post("/track", self._apply_mode(payload))

    def identify(self, distinct_id: Union[str, List[Dict[str, Any]]], options: Optional[Dict[str, Any]] = None):
        if self._ignore_identity():
            return None
        if isinstance(distinct_id, list):
            return self._post("/identify", distinct_id)

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

    def alias(self, distinct_id: Union[str, List[Dict[str, Any]]], new_user_id: Optional[str] = None, options: Optional[Dict[str, Any]] = None):
        if self._ignore_identity():
            return None
        if isinstance(distinct_id, list):
            return self._post("/alias", distinct_id)
        if new_user_id is None:
            raise TypeError("new_user_id is required when aliasing one user")

        options = options or {}
        payload = {
            "timestamp": self._get_timestamp(options.get("timestamp")),
            "environment": options.get("environment", self.environment),
            "distinct_id": distinct_id,
            "new_user_id": new_user_id,
        }

        return self._post("/alias", payload)
