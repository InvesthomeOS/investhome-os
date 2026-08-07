"""Eligibility rules for AI indexing (text sources only)."""

from __future__ import annotations

from pathlib import PurePosixPath

# Local copies of Drive special filenames / archive — avoid importing google_drive package
# (which pulls scanner/sync and historically caused import cycles with AI hooks).
ARCHIVE_CATEGORY = "10_ARCHIVE"
METADATA_FILENAME = "metadata.json"
README_FILENAME = "README.md"

# Full-text content categories (project info / catalogs / location / marketing / notes).
CONTENT_CATEGORIES: frozenset[str] = frozenset(
    {
        "00_PROJECT_INFO",
        "05_LOCATION",
        "07_CATALOG",
        "08_MARKETING",
        "03_FLOOR_PLANS",  # construction notes / plan text when extractable
        "04_UNIT_PLANS",
    }
)

# Legal / formal docs: metadata only (no full-text extraction).
LEGAL_CATEGORY = "09_DOCUMENTS"

TEXT_EXTENSIONS: frozenset[str] = frozenset({"md", "txt", "json", "docx", "pdf"})

# Soft cap for Drive downloads during indexing (bytes).
MAX_INDEX_DOWNLOAD_BYTES = 5_000_000


def extension_of(filename: str) -> str:
    return PurePosixPath(filename).suffix.lower().lstrip(".")


def is_special_filename(filename: str) -> bool:
    name = filename.lower().strip()
    return name in {README_FILENAME.lower(), METADATA_FILENAME.lower()}


def is_readme(filename: str) -> bool:
    return filename.lower().strip() == README_FILENAME.lower()


def is_metadata_file(filename: str) -> bool:
    return filename.lower().strip() == METADATA_FILENAME.lower()


def is_text_extension(filename: str) -> bool:
    return extension_of(filename) in TEXT_EXTENSIONS


def is_archive_category(category: str | None) -> bool:
    return category == ARCHIVE_CATEGORY


def is_legal_category(category: str | None) -> bool:
    return category == LEGAL_CATEGORY


def is_content_category(category: str | None) -> bool:
    if category is None:
        # Project-root / unknown folder: allow special files + text when linked
        return True
    return category in CONTENT_CATEGORIES


def asset_is_ai_index_candidate(
    *,
    filename: str,
    folder_category: str | None,
    sync_status: str | None = None,
) -> bool:
    """Whether a Media Library asset should enter the AI index pipeline."""
    if sync_status == "missing":
        return False
    if is_archive_category(folder_category):
        return False
    if is_special_filename(filename):
        return True
    if is_legal_category(folder_category):
        # Legal: index metadata shell only
        return True
    if not is_content_category(folder_category):
        # Brand / render / media binaries — skip unless text extension slips in
        return is_text_extension(filename)
    return is_text_extension(filename)
