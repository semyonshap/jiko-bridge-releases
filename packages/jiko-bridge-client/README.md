# jiko-bridge-client

Shared models, HTTP API client and integration contracts for **Jiko Bridge** DCC plugins.

Standard library only · no DCC imports · typed (PEP 561) · Python 3.10+

## Installation

```bash
pip install jiko-bridge-client
```

## Quick start

```python
from jiko_bridge_client import JbAPI

api = JbAPI()                              # port read from the app's settings.json
api = JbAPI(host="127.0.0.1", port=5174)   # or connect explicitly

asset = api.get_active_asset()             # Optional[AssetModel]
if asset:
    print(asset.pack_name, asset.asset_name)
    for f in asset.files:
        print(f.bridge_type, f.filepath)
```
