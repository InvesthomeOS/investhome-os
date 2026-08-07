"""Google Drive API provider — auth, list, metadata, download. No Media Library logic."""

from __future__ import annotations

import logging
from collections.abc import Iterator
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Protocol

from investhome_api.config.settings import Settings, get_settings
from investhome_api.services.google_drive.categories import DRIVE_FOLDER_MIME
from investhome_api.services.google_drive.errors import (
    GoogleDriveApiError,
    GoogleDriveAuthError,
    GoogleDriveConfigError,
    GoogleDriveError,
    GoogleDriveNotFoundError,
    GoogleDrivePermissionError,
)

logger = logging.getLogger(__name__)

_FILE_FIELDS = (
    "id,name,mimeType,size,createdTime,modifiedTime,md5Checksum,"
    "parents,webViewLink,thumbnailLink,trashed"
)


@dataclass(frozen=True)
class DriveFileMeta:
    id: str
    name: str
    mime_type: str
    size: int | None
    created_at: datetime | None
    modified_at: datetime | None
    md5_checksum: str | None
    parent_ids: tuple[str, ...]
    web_view_link: str | None
    thumbnail_link: str | None
    trashed: bool = False

    @property
    def is_folder(self) -> bool:
        return self.mime_type == DRIVE_FOLDER_MIME


@dataclass(frozen=True)
class DriveChange:
    """One item from Drive Changes API (file may be None when removed)."""

    file_id: str
    removed: bool
    file: DriveFileMeta | None = None


@dataclass(frozen=True)
class DriveChangesPage:
    changes: tuple[DriveChange, ...]
    next_page_token: str | None
    new_start_page_token: str | None


class GoogleDriveProviderProtocol(Protocol):
    """Testable surface used by DriveAssetScanner / incremental sync."""

    @property
    def root_folder_id(self) -> str: ...

    def get_file(self, file_id: str) -> DriveFileMeta: ...

    def list_children(self, folder_id: str, *, page_size: int = 100) -> Iterator[DriveFileMeta]: ...

    def is_descendant_of_root(self, folder_id: str) -> bool: ...

    def download_bytes(self, file_id: str, *, max_bytes: int | None = None) -> bytes: ...

    def get_start_page_token(self) -> str: ...

    def list_changes(
        self,
        page_token: str,
        *,
        page_size: int = 100,
    ) -> DriveChangesPage: ...


def _parse_rfc3339(value: str | None) -> datetime | None:
    if not value:
        return None
    # Drive returns e.g. 2024-01-15T12:00:00.000Z
    normalized = value.replace("Z", "+00:00")
    try:
        return datetime.fromisoformat(normalized)
    except ValueError:
        return None


def _normalize_file(raw: dict[str, Any]) -> DriveFileMeta:
    parents = raw.get("parents") or []
    size_raw = raw.get("size")
    return DriveFileMeta(
        id=str(raw["id"]),
        name=str(raw.get("name") or ""),
        mime_type=str(raw.get("mimeType") or "application/octet-stream"),
        size=int(size_raw) if size_raw is not None else None,
        created_at=_parse_rfc3339(raw.get("createdTime")),
        modified_at=_parse_rfc3339(raw.get("modifiedTime")),
        md5_checksum=raw.get("md5Checksum"),
        parent_ids=tuple(str(p) for p in parents),
        web_view_link=raw.get("webViewLink"),
        thumbnail_link=raw.get("thumbnailLink"),
        trashed=bool(raw.get("trashed", False)),
    )


def _map_http_error(exc: BaseException) -> GoogleDriveError:
    status = getattr(exc, "status_code", None) or getattr(exc, "resp", None)
    code = None
    if status is not None and hasattr(status, "status"):
        code = int(status.status)
    elif isinstance(status, int):
        code = status
    message = str(exc)
    lower = message.lower()
    if code == 401 or "invalid_grant" in lower or "credentials" in lower:
        return GoogleDriveAuthError(message)
    if code == 403:
        return GoogleDrivePermissionError(message)
    if code == 404:
        return GoogleDriveNotFoundError(message)
    # Changes API returns 410 when startPageToken is invalid/expired
    if code == 410 or "page token" in lower or "startpagetoken" in lower.replace(" ", ""):
        return GoogleDriveApiError(message, code="drive_invalid_page_token")
    if code == 429:
        return GoogleDriveApiError(message, code="drive_rate_limited")
    if code is not None and code >= 500:
        return GoogleDriveApiError(message, code="drive_server_error")
    return GoogleDriveApiError(message)


