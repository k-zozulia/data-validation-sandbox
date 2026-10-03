"""Errors that should surface to the client as a clean JSON 4xx."""
from __future__ import annotations


class AppException(Exception):
    """E.g. raise AppException(413, "file_too_large", "File exceeds limit").

    `extra` is merged into the response body (used e.g. for rule lint issues).
    """

    def __init__(self, status_code: int, error: str, detail: str | None = None,
                 extra: dict | None = None):
        self.status_code = status_code
        self.error = error
        self.detail = detail
        self.extra = extra or {}
        super().__init__(detail or error)


def not_found(what: str) -> AppException:
    return AppException(404, f"{what}_not_found", f"Unknown {what.replace('_', ' ')} id")
