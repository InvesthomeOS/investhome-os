"""Local filesystem storage provider for development and Docker."""

from __future__ import annotations

import os
import shutil
import unicodedata
from pathlib import Path
from typing import BinaryIO, NoReturn
from urllib.parse import unquote

from investhome_api.services.storage.base import StorageProviderBase

_INVALID_KEY = "Invalid storage key"
_MAX_DECODE_ROUNDS = 4


def _contained_in_root(target: Path, root: Path) -> bool:
    """True iff target is a descendant of root (the root directory itself is not a valid object path)."""
    try:
        return target.is_relative_to(root) and target != root
    except AttributeError:
        try:
            rel = target.relative_to(root)
        except ValueError:
            return False
        return bool(rel.parts)


def _is_absolute_key(value: str) -> bool:
    if not value:
        return False
    if value.startswith("/") or value.startswith("\\"):
        return True
    if len(value) >= 2 and value[0].isalpha() and value[1] == ":":
        return True
    try:
        return Path(value).is_absolute()
    except (OSError, ValueError):
        return True


def _decode_storage_key(storage_key: str) -> str:
    current = storage_key
    for _ in range(_MAX_DECODE_ROUNDS):
        decoded = unquote(current)
        if decoded == current:
            return current
        current = decoded
    raise ValueError(_INVALID_KEY)


class LocalStorageProvider(StorageProviderBase):
    def __init__(self, root_path: str) -> None:
        self._root = Path(root_path).resolve()
        self._root.mkdir(parents=True, exist_ok=True)

    def _reject(self) -> NoReturn:
        raise ValueError(_INVALID_KEY)

    def _resolve_key(self, storage_key: str) -> Path:
        if not isinstance(storage_key, str) or not storage_key.strip():
            self._reject()
        if "\x00" in storage_key:
            self._reject()
        try:
            decoded = _decode_storage_key(storage_key)
        except ValueError:
            self._reject()
        if "\x00" in decoded:
            self._reject()
        if _is_absolute_key(decoded) or _is_absolute_key(decoded.replace("\\", "/")):
            self._reject()

        unified = decoded.replace("\\", "/")
        parts = [part for part in unified.split("/") if part not in ("", ".")]
        if not parts:
            self._reject()
        for part in parts:
            collapsed = unicodedata.normalize("NFKC", part)
            if part == ".." or collapsed == ".." or collapsed in {".", "~"}:
                self._reject()
            if "\x00" in part:
                self._reject()
            if len(part) >= 2 and part[1] == ":":
                self._reject()

        try:
            root = self._root.resolve()
            target = root.joinpath(*parts).resolve(strict=False)
        except (OSError, RuntimeError, ValueError):
            self._reject()

        if not _contained_in_root(target, root):
            self._reject()
        return target

    def save(self, storage_key: str, stream: BinaryIO, *, content_length: int) -> None:
        del content_length
        target = self._resolve_key(storage_key)
        parent = target.parent
        if not _contained_in_root(parent, self._root.resolve()) and parent != self._root.resolve():
            self._reject()
        parent.mkdir(parents=True, exist_ok=True)
        with open(target, "wb") as dest:
            shutil.copyfileobj(stream, dest)

    def open(self, storage_key: str) -> BinaryIO:
        target = self._resolve_key(storage_key)
        if not target.is_file():
            raise FileNotFoundError("Stored file not found")
        return open(target, "rb")

    def exists(self, storage_key: str) -> bool:
        return self._resolve_key(storage_key).is_file()

    def delete(self, storage_key: str) -> None:
        target = self._resolve_key(storage_key)
        if target.is_file():
            os.remove(target)

    def get_local_path(self, storage_key: str) -> str:
        return str(self._resolve_key(storage_key))
