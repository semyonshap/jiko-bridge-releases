"""
Api client to Jiko Bridge
Code by Semyon Shapoval, 2026
"""

import json
import os
import platform
import urllib.error
import urllib.request
from typing import Optional


from src.jb_types import AssetModel
from src.jb_protocols import JbAPIProtocol
from src.jb_utils import get_logger

DEFAULT_PORT = 5174

logger = get_logger(__name__)


def _get_port() -> int:
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


class JbAPI(JbAPIProtocol):
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
        url = f"{self.base_url}{endpoint}"
        data = json.dumps(payload).encode() if payload else None
        headers = {"Content-Type": "application/json"} if data else {}

        try:
            req = urllib.request.Request(url, data=data, headers=headers, method=method)
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                parsed = json.loads(resp.read().decode())
                pretty = json.dumps(parsed, indent=2, ensure_ascii=False)
                logger.debug("API response: %s %s\n%s", method, endpoint, pretty)
                return parsed
        except urllib.error.HTTPError as e:
            logger.error("JB_API HTTP error: %s %s", e.code, e.reason)
            return None
        except (urllib.error.URLError, json.JSONDecodeError, OSError) as e:
            logger.exception("JB_API error: %s", e)
            return None

    def _asset_from_response(self, resp: Optional[dict]) -> Optional[AssetModel]:
        payload = (resp or {}).get("data")
        if not payload:
            return None
        return AssetModel.from_dict(payload)

    def get_active_asset(self) -> Optional[AssetModel]:
        return self._asset_from_response(self._request("/api/asset/active"))

    def get_asset_by_search(self, search_key) -> Optional[AssetModel]:
        return self._asset_from_response(
            self._request("/api/asset", {"searchKey": search_key}, method="POST")
        )

    def get_asset(self, asset) -> Optional[AssetModel]:
        return self._asset_from_response(
            self._request("/api/asset", asset.to_dict(), method="POST")
        )

    def create_asset(self, asset: AssetModel) -> Optional[AssetModel]:
        return self._asset_from_response(
            self._request("/api/asset/create", asset.to_dict(), method="POST", timeout=300)
        )

    def update_asset(self, asset: AssetModel) -> Optional[AssetModel]:
        return self._asset_from_response(
            self._request("/api/asset/update", asset.to_dict(), method="POST", timeout=30)
        )
