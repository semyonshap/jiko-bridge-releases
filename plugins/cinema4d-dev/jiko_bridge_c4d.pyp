import importlib
import os
from pathlib import Path
import sys

if __name__ == "__main__":
    dev_root = Path(__file__).resolve().parent
    root = dev_root.parents[1]
    for name in ("jiko-bridge-c4d", "jiko-bridge-client"):
        source = root / "packages" / name
        if not source.is_dir():
            raise RuntimeError(f"Jiko Bridge source directory not found: {source}")
        sys.path.insert(0, str(source))
    sys.path.insert(0, str(dev_root))

    if "jiko_bridge_c4d" in sys.modules:
        raise RuntimeError("Jiko Bridge is already loaded. Enable only the development plugin.")

    os.environ.setdefault("JB_ENV", "development")

    development = importlib.import_module("jb_development")

    from jiko_bridge_c4d import jb_plugin

    jb_plugin.registerJikoBridge()
    development.register_reload_command()