class GoogleDriveProvider:
    """Live Google Drive v3 client. Credentials come only from Settings / env."""

    def __init__(self, settings: Settings | None = None) -> None:
        self._settings = settings or get_settings()
        self._service: Any | None = None

    @property
    def root_folder_id(self) -> str:
        root = (self._settings.google_drive_root_folder_id or "").strip()
        if not root:
            raise GoogleDriveConfigError("GOOGLE_DRIVE_ROOT_FOLDER_ID is not set")
        return root

    def _ensure_configured(self) -> None:
        s = self._settings
        missing = [
            name
            for name, val in (
                ("GOOGLE_DRIVE_CLIENT_ID", s.google_drive_client_id),
                ("GOOGLE_DRIVE_CLIENT_SECRET", s.google_drive_client_secret),
                ("GOOGLE_DRIVE_REFRESH_TOKEN", s.google_drive_refresh_token),
                ("GOOGLE_DRIVE_ROOT_FOLDER_ID", s.google_drive_root_folder_id),
            )
            if not (val or "").strip()
        ]
        if missing:
            raise GoogleDriveConfigError(
                f"Google Drive is not configured (missing: {', '.join(missing)})"
            )

    def _build_service(self) -> Any:
        if self._service is not None:
            return self._service
        self._ensure_configured()
        try:
            from google.auth.transport.requests import Request
            from google.oauth2.credentials import Credentials
            from googleapiclient.discovery import build
        except ImportError as exc:
            raise GoogleDriveConfigError(
                "google-api-python-client / google-auth are not installed"
            ) from exc

        s = self._settings
        creds = Credentials(
            token=None,
            refresh_token=s.google_drive_refresh_token,
            token_uri="https://oauth2.googleapis.com/token",
            client_id=s.google_drive_client_id,
            client_secret=s.google_drive_client_secret,
            scopes=["https://www.googleapis.com/auth/drive.readonly"],
        )
        try:
            creds.refresh(Request())
        except Exception as exc:
            logger.warning("google_drive_auth_refresh_failed", extra={"error_type": type(exc).__name__})
            raise GoogleDriveAuthError("Failed to refresh Google Drive credentials") from exc

        self._service = build("drive", "v3", credentials=creds, cache_discovery=False)
        return self._service

    def get_file(self, file_id: str) -> DriveFileMeta:
        service = self._build_service()
        try:
            raw = (
                service.files()
                .get(fileId=file_id, fields=_FILE_FIELDS, supportsAllDrives=True)
                .execute()
            )
        except Exception as exc:
            raise _map_http_error(exc) from exc
        return _normalize_file(raw)

    def list_children(self, folder_id: str, *, page_size: int = 100) -> Iterator[DriveFileMeta]:
        """Paginated children of a folder (files + subfolders). Skips trashed."""
        service = self._build_service()
        page_token: str | None = None
        query = f"'{folder_id}' in parents and trashed = false"
        while True:
            try:
                response = (
                    service.files()
                    .list(
                        q=query,
                        spaces="drive",
                        fields=f"nextPageToken, files({_FILE_FIELDS})",
                        pageToken=page_token,
                        pageSize=min(page_size, 1000),
                        supportsAllDrives=True,
                        includeItemsFromAllDrives=True,
                    )
                    .execute()
                )
            except Exception as exc:
                raise _map_http_error(exc) from exc

            for raw in response.get("files", []):
                yield _normalize_file(raw)

            page_token = response.get("nextPageToken")
            if not page_token:
                break

    def is_descendant_of_root(self, folder_id: str) -> bool:
        """True if folder_id is the approved root or nested beneath it."""
        root = self.root_folder_id
        if folder_id == root:
            return True
        current = folder_id
        seen: set[str] = set()
        while current and current not in seen:
            seen.add(current)
            if current == root:
                return True
            meta = self.get_file(current)
            if not meta.parent_ids:
                return False
            # Prefer first parent; shared-drive edges are rare for project trees
            current = meta.parent_ids[0]
        return False

    def download_bytes(self, file_id: str, *, max_bytes: int | None = None) -> bytes:
        """Download file media (not used during scan; available for later pipelines)."""
        service = self._build_service()
        try:
            from googleapiclient.http import MediaIoBaseDownload
            import io
        except ImportError as exc:
            raise GoogleDriveConfigError(
                "google-api-python-client is not installed"
            ) from exc

        request = service.files().get_media(fileId=file_id, supportsAllDrives=True)
        buffer = io.BytesIO()
        downloader = MediaIoBaseDownload(buffer, request)
        done = False
        try:
            while not done:
                _, done = downloader.next_chunk()
                if max_bytes is not None and buffer.tell() > max_bytes:
                    raise GoogleDriveApiError(
                        f"Download exceeded max_bytes={max_bytes}",
                        code="drive_download_too_large",
                    )
        except GoogleDriveError:
            raise
        except Exception as exc:
            raise _map_http_error(exc) from exc
        return buffer.getvalue()

    def get_start_page_token(self) -> str:
        """Initial Changes API cursor for this credential (global per user)."""
        service = self._build_service()
        try:
            response = service.changes().getStartPageToken(supportsAllDrives=True).execute()
        except Exception as exc:
            raise _map_http_error(exc) from exc
        token = response.get("startPageToken")
        if not token:
            raise GoogleDriveApiError("Drive did not return startPageToken")
        return str(token)

    def list_changes(
        self,
        page_token: str,
        *,
        page_size: int = 100,
    ) -> DriveChangesPage:
        """One page of Drive changes since ``page_token``."""
        service = self._build_service()
        try:
            response = (
                service.changes()
                .list(
                    pageToken=page_token,
                    spaces="drive",
                    pageSize=min(page_size, 1000),
                    fields=(
                        "nextPageToken,newStartPageToken,"
                        f"changes(fileId,removed,file({_FILE_FIELDS}))"
                    ),
                    includeItemsFromAllDrives=True,
                    supportsAllDrives=True,
                    includeRemoved=True,
                )
                .execute()
            )
        except Exception as exc:
            raise _map_http_error(exc) from exc

        changes: list[DriveChange] = []
        for raw in response.get("changes", []) or []:
            file_id = str(raw.get("fileId") or "")
            if not file_id:
                continue
            removed = bool(raw.get("removed"))
            file_raw = raw.get("file")
            meta = _normalize_file(file_raw) if isinstance(file_raw, dict) else None
            if meta is not None and meta.trashed:
                removed = True
            changes.append(DriveChange(file_id=file_id, removed=removed, file=meta))

        return DriveChangesPage(
            changes=tuple(changes),
            next_page_token=response.get("nextPageToken"),
            new_start_page_token=response.get("newStartPageToken"),
        )


def get_google_drive_provider(settings: Settings | None = None) -> GoogleDriveProvider:
    return GoogleDriveProvider(settings=settings)
