import json
import os
import urllib.request
from typing import Any, Dict, Optional

from jb_asset_model import AssetModel


class JB_API:
    """Класс для взаимодействия с Jiko Bridge сервером"""

    def __init__(self, host: str = "127.0.0.1", port: int = 8765):
        self.host = host
        self.port = port
        self.base_url = f"http://{host}:{port}"

    def _make_request(self, endpoint: str) -> Optional[Dict[str, Any]]:
        """Выполняет HTTP запрос к серверу"""
        try:
            url = f"{self.base_url}{endpoint}"

            request = urllib.request.Request(url)

            with urllib.request.urlopen(request, timeout=5) as response:
                if response.getcode() == 200:
                    data = response.read().decode('utf-8')
                    return json.loads(data)
                else:
                    print(f"HTTP Error: {response.getcode()}")
                    return None

        except Exception as e:
            print(f"Unexpected error: {e}")
            return None

    def get_server_status(self) -> Optional[Dict[str, Any]]:
        """Получает статус сервера"""
        return self._make_request("/status")

    def get_active_asset(self) -> Optional[AssetModel]:
        """Получает информацию об активном ассете"""
        request = self._make_request("/active-asset")
        data = request.get("data", None)

        if data:
            asset_path = data.get('file_path', '')
            asset_name = data.get('name', '')
            pack_name = data.get('pack_name', '')

            if asset_path and os.path.exists(asset_path) and asset_name and pack_name:
                asset = AssetModel(
                    asset_path=asset_path, asset_name=asset_name, pack_name=pack_name
                )
                return asset

        return None
