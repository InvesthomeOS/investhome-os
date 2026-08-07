"""Google Drive folder category constants for InvestHome project trees."""

from __future__ import annotations

STANDARD_FOLDER_CATEGORIES: frozenset[str] = frozenset(
    {
        "00_PROJECT_INFO",
        "01_BRAND",
        "02_RENDER",
        "03_FLOOR_PLANS",
        "04_UNIT_PLANS",
        "05_LOCATION",
        "06_MEDIA",
        "07_CATALOG",
        "08_MARKETING",
        "09_DOCUMENTS",
        "10_ARCHIVE",
    }
)

ARCHIVE_CATEGORY = "10_ARCHIVE"

# Google Workspace MIME types — indexed as references only (no binary download during scan).
GOOGLE_NATIVE_MIMES: frozenset[str] = frozenset(
    {
        "application/vnd.google-apps.document",
        "application/vnd.google-apps.spreadsheet",
        "application/vnd.google-apps.presentation",
        "application/vnd.google-apps.drawing",
        "application/vnd.google-apps.form",
        "application/vnd.google-apps.site",
        "application/vnd.google-apps.map",
    }
)

DRIVE_FOLDER_MIME = "application/vnd.google-apps.folder"
METADATA_FILENAME = "metadata.json"
README_FILENAME = "README.md"


def resolve_folder_category(folder_name: str) -> str | None:
    """Map a Drive folder name to a standard category, or None if unknown."""
    name = folder_name.strip()
    if name in STANDARD_FOLDER_CATEGORIES:
        return name
    # Allow prefix match e.g. "02_RENDER - Exterior"
    for category in STANDARD_FOLDER_CATEGORIES:
        if name.startswith(category):
            return category
    return None
