"""Build plain Python source files from statically imported local modules."""

from .bundler import BundleError, BundleResult, bundle, bundle_to_file

__all__ = ["BundleError", "BundleResult", "bundle", "bundle_to_file"]
__version__ = "0.1.0"
