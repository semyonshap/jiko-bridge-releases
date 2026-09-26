import json
import os
import platform
import urllib.error
import urllib.request
from typing import Optional

from .contracts import JbAPIABC
from .logger import get_logger, log_http
from .models import AssetModel

DEFAULT_PORT = 5174

logger = get_logger(__name__)


def _get_port() -> int:
    """Read the API port from the Jiko Bridge desktop app settings.

    Falls back to DEFAULT_PORT when the settings file is missing or
    unreadable, so the client always has a usable address.
    """
    system = platform.system()
    if system == "Windows":
        path = os.path.join(os.getenv("APPDATA", ""), "jiko-bridge", "settings.json")
    elif system == "Darwin":
        path = os.path.expanduser("~/Library/Application Support/jiko-bridge/settings.json")
    else:
        base = os.getenv("XDG_CONFIG_HOME", os.path.expanduser("~/.config"))
        path = os.path.join(base, "jiko-bridge", "settings.json")

    try:
        with open(path, "r", encoding="utf-8") as f:
            port = json.load(f).get("apiPort")
        if isinstance(port, int):
            return port
    except (OSError, json.JSONDecodeError):
        pass

    return DEFAULT_PORT


class JbAPI(JbAPIABC):
    """Client for communicating with the Jiko Bridge API server."""

    def __init__(self, host: str = "localhost", port: Optional[int] = None):
        self.base_url = f"http://{host}:{port or _get_port()}"

    def _request(
        self,
        endpoint: str,
        payload: Optional[dict] = None,
        method: str = "GET",
        timeout: int = 15,
    ) -> Optional[dict]:
        data = json.dumps(payload).encode() if payload is not None else None
        headers = {"Content-Type": "application/json"} if data else {}
        req = urllib.request.Request(
            f"{self.base_url}{endpoint}", data=data, headers=headers, method=method
        )

        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                parsed = json.loads(resp.read().decode())
        except (urllib.error.URLError, json.JSONDecodeError, OSError) as e:
            log_http(logger, method, endpoint, payload, error=e)
            return None

        log_http(logger, method, endpoint, payload, response=parsed)
        return parsed

    def _asset(
        self,
        endpoint: str,
        payload: Optional[dict] = None,
        method: str = "GET",
        timeout: int = 15,
    ) -> Optional[AssetModel]:
        """Query an asset endpoint and decode the reply into an asset."""
        data = (self._request(endpoint, payload, method, timeout) or {}).get("data")
        return AssetModel.from_dict(data) if data else None

    def get_active_asset(self) -> Optional[AssetModel]:
        return self._asset("/api/asset/active")

    def get_asset_by_search(self, search_key: str) -> Optional[AssetModel]:
        return self._asset("/api/asset", {"searchKey": search_key}, "POST")

    def get_asset(self, asset: AssetModel) -> Optional[AssetModel]:
        return self._asset("/api/asset", asset.to_dict(), "POST")

    def create_asset(self, asset: AssetModel) -> Optional[AssetModel]:
        return self._asset("/api/asset/create", asset.to_dict(), "POST", 300)

    def update_asset(self, asset: AssetModel) -> Optional[AssetModel]:
        return self._asset("/api/asset/update", asset.to_dict(), "POST", 30)
