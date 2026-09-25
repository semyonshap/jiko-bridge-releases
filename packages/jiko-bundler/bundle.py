"""Run the local CLI from a checkout without installing the package first."""

from jiko_bundler.cli import main

if __name__ == "__main__":
    raise SystemExit(main())
