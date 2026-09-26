import json
import logging
import os
import urllib.error
from typing import Any, Optional

JB_ENV = os.getenv("JB_ENV", "production")

_DEFAULT_LEVEL = logging.INFO if JB_ENV == "production" else logging.DEBUG


def get_logger(name: str, level: int | None = None) -> logging.Logger:
    """Return a logger with a single console handler.

    Calling this twice for the same name returns the already configured
    logger untouched, so imports are safe.
    """
    logger = logging.getLogger(name)

    if logger.handlers:
        return logger

    logger.setLevel(level if level is not None else _DEFAULT_LEVEL)
    formatter = logging.Formatter(
        "[Jiko Bridge] %(levelname)s [%(name)s] %(message)s", datefmt="%H:%M:%S"
    )

    console = logging.StreamHandler()
    console.setLevel(logging.DEBUG)
    console.setFormatter(formatter)
    logger.addHandler(console)
    logger.propagate = False

    return logger


def _pretty(value: Any) -> str:
    return json.dumps(value, indent=2, ensure_ascii=False)


def _error_body(error: BaseException) -> str:
    """Best-effort read of an HTTP error response body."""
    try:
        return getattr(error, "read")().decode(errors="replace").strip() or "-"
    except (AttributeError, OSError):
        return "-"


def log_http(
    logger: logging.Logger,
    method: str,
    endpoint: str,
    payload: Optional[dict] = None,
    response: Optional[dict] = None,
    error: Optional[BaseException] = None,
) -> None:
    """Log one HTTP exchange: what was sent, then the reply or the failure."""
    sent = f"{method} {endpoint}"
    if payload is not None:
        sent += "\n" + _pretty(payload)

    if error is None:
        logger.debug("API response: %s\n%s", sent, _pretty(response))
    elif isinstance(error, urllib.error.HTTPError) and error.code == 404:
        logger.debug(
            "JB_API not found: %s %s\nRequest: %s",
            error.code,
            error.reason,
            sent,
        )
    elif isinstance(error, urllib.error.HTTPError):
        logger.error(
            "JB_API HTTP error: %s %s\nRequest: %s\nResponse: %s",
            error.code,
            error.reason,
            sent,
            _error_body(error),
        )
    else:
        logger.exception("JB_API error: %s\nRequest: %s", error, sent)
