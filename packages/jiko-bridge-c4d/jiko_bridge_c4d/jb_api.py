"""
Cinema 4D entry point to the shared Jiko Bridge API client.

Re-exported rather than imported directly so the plugin keeps one local seam
for the integration tests to patch.
"""

from jiko_bridge_client import JbAPI

__all__ = ["JbAPI"]
