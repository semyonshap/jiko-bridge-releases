"""Build a PythonModule compatible with Houdini's Python 3.10+ runtime."""

import sys
from pathlib import Path

import black

PACKAGE = Path(__file__).resolve().parent
ROOT = PACKAGE.parent.parent
sys.path.insert(0, str(PACKAGE.parent / "jiko-bundler"))

from jiko_bundler.bundler import bundle_to_file  # noqa: E402


def main() -> None:
    """Bundle local packages and normalise syntax for older Houdini Python versions."""
    output = ROOT / "dist/houdini/PythonModule.py"
    result = bundle_to_file(
        PACKAGE / "jiko_bridge_houdini/entry.py",
        output,
        search_paths=[PACKAGE, PACKAGE.parent / "jiko-bridge-client"],
        external=["hou", "pxr", "loputils"],
    )
    # New Python AST unparsers can reuse quotes inside f-strings. Houdini 20.5
    # ships Python 3.11, so keep the result compatible with the package minimum.
    source = black.format_str(
        result.source,
        mode=black.Mode(line_length=100, target_versions={black.TargetVersion.PY310}),
    )
    compile(source, str(output), "exec")
    output.write_text(source, encoding="utf-8")
    print(f"Bundled {len(result.modules)} files -> {output}")


if __name__ == "__main__":
    main()
