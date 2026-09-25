import os
import sys

plugin_dir = os.path.abspath(os.path.dirname(__file__))
vendor_dir = os.path.join(plugin_dir, "_vendor")

if vendor_dir not in sys.path:
    sys.path.insert(0, vendor_dir)
    
if plugin_dir not in sys.path:
    sys.path.insert(0, plugin_dir)

from jiko_bridge_c4d import registerJikoBridge

if __name__ == "__main__":
    registerJikoBridge()
