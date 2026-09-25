"""Command line interface for the source bundler."""

import argparse
import sys
from pathlib import Path

from . import __version__
from .bundler import BundleError, bundle_to_file


def main(argv: list[str] | None = None) -> int:
    """Build a bundle and report actionable diagnostics without a traceback."""
    parser = argparse.ArgumentParser(
        description="Merge static Python modules into one readable file without a runtime loader."
    )
    parser.add_argument("entry", type=Path, help="Entry script (.py, .pyp, etc.)")
    parser.add_argument("-o", "--output", type=Path, required=True, help="Output source file")
    parser.add_argument(
        "-I",
        "--python-path",
        action="append",
        default=[],
        type=Path,
        help="Local import root; repeat for multiple packages (entry directory is included)",
    )
    parser.add_argument(
        "--external",
        action="append",
        default=[],
        metavar="MODULE",
        help="Keep this module and its submodules external, even if found locally; repeatable",
    )
    parser.add_argument("--strip-docstrings", action="store_true")
    parser.add_argument("--version", action="version", version=__version__)
    args = parser.parse_args(argv)
    try:
        result = bundle_to_file(
            args.entry,
            args.output,
            search_paths=args.python_path,
            external=args.external,
            strip_docstrings=args.strip_docstrings,
        )
    except (BundleError, OSError) as error:
        print(f"jiko-bundle: {error}", file=sys.stderr)
        return 1
    print(f"Bundled {len(result.modules)} files -> {args.output}")
    return 0
