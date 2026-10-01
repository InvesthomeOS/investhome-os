"""Local storage path traversal hardening tests."""

from __future__ import annotations

import io
from pathlib import Path

import pytest

from investhome_api.services.storage.local import LocalStorageProvider


def _provider(tmp_path: Path) -> tuple[LocalStorageProvider, Path, Path]:
    root = tmp_path / "files"
    sibling = tmp_path / "files_evil"
    root.mkdir()
    sibling.mkdir()
    (sibling / "stolen.txt").write_text("outside", encoding="utf-8")
    return LocalStorageProvider(str(root)), root.resolve(), sibling.resolve()


def _assert_generic_error(exc: BaseException, root: Path, sibling: Path) -> None:
    message = str(exc)
    assert message == "Invalid storage key"
    assert str(root) not in message
    assert str(sibling) not in message
    assert "files_evil" not in message
    assert ".." not in message


def test_valid_key_accepted(tmp_path: Path) -> None:
    provider, root, _ = _provider(tmp_path)
    provider.save("2026/09/doc.pdf", io.BytesIO(b"ok"), content_length=2)
    assert provider.exists("2026/09/doc.pdf") is True
    with provider.open("2026/09/doc.pdf") as handle:
        assert handle.read() == b"ok"
    resolved = Path(provider.get_local_path("2026/09/doc.pdf"))
    assert resolved.is_relative_to(root)
    assert resolved.name == "doc.pdf"


def test_nested_valid_paths_accepted(tmp_path: Path) -> None:
    provider, root, _ = _provider(tmp_path)
    key = "a/b/c/nested.bin"
    provider.save(key, io.BytesIO(b"nested"), content_length=6)
    assert provider.exists(key) is True
    path = Path(provider.get_local_path(key))
    assert path.is_relative_to(root)
    assert path.read_bytes() == b"nested"
    provider.delete(key)
    assert provider.exists(key) is False


def test_dotdot_escape_rejected_on_all_ops(tmp_path: Path) -> None:
    provider, root, sibling = _provider(tmp_path)
    attacks = (
        "../files_evil/stolen.txt",
        "..\\files_evil\\stolen.txt",
        "ok/../../files_evil/stolen.txt",
        "ok/../files_evil/stolen.txt",
        "%2e%2e/files_evil/stolen.txt",
        "%2e%2e%2ffiles_evil%2fstolen.txt",
        "%252e%252e/files_evil/stolen.txt",
    )
    for key in attacks:
        with pytest.raises(ValueError) as exc:
            provider._resolve_key(key)
        _assert_generic_error(exc.value, root, sibling)
        with pytest.raises(ValueError):
            provider.save(key, io.BytesIO(b"x"), content_length=1)
        with pytest.raises(ValueError):
            provider.open(key)
        with pytest.raises(ValueError):
            provider.exists(key)
        with pytest.raises(ValueError):
            provider.delete(key)
        with pytest.raises(ValueError):
            provider.get_local_path(key)
    assert (sibling / "stolen.txt").read_text(encoding="utf-8") == "outside"


def test_absolute_path_rejected(tmp_path: Path) -> None:
    provider, root, sibling = _provider(tmp_path)
    attacks = (
        str(sibling / "stolen.txt"),
        str(sibling / "stolen.txt").replace("\\", "/"),
        "/etc/passwd",
        "C:/Windows/System32/config/SAM",
        "\\\\server\\share\\file",
    )
    for key in attacks:
        with pytest.raises(ValueError) as exc:
            provider._resolve_key(key)
        _assert_generic_error(exc.value, root, sibling)


def test_root_prefix_sibling_attack_rejected(tmp_path: Path) -> None:
    provider, root, sibling = _provider(tmp_path)
    # Demonstrates the startswith(str(root)) bypass: files vs files_evil
    assert str(sibling).startswith(str(root))
    with pytest.raises(ValueError) as exc:
        provider._resolve_key("../files_evil/stolen.txt")
    _assert_generic_error(exc.value, root, sibling)
    with pytest.raises(ValueError):
        provider.open(str(sibling / "stolen.txt"))
    assert provider.exists("missing-inside.txt") is False
    with pytest.raises(ValueError):
        provider.exists("../files_evil/stolen.txt")


def test_symlink_escape_rejected_where_applicable(tmp_path: Path) -> None:
    provider, root, sibling = _provider(tmp_path)
    link = root / "escape"
    try:
        link.symlink_to(sibling / "stolen.txt")
    except OSError:
        pytest.skip("symlink creation is not permitted in this environment")
    with pytest.raises(ValueError) as exc:
        provider.open("escape")
    _assert_generic_error(exc.value, root, sibling)
    with pytest.raises(ValueError):
        provider.get_local_path("escape")
    with pytest.raises(ValueError):
        provider.exists("escape")
    with pytest.raises(ValueError):
        provider.delete("escape")


def test_symlink_inside_root_still_readable(tmp_path: Path) -> None:
    provider, root, _ = _provider(tmp_path)
    nested = root / "nested"
    nested.mkdir()
    target = nested / "ok.txt"
    target.write_text("inside", encoding="utf-8")
    alias = root / "alias.txt"
    try:
        alias.symlink_to(target)
    except OSError:
        pytest.skip("symlink creation is not permitted in this environment")
    with provider.open("alias.txt") as handle:
        assert handle.read() == b"inside"


def test_empty_and_root_keys_rejected(tmp_path: Path) -> None:
    provider, root, sibling = _provider(tmp_path)
    for key in ("", " ", ".", "/", "..", "./"):
        with pytest.raises(ValueError) as exc:
            provider._resolve_key(key)
        _assert_generic_error(exc.value, root, sibling)
