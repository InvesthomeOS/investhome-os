"""Normalized Google Drive errors — no Google SDK types leak to callers."""

from __future__ import annotations


class GoogleDriveError(Exception):
    """Base Drive provider error."""

    def __init__(self, message: str, *, code: str = "drive_error") -> None:
        super().__init__(message)
        self.message = message
        self.code = code


class GoogleDriveAuthError(GoogleDriveError):
    def __init__(self, message: str = "Google Drive authentication failed") -> None:
        super().__init__(message, code="drive_auth_error")


class GoogleDriveNotFoundError(GoogleDriveError):
    def __init__(self, message: str = "Google Drive resource not found") -> None:
        super().__init__(message, code="drive_not_found")


class GoogleDrivePermissionError(GoogleDriveError):
    def __init__(self, message: str = "Google Drive permission denied") -> None:
        super().__init__(message, code="drive_permission_denied")


class GoogleDriveApiError(GoogleDriveError):
    def __init__(self, message: str, *, code: str = "drive_api_error") -> None:
        super().__init__(message, code=code)


class GoogleDriveConfigError(GoogleDriveError):
    def __init__(self, message: str = "Google Drive is not configured") -> None:
        super().__init__(message, code="drive_not_configured")
