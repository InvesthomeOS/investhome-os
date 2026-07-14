"""Storage provider abstraction for document binary files."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import BinaryIO


class StorageProviderBase(ABC):
    """Abstract storage backend — local, S3, GCS, Azure implementations."""

    @abstractmethod
    def save(self, storage_key: str, stream: BinaryIO, *, content_length: int) -> None:
        """Persist binary content at the given storage key."""

    @abstractmethod
    def open(self, storage_key: str) -> BinaryIO:
        """Open a readable stream for the stored object."""

    @abstractmethod
    def exists(self, storage_key: str) -> bool:
        """Return True if the object exists."""

    @abstractmethod
    def delete(self, storage_key: str) -> None:
        """Remove the stored object (used sparingly — versions are preserved)."""

    def get_signed_url(self, storage_key: str, *, expires_seconds: int = 3600) -> str | None:
        """Return a time-limited URL for direct download (cloud providers)."""
        return None
