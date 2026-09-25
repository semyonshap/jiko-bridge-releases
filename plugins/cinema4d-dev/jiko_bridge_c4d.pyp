"""Load editable sources from this checkout, without building a bundle."""

import os
from pathlib import Path
import sys

if __name__ == "__main__":
    root = Path(__file__).resolve().parents[2]
    for name in ("jiko-bridge-c4d", "jiko-bridge-client"):
        source = root / "packages" / name
        if not source.is_dir():
            raise RuntimeError(f"Jiko Bridge source directory not found: {source}")
        sys.path.insert(0, str(source))

    if "jiko_bridge_c4d" in sys.modules:
        raise RuntimeError("Jiko Bridge is already loaded. Enable only the development plugin.")

    os.environ.setdefault("JB_ENV", "development")

    from jiko_bridge_c4d import jb_plugin
    from jiko_bridge_c4d.jb_development import enable_development

    enable_development()
    jb_plugin.registerJikoBridge()
