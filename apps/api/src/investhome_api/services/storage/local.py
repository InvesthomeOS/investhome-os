"""Local filesystem storage provider for development and Docker."""

from __future__ import annotations

import os
import shutil
from pathlib import Path
from typing import BinaryIO

from investhome_api.services.storage.base import StorageProviderBase


class LocalStorageProvider(StorageProviderBase):
    def __init__(self, root_path: str) -> None:
        self._root = Path(root_path).resolve()
        self._root.mkdir(parents=True, exist_ok=True)

    def _resolve_key(self, storage_key: str) -> Path:
        normalized = storage_key.replace("\\", "/").lstrip("/")
        if ".." in normalized.split("/"):
            msg = "Invalid storage key: path traversal detected"
            raise ValueError(msg)
        target = (self._root / normalized).resolve()
        if not str(target).startswith(str(self._root)):
            msg = "Invalid storage key: escapes storage root"
            raise ValueError(msg)
        return target

    def save(self, storage_key: str, stream: BinaryIO, *, content_length: int) -> None:
        target = self._resolve_key(storage_key)
        target.parent.mkdir(parents=True, exist_ok=True)
        with open(target, "wb") as dest:
            shutil.copyfileobj(stream, dest)

    def open(self, storage_key: str) -> BinaryIO:
        target = self._resolve_key(storage_key)
        if not target.is_file():
            msg = "Stored file not found"
            raise FileNotFoundError(msg)
        return open(target, "rb")

    def exists(self, storage_key: str) -> bool:
        return self._resolve_key(storage_key).is_file()

    def delete(self, storage_key: str) -> None:
        target = self._resolve_key(storage_key)
        if target.is_file():
            os.remove(target)
