"""CreativeReferenceLibraryV1 — official DESIGN_REFERENCES from Media Library / Drive.

Does not invent references. Does not treat OS experiment PNGs as design references.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from uuid import UUID, uuid4, uuid5, NAMESPACE_URL

from sqlalchemy import select
from sqlalchemy.orm import Session

from investhome_api.models.creative_studio_media import (
    CreativeStudioMediaAsset,
    CreativeStudioMediaFolder,
    MediaAssetSourceType,
    MediaAssetSyncStatus,
)
from investhome_api.services.creative_studio_media_service import IMAGE_EXTENSIONS
from investhome_api.services.google_drive.categories import DRIVE_FOLDER_MIME
from investhome_api.services.google_drive.errors import GoogleDriveError
from investhome_api.services.google_drive.provider import (
    GoogleDriveProviderProtocol,
    get_google_drive_provider,
)

CANONICAL_FOLDER_NAME = "DESIGN_REFERENCES"
CANONICAL_FOLDER_ALIASES = ("DESIGN_REFERENCES", "DESIGN_REFERENCE")
WRONG_PREFIX_NAMES = ("12_DESIGN_REFERENCE", "12_DESIGN_REFERENCES")
COMPANY_HINTS = ("investhome", "investhome os", "media library")
SHORTCUT_MIME = "application/vnd.google-apps.shortcut"
IMAGE_MIMES = ("image/jpeg", "image/jpg", "image/png", "image/webp", "image/gif", "image/tiff")
MAX_DRIVE_WALK = 250
PREVIOUS_PROJECT_SEARCH_ROOT_ID = "1opwsQlV8kehhbOscXpPAILWH1m_cc7Le"
PREVIOUS_PROJECT_SEARCH_ROOT_NAME = "Investhome OS"
STORAGE_PROVIDER_GOOGLE_DRIVE = "google_drive"


class DesignReferencesNotFound(RuntimeError):
    """DESIGN_REFERENCES could not be located. Callers must STOP."""


def _norm(name: str | None) -> str:
    return " ".join((name or "").strip().split()).casefold()


def is_canonical_reference_folder_name(name: str | None) -> bool:
    """Accept DESIGN_REFERENCES or the live Media Library folder DESIGN_REFERENCE.

    Still rejects numbered prefixes such as 12_DESIGN_REFERENCE.
    """
    if is_wrong_prefix_name(name):
        return False
    return _norm(name) in {_norm(alias) for alias in CANONICAL_FOLDER_ALIASES}


def is_wrong_prefix_name(name: str | None) -> bool:
    return _norm(name) in {_norm(n) for n in WRONG_PREFIX_NAMES}


def _folder_path(db: Session, folder: CreativeStudioMediaFolder | None) -> list[str]:
    names: list[str] = []
    current = folder
    seen: set[str] = set()
    while current is not None and str(current.id) not in seen:
        seen.add(str(current.id))
        names.append(current.name)
        current = db.get(CreativeStudioMediaFolder, current.parent_id) if current.parent_id else None
    names.reverse()
    return names


def _media_library_search(db: Session) -> dict[str, Any]:
    folders = list(
        db.scalars(
            select(CreativeStudioMediaFolder).where(CreativeStudioMediaFolder.archived_at.is_(None))
        )
    )
    exact = [f for f in folders if is_canonical_reference_folder_name(f.name)]
    wrong = [f for f in folders if is_wrong_prefix_name(f.name)]
    companyish = [f for f in folders if _norm(f.name) in COMPANY_HINTS]
    return {
        "folder_count_scanned": len(folders),
        "exact_matches": [
            {
                "media_folder_id": str(f.id),
                "name": f.name,
                "path": _folder_path(db, f),
                "drive_folder_id": f.external_folder_id,
                "linked_project_id": str(f.linked_project_id) if f.linked_project_id else None,
                "parent_id": str(f.parent_id) if f.parent_id else None,
            }
            for f in exact
        ],
        "wrong_prefix_matches": [{"name": f.name, "id": str(f.id)} for f in wrong],
        "company_named_folders": [{"name": f.name, "id": str(f.id)} for f in companyish],
    }


def _drive_walk_search(provider: GoogleDriveProviderProtocol) -> dict[str, Any]:
    log: dict[str, Any] = {
        "root_folder_id": None,
        "root_name": None,
        "visited": 0,
        "exact_matches": [],
        "wrong_prefix_matches": [],
        "error": None,
    }
    try:
        root_id = provider.root_folder_id
        root = provider.get_file(root_id)
        log["root_folder_id"] = root_id
        log["root_name"] = root.name
    except Exception as exc:
        log["error"] = str(exc)
        return log

    queue: list[tuple[str, str, int]] = [(root_id, root.name, 0)]
    seen: set[str] = {root_id}
    while queue and log["visited"] < MAX_DRIVE_WALK:
        folder_id, path, depth = queue.pop(0)
        log["visited"] += 1
        try:
            children = list(provider.list_children(folder_id))
        except GoogleDriveError as exc:
            log.setdefault("walk_errors", []).append({"folder_id": folder_id, "error": str(exc)})
            continue
        for child in children:
            if not child.is_folder:
                continue
            child_path = f"{path}/{child.name}"
            if is_canonical_reference_folder_name(child.name):
                log["exact_matches"].append(
                    {
                        "drive_folder_id": child.id,
                        "name": child.name,
                        "path": child_path,
                        "parent_ids": list(child.parent_ids),
                    }
                )
            if is_wrong_prefix_name(child.name):
                log["wrong_prefix_matches"].append({"drive_folder_id": child.id, "name": child.name, "path": child_path})
            if child.id not in seen and depth < 8:
                seen.add(child.id)
                queue.append((child.id, child_path, depth + 1))
    return log


def _drive_files_list(
    provider: GoogleDriveProviderProtocol,
    q: str,
    *,
    extra: dict[str, Any] | None = None,
    page_size: int = 100,
) -> tuple[list[dict[str, Any]], str | None]:
    build = getattr(provider, "_build_service", None)
    if not callable(build):
        return [], "provider_cannot_query"
    service = build()
    token: str | None = None
    out: list[dict[str, Any]] = []
    params: dict[str, Any] = {
        "q": q,
        "spaces": "drive",
        "fields": "nextPageToken, files(id,name,mimeType,parents,webViewLink,shortcutDetails)",
        "pageSize": min(page_size, 1000),
        "supportsAllDrives": True,
        "includeItemsFromAllDrives": True,
    }
    if extra:
        params.update(extra)
    try:
        while True:
            if token:
                params["pageToken"] = token
            elif "pageToken" in params:
                params.pop("pageToken")
            response = service.files().list(**params).execute()
            for raw in response.get("files") or []:
                shortcut = dict(raw.get("shortcutDetails") or {})
                out.append(
                    {
                        "drive_folder_id": shortcut.get("targetId") or raw.get("id"),
                        "name": raw.get("name"),
                        "parents": raw.get("parents") or [],
                        "web_view_link": raw.get("webViewLink"),
                        "mime_type": raw.get("mimeType"),
                        "shortcut_target_id": shortcut.get("targetId"),
                    }
                )
            token = response.get("nextPageToken")
            if not token:
                break
    except Exception as exc:
        return out, str(exc)
    return out, None


def _drive_name_query(provider: GoogleDriveProviderProtocol) -> dict[str, Any]:
    """Exact Drive name query. Does not search 12_ prefixes as the canonical target."""
    result: dict[str, Any] = {"query": list(CANONICAL_FOLDER_ALIASES), "matches": [], "error": None}
    seen: set[str] = set()
    for alias in CANONICAL_FOLDER_ALIASES:
        matches, error = _drive_files_list(
            provider,
            f"name = '{alias}' and mimeType = '{DRIVE_FOLDER_MIME}' and trashed = false",
        )
        if error and result["error"] is None:
            result["error"] = error
        for item in matches:
            if is_wrong_prefix_name(str(item.get("name"))):
                continue
            fid = str(item.get("drive_folder_id") or "")
            if fid and fid not in seen and is_canonical_reference_folder_name(str(item.get("name"))):
                result["matches"].append(item)
                seen.add(fid)
    return result


def _drive_about(provider: GoogleDriveProviderProtocol) -> dict[str, Any]:
    build = getattr(provider, "_build_service", None)
    if not callable(build):
        return {"error": "provider_cannot_query_about"}
    try:
        about = build().about().get(fields="user(displayName,emailAddress,permissionId)").execute()
        user = dict(about.get("user") or {})
        return {
            "email": user.get("emailAddress"),
            "display_name": user.get("displayName"),
            "permission_id": user.get("permissionId"),
        }
    except Exception as exc:
        return {"error": str(exc)}


def _list_drive_folders(provider: GoogleDriveProviderProtocol, *, extra: dict[str, Any] | None = None) -> tuple[list[dict[str, Any]], str | None]:
    return _drive_files_list(
        provider,
        f"mimeType = '{DRIVE_FOLDER_MIME}' and trashed = false",
        extra=extra,
    )


def _shared_with_me_folders(provider: GoogleDriveProviderProtocol) -> tuple[list[dict[str, Any]], str | None]:
    return _drive_files_list(
        provider,
        f"sharedWithMe = true and mimeType = '{DRIVE_FOLDER_MIME}' and trashed = false",
    )


def _list_shared_drives(provider: GoogleDriveProviderProtocol) -> tuple[list[dict[str, str]], str | None]:
    build = getattr(provider, "_build_service", None)
    if not callable(build):
        return [], "provider_cannot_query"
    try:
        token: str | None = None
        out: list[dict[str, str]] = []
        service = build()
        while True:
            response = service.drives().list(pageSize=100, pageToken=token, fields="nextPageToken, drives(id,name)").execute()
            for raw in response.get("drives") or []:
                out.append({"id": str(raw.get("id")), "name": str(raw.get("name") or "")})
            token = response.get("nextPageToken")
            if not token:
                break
        return out, None
    except Exception as exc:
        return [], str(exc)


def _is_media_library_name(name: str | None) -> bool:
    return _norm(name) == "media library"


def _is_company_investhome_name(name: str | None) -> bool:
    return _norm(name) in {"investhome", "investhome os"}


def _walk_expected_media_library_tree(
    provider: GoogleDriveProviderProtocol,
    folders: list[dict[str, Any]],
) -> dict[str, Any]:
    """Media Library → Investhome → DESIGN_REFERENCES, independent of project Drive root."""
    media_roots = [item for item in folders if _is_media_library_name(str(item.get("name")))]
    investhome_nodes = [item for item in folders if _is_company_investhome_name(str(item.get("name")))]
    exact: list[dict[str, Any]] = []
    inspected: list[dict[str, Any]] = []
    for root in media_roots:
        root_id = str(root.get("drive_folder_id") or "")
        if not root_id:
            continue
        try:
            children = list(provider.list_children(root_id))
        except Exception as exc:
            inspected.append({"id": root_id, "name": root.get("name"), "error": str(exc)})
            continue
        company = [child for child in children if child.is_folder and _is_company_investhome_name(child.name)]
        inspected.append(
            {
                "id": root_id,
                "name": root.get("name"),
                "child_folder_names": [child.name for child in children if child.is_folder][:40],
            }
        )
        for node in company:
            try:
                sub = list(provider.list_children(node.id))
            except Exception as exc:
                inspected.append({"id": node.id, "name": node.name, "error": str(exc)})
                continue
            inspected.append(
                {
                    "id": node.id,
                    "name": node.name,
                    "parent": root_id,
                    "child_folder_names": [child.name for child in sub if child.is_folder][:40],
                }
            )
            for child in sub:
                if child.is_folder and is_canonical_reference_folder_name(child.name):
                    exact.append(
                        {
                            "drive_folder_id": child.id,
                            "name": child.name,
                            "parents": list(child.parent_ids),
                            "path": f"{root.get('name')}/{node.name}/{child.name}",
                            "source": "media_library_tree",
                        }
                    )
    for node in investhome_nodes:
        node_id = str(node.get("drive_folder_id") or "")
        if not node_id or any(item.get("id") == node_id for item in inspected):
            continue
        try:
            sub = list(provider.list_children(node_id))
        except Exception as exc:
            inspected.append({"id": node_id, "name": node.get("name"), "error": str(exc)})
            continue
        inspected.append(
            {
                "id": node_id,
                "name": node.get("name"),
                "child_folder_names": [child.name for child in sub if child.is_folder][:40],
            }
        )
        for child in sub:
            if child.is_folder and is_canonical_reference_folder_name(child.name):
                exact.append(
                    {
                        "drive_folder_id": child.id,
                        "name": child.name,
                        "parents": list(child.parent_ids),
                        "path": f"{node.get('name')}/{child.name}",
                        "source": "investhome_tree",
                    }
                )
    return {
        "media_library_roots": [{"id": item.get("drive_folder_id"), "name": item.get("name")} for item in media_roots],
        "investhome_nodes": [{"id": item.get("drive_folder_id"), "name": item.get("name")} for item in investhome_nodes],
        "inspected": inspected,
        "exact_matches": exact,
    }


def drive_folder_hierarchy(provider: GoogleDriveProviderProtocol, folder_id: str) -> list[dict[str, str]]:
    chain: list[dict[str, str]] = []
    current = folder_id
    seen: set[str] = set()
    while current and current not in seen:
        seen.add(current)
        try:
            meta = provider.get_file(current)
        except Exception:
            break
        chain.append({"id": meta.id, "name": meta.name})
        if not meta.parent_ids:
            break
        current = meta.parent_ids[0]
        if len(chain) >= 12:
            break
    chain.reverse()
    return chain


def _drive_full_scope_search(provider: GoogleDriveProviderProtocol) -> dict[str, Any]:
    """Search the entire Drive corpus visible to the application credential."""
    about = _drive_about(provider)
    user_folders: list[dict[str, Any]] = []
    all_drive_folders: list[dict[str, Any]] = []
    shared: list[dict[str, Any]] = []
    shared_drives: list[dict[str, str]] = []
    shared_drive_folders: list[dict[str, Any]] = []
    shortcuts: list[dict[str, Any]] = []
    targeted: dict[str, Any] = {}
    errors: list[str] = []
    user_folders, err = _list_drive_folders(provider, extra={"corpora": "user"})
    if err:
        errors.append(f"user_corpus:{err}")
    all_drive_folders, err = _list_drive_folders(provider, extra={"corpora": "allDrives"})
    if err:
        errors.append(f"allDrives:{err}")
    shared, err = _shared_with_me_folders(provider)
    if err:
        errors.append(f"sharedWithMe:{err}")
    shared_drives, err = _list_shared_drives(provider)
    if err:
        errors.append(f"drives.list:{err}")
    for drive in shared_drives:
        rows, drive_err = _list_drive_folders(
            provider,
            extra={"corpora": "drive", "driveId": drive["id"]},
        )
        shared_drive_folders.extend(rows)
        if drive_err:
            errors.append(f"shared_drive:{drive['id']}:{drive_err}")
    shortcuts, err = _drive_files_list(
        provider,
        f"mimeType = '{SHORTCUT_MIME}' and name contains 'DESIGN' and trashed = false",
    )
    if err:
        errors.append(f"shortcuts:{err}")
    for label, query in (
        ("media_library", f"name = 'Media Library' and mimeType = '{DRIVE_FOLDER_MIME}' and trashed = false"),
        ("investhome", f"name = 'Investhome' and mimeType = '{DRIVE_FOLDER_MIME}' and trashed = false"),
        ("design_contains", "name contains 'DESIGN' and mimeType = 'application/vnd.google-apps.folder' and trashed = false"),
        ("reference_contains", "name contains 'REFERENCE' and mimeType = 'application/vnd.google-apps.folder' and trashed = false"),
    ):
        rows, query_err = _drive_files_list(provider, query)
        targeted[label] = {"matches": rows, "error": query_err}
        if query_err:
            errors.append(f"{label}:{query_err}")
    combined: dict[str, dict[str, Any]] = {}
    for item in (
        user_folders
        + all_drive_folders
        + shared
        + shared_drive_folders
        + shortcuts
        + [row for pack in targeted.values() for row in list(pack.get("matches") or [])]
    ):
        fid = str(item.get("drive_folder_id") or "")
        if fid:
            combined[fid] = item
    tree = _walk_expected_media_library_tree(provider, list(combined.values()))
    my_drive_inventory: dict[str, Any] = {"error": None}
    try:
        project_root_id = provider.root_folder_id
        project_root = provider.get_file(project_root_id)
        parent_ids = list(project_root.parent_ids)
        if parent_ids:
            my_drive_id = parent_ids[0]
            my_drive_meta = provider.get_file(my_drive_id)
            siblings = [
                {"id": child.id, "name": child.name}
                for child in provider.list_children(my_drive_id)
                if child.is_folder
            ]
            my_drive_inventory = {
                "id": my_drive_meta.id,
                "name": my_drive_meta.name,
                "child_folders": siblings,
                "child_folder_count": len(siblings),
            }
        else:
            my_drive_inventory = {"id": project_root_id, "name": project_root.name, "child_folders": [], "note": "no_parent"}
    except Exception as exc:
        my_drive_inventory = {"error": str(exc)}
    exact = [item for item in combined.values() if is_canonical_reference_folder_name(str(item.get("name")))]
    for hit in tree.get("exact_matches") or []:
        fid = str(hit.get("drive_folder_id") or "")
        if fid and not any(str(item.get("drive_folder_id")) == fid for item in exact):
            exact.append(hit)
    wrong = [item for item in combined.values() if is_wrong_prefix_name(str(item.get("name")))]
    companyish = [item for item in combined.values() if _norm(str(item.get("name"))) in COMPANY_HINTS]
    return {
        "connected_account": about,
        "previous_search_root": {
            "id": PREVIOUS_PROJECT_SEARCH_ROOT_ID,
            "name": PREVIOUS_PROJECT_SEARCH_ROOT_NAME,
            "note": "Investhome OS project Drive root — not the company Media Library",
        },
        "correct_search_root": "application credential full Drive scope (My Drive + allDrives + sharedWithMe + shared drives + Media Library tree)",
        "user_folder_count": len(user_folders),
        "all_drives_folder_count": len(all_drive_folders),
        "shared_with_me_folder_count": len(shared),
        "shared_drive_count": len(shared_drives),
        "shared_drives": shared_drives,
        "shared_drive_folder_count": len(shared_drive_folders),
        "unique_folder_count": len(combined),
        "targeted_queries": {key: {"count": len(pack.get("matches") or []), "error": pack.get("error")} for key, pack in targeted.items()},
        "media_library_tree": tree,
        "my_drive_inventory": my_drive_inventory,
        "exact_matches": exact,
        "wrong_prefix_matches": wrong,
        "company_named_folders": companyish,
        "errors": errors,
    }


def _company_id(db: Session) -> UUID | None:
    value = db.scalars(
        select(CreativeStudioMediaFolder.company_id).where(CreativeStudioMediaFolder.company_id.isnot(None)).limit(1)
    ).first()
    return value


def _upsert_media_folder(
    db: Session,
    *,
    name: str,
    drive_folder_id: str,
    drive_parent_id: str | None,
    parent_media_id: UUID | None,
    company_id: UUID | None,
) -> CreativeStudioMediaFolder:
    existing = db.scalar(
        select(CreativeStudioMediaFolder).where(CreativeStudioMediaFolder.external_folder_id == drive_folder_id)
    )
    if existing is not None:
        existing.name = name[:255]
        if parent_media_id is not None:
            existing.parent_id = parent_media_id
        if drive_parent_id is not None:
            existing.external_parent_id = drive_parent_id
        if company_id is not None and existing.company_id is None:
            existing.company_id = company_id
        existing.archived_at = None
        existing.updated_at = datetime.now(UTC)
        db.flush()
        return existing
    folder = CreativeStudioMediaFolder(
        id=uuid4(),
        name=name[:255],
        parent_id=parent_media_id,
        company_id=company_id,
        external_folder_id=drive_folder_id,
        external_parent_id=drive_parent_id,
        linked_project_id=None,
    )
    db.add(folder)
    db.flush()
    return folder


def index_design_references_folder(
    db: Session,
    location: dict[str, Any],
    *,
    provider: GoogleDriveProviderProtocol | None = None,
) -> dict[str, Any]:
    """Map DESIGN_REFERENCES into Media Library without duplicating Drive bytes."""
    folder = dict(location.get("folder") or {})
    drive_id = str(folder.get("drive_folder_id") or "")
    if not drive_id:
        return {"indexed": False, "reason": "no_drive_folder_id"}
    drive = provider or get_google_drive_provider()
    hierarchy = drive_folder_hierarchy(drive, drive_id)
    company_id = _company_id(db)
    parent_media_id: UUID | None = None
    mapped: list[dict[str, Any]] = []
    for i, node in enumerate(hierarchy):
        parent_drive = hierarchy[i - 1]["id"] if i else None
        media = _upsert_media_folder(
            db,
            name=node["name"],
            drive_folder_id=node["id"],
            drive_parent_id=parent_drive,
            parent_media_id=parent_media_id,
            company_id=company_id,
        )
        parent_media_id = media.id
        mapped.append({"drive_folder_id": node["id"], "name": node["name"], "media_folder_id": str(media.id)})
    target = mapped[-1] if mapped else None
    created_assets = 0
    skipped: list[dict[str, str]] = []
    if target:
        try:
            children = list(drive.list_children(drive_id))
        except GoogleDriveError as exc:
            return {
                "indexed": False,
                "reason": "credential_cannot_read",
                "error": str(exc),
                "hierarchy": hierarchy,
                "mapped_folders": mapped,
                "duplicated_files": False,
                "source_of_truth": "google_drive",
            }
        for child in children:
            if child.is_folder:
                continue
            mime = (child.mime_type or "").casefold()
            ext = child.name.rsplit(".", 1)[-1].casefold() if "." in child.name else ""
            if mime not in IMAGE_MIMES and ext not in IMAGE_EXTENSIONS:
                skipped.append({"filename": child.name, "reason": f"not_a_readable_visual:{mime or ext}"})
                continue
            existing = db.scalar(
                select(CreativeStudioMediaAsset).where(CreativeStudioMediaAsset.external_file_id == child.id)
            )
            if existing is not None:
                if existing.linked_project_id is None:
                    existing.folder_id = UUID(str(target["media_folder_id"]))
                continue
            db.add(
                CreativeStudioMediaAsset(
                    id=uuid4(),
                    filename=child.name[:255],
                    content_type=(child.mime_type or "application/octet-stream")[:120],
                    file_size=child.size or 0,
                    storage_provider=STORAGE_PROVIDER_GOOGLE_DRIVE,
                    storage_key=f"gdrive:{child.id}",
                    folder_id=UUID(str(target["media_folder_id"])),
                    company_id=company_id,
                    linked_project_id=None,
                    source_type=MediaAssetSourceType.GOOGLE_DRIVE.value,
                    external_file_id=child.id,
                    external_parent_id=drive_id,
                    external_modified_at=child.modified_at,
                    external_checksum=child.md5_checksum,
                    sync_status=MediaAssetSyncStatus.ACTIVE.value,
                    web_view_link=child.web_view_link,
                    external_thumbnail_link=child.thumbnail_link,
                )
            )
            created_assets += 1
        db.flush()
    return {
        "indexed": True,
        "hierarchy": hierarchy,
        "mapped_folders": mapped,
        "assets_created": created_assets,
        "skipped": skipped,
        "duplicated_files": False,
        "source_of_truth": "google_drive",
    }


def locate_design_references(
    db: Session,
    *,
    provider: GoogleDriveProviderProtocol | None = None,
) -> dict[str, Any]:
    """Resolve Media Library → Investhome → DESIGN_REFERENCES across full Drive scope."""
    media = _media_library_search(db)
    drive_provider = provider or get_google_drive_provider()
    walk = _drive_walk_search(drive_provider)
    named = _drive_name_query(drive_provider)
    full = _drive_full_scope_search(drive_provider)
    chosen: dict[str, Any] | None = None
    if media["exact_matches"]:
        chosen = {"source": "media_library", **media["exact_matches"][0]}
    elif full.get("exact_matches"):
        hit = dict(full["exact_matches"][0])
        hit["hierarchy"] = drive_folder_hierarchy(drive_provider, str(hit.get("drive_folder_id")))
        chosen = {"source": "google_drive_full_scope", **hit}
    elif walk.get("exact_matches"):
        chosen = {"source": "google_drive_project_walk", **walk["exact_matches"][0]}
    elif named.get("matches"):
        chosen = {"source": "google_drive_name_query", **named["matches"][0]}

    found = chosen is not None
    if chosen and not chosen.get("hierarchy") and chosen.get("drive_folder_id"):
        try:
            chosen["hierarchy"] = drive_folder_hierarchy(drive_provider, str(chosen.get("drive_folder_id")))
        except Exception:
            chosen["hierarchy"] = chosen.get("path")
    parent_folder_id = None
    hierarchy = (chosen or {}).get("hierarchy") if isinstance((chosen or {}).get("hierarchy"), list) else None
    if isinstance(hierarchy, list) and len(hierarchy) >= 2 and isinstance(hierarchy[-2], dict):
        parent_folder_id = hierarchy[-2].get("id")
    elif chosen:
        parent_folder_id = chosen.get("parent_id") or (list(chosen.get("parents") or [None]) + [None])[0]
    account = dict(full.get("connected_account") or {})
    tree = dict(full.get("media_library_tree") or {})
    my_drive = dict(full.get("my_drive_inventory") or {})
    reason = None
    if not found:
        reason = (
            "DESIGN_REFERENCES is not visible to the application Google Drive credential "
            f"{account.get('email') or '(unknown)'} ({account.get('display_name') or ''}). "
            f"Full connected scope searched: {full.get('unique_folder_count')} unique folders, "
            f"{full.get('shared_with_me_folder_count')} sharedWithMe folders, "
            f"{full.get('shared_drive_count')} shared drives, "
            f"Media Library roots visible: {len(tree.get('media_library_roots') or [])}, "
            f"Investhome company folders visible: {len(tree.get('investhome_nodes') or [])}, "
            "0 matching DESIGN_REFERENCES. "
            f"Previous search root was project folder {PREVIOUS_PROJECT_SEARCH_ROOT_NAME} "
            f"({PREVIOUS_PROJECT_SEARCH_ROOT_ID}). "
            "Correct search root is the full application credential Drive corpus "
            "(My Drive + allDrives + sharedWithMe + shared drives + Media Library → Investhome tree), "
            "not the Investhome OS project root. "
            "Media Library DB sync currently maps only The Temple project Drive folder. "
            f"Application My Drive root visible as {my_drive.get('name')} "
            f"({my_drive.get('id')}) with child folders: "
            f"{[item.get('name') for item in list(my_drive.get('child_folders') or [])]}. "
            "Credential/root/sync mismatch: the company Media Library → Investhome → DESIGN_REFERENCES "
            "tree is not readable by this OAuth user; mapping cannot proceed until that folder is "
            "visible to this same Drive integration (share, do not move)."
        )
        if full.get("errors"):
            reason += f" Drive query errors: {full.get('errors')}"
    return {
        "schema": "DesignReferenceLocationV1",
        "canonical_folder_name": CANONICAL_FOLDER_NAME,
        "found": found,
        "folder": chosen,
        "drive_folder_id": (chosen or {}).get("drive_folder_id"),
        "parent_folder_id": parent_folder_id,
        "parent_hierarchy": (chosen or {}).get("hierarchy") or (chosen or {}).get("path"),
        "media_library_mapping": chosen if found and chosen.get("media_folder_id") else None,
        "media_library_search": media,
        "drive_walk": walk,
        "drive_name_query": named,
        "drive_full_scope": full,
        "previous_search_root": full.get("previous_search_root"),
        "correct_search_root": full.get("correct_search_root"),
        "wrong_prefix_ignored": True,
        "fail_fast": not found,
        "reason": reason,
    }


def attach_media_library_mapping(db: Session, location: dict[str, Any]) -> dict[str, Any]:
    """Refresh Media Library ids after Drive → Media Library indexing. Does not re-search Drive."""
    media = _media_library_search(db)
    location["media_library_search"] = media
    if media["exact_matches"]:
        hit = media["exact_matches"][0]
        folder = dict(location.get("folder") or {})
        folder.update(hit)
        location["folder"] = folder
        location["media_library_mapping"] = hit
        location["found"] = True
        location["drive_folder_id"] = hit.get("drive_folder_id") or location.get("drive_folder_id")
        location["fail_fast"] = False
    return location


def classify_reference_filename(filename: str, *, width: int | None = None, height: int | None = None) -> dict[str, Any]:
    name = (filename or "").casefold()
    project_affinity = None
    if "temple" in name or "tmp_001" in name or "dc_tmp" in name:
        project_affinity = "THE_TEMPLE"
    elif "uniloft" in name or "uni-loft" in name or "uni_loft" in name:
        project_affinity = "UNILOFT"
    brand_affinity = "INVESHOME" if "investhome" in name or name.startswith("ih_") else None
    content = "campaign_graphic"
    if any(k in name for k in ("poster", "baski", "print")):
        content = "poster"
    elif any(k in name for k in ("story", "reel", "social")):
        content = "social_media_creative"
    elif any(k in name for k in ("catalog", "catalogue", "presentation")):
        content = "premium_presentation"
    elif any(k in name for k in ("invest", "yatirim", "campaign")):
        content = "investment_advertisement"
    orientation = "unknown"
    aspect = None
    if width and height:
        orientation = "portrait" if height > width else "landscape" if width > height else "square"
        aspect = round(width / max(height, 1), 3)
    design_category = "editorial" if "editorial" in name else "campaign"
    return {
        "project_affinity": project_affinity,
        "brand_affinity": brand_affinity,
        "content_category": content,
        "design_category": design_category,
        "orientation": orientation,
        "aspect_ratio": aspect,
    }


def _is_readable_image(asset: CreativeStudioMediaAsset) -> tuple[bool, str | None]:
    if asset.archived_at is not None:
        return False, "archived"
    mime = (asset.content_type or "").casefold()
    ext = (asset.filename or "").rsplit(".", 1)[-1].casefold() if "." in (asset.filename or "") else ""
    if mime in IMAGE_MIMES or ext in IMAGE_EXTENSIONS:
        return True, None
    if mime.startswith("image/"):
        return True, None
    return False, f"not_a_readable_visual:{mime or ext or 'unknown'}"


def collect_folder_assets(db: Session, folder_id: UUID) -> tuple[list[CreativeStudioMediaAsset], list[CreativeStudioMediaAsset]]:
    ids = [folder_id]
    queue = [folder_id]
    while queue:
        current = queue.pop()
        children = list(
            db.scalars(
                select(CreativeStudioMediaFolder.id).where(
                    CreativeStudioMediaFolder.parent_id == current,
                    CreativeStudioMediaFolder.archived_at.is_(None),
                )
            )
        )
        for child in children:
            ids.append(child)
            queue.append(child)
    assets = list(
        db.scalars(
            select(CreativeStudioMediaAsset).where(
                CreativeStudioMediaAsset.folder_id.in_(ids),
                CreativeStudioMediaAsset.archived_at.is_(None),
            )
        )
    )
    readable: list[CreativeStudioMediaAsset] = []
    skipped: list[CreativeStudioMediaAsset] = []
    for asset in assets:
        ok, _reason = _is_readable_image(asset)
        (readable if ok else skipped).append(asset)
    return readable, skipped


def build_reference_library(db: Session, location: dict[str, Any]) -> dict[str, Any]:
    if not location.get("found"):
        raise DesignReferencesNotFound(location.get("reason") or "DESIGN_REFERENCES not found")
    folder_info = dict(location.get("folder") or {})
    media_id = folder_info.get("media_folder_id")
    entries: list[dict[str, Any]] = []
    skipped: list[dict[str, Any]] = []
    if media_id:
        readable, skipped_assets = collect_folder_assets(db, UUID(str(media_id)))
        for asset in readable:
            cls = classify_reference_filename(asset.filename, width=asset.width, height=asset.height)
            entries.append(
                {
                    "reference_id": str(uuid5(NAMESPACE_URL, f"investhome:design-ref:{asset.id}")),
                    "asset_id": str(asset.id),
                    "filename": asset.filename,
                    "drive_source": {
                        "external_file_id": asset.external_file_id,
                        "web_view_link": asset.web_view_link,
                        "source_type": asset.source_type,
                    },
                    "visual_analysis_status": "PENDING",
                    "reference_quality_status": "UNSCORED",
                    **cls,
                }
            )
        for asset in skipped_assets:
            _ok, reason = _is_readable_image(asset)
            skipped.append({"asset_id": str(asset.id), "filename": asset.filename, "reason": reason})
    return {
        "schema": "CreativeReferenceLibraryV1",
        "library_id": str(uuid5(NAMESPACE_URL, f"investhome:design-ref-library:{CANONICAL_FOLDER_NAME}")),
        "folder": folder_info,
        "file_count": len(entries) + len(skipped),
        "image_count": len(entries),
        "skipped_count": len(skipped),
        "skipped": skipped,
        "references": entries,
        "status": "READY" if entries else "EMPTY_FOLDER",
    }


def retrieve_references(
    library: dict[str, Any],
    *,
    purpose: str = "premium_project_campaign",
    format_aspect: str = "4:5",
    limit: int = 8,
) -> list[dict[str, Any]]:
    """CreativeReferenceRetrieverV1 — diverse set, not Temple-only."""
    refs = list(library.get("references") or [])
    dna = {str(item.get("reference_id")): item for item in list(library.get("dna") or [])}

    def score(entry: dict[str, Any]) -> tuple[int, str]:
        rid = str(entry.get("reference_id"))
        analyzed = 2 if dna.get(rid, {}).get("visual_analysis_status") == "ANALYZED" else 0
        diverse = 1 if entry.get("project_affinity") != "THE_TEMPLE" else 0
        portrait = 1 if entry.get("orientation") in {"portrait", "square"} or format_aspect == "4:5" else 0
        return (analyzed + diverse + portrait, rid)

    ranked = sorted(refs, key=score, reverse=True)
    picked: list[dict[str, Any]] = []
    seen_affinity: set[str] = set()
    for entry in ranked:
        aff = str(entry.get("project_affinity") or entry.get("brand_affinity") or "other")
        if aff in seen_affinity and len(picked) < limit - 1 and len(ranked) > limit:
            continue
        seen_affinity.add(aff)
        blob = dict(entry)
        blob["dna"] = dna.get(str(entry.get("reference_id")))
        picked.append(blob)
        if len(picked) >= limit:
            break
    if len(picked) < min(limit, len(ranked)):
        for entry in ranked:
            if entry in picked or any(p.get("reference_id") == entry.get("reference_id") for p in picked):
                continue
            blob = dict(entry)
            blob["dna"] = dna.get(str(entry.get("reference_id")))
            picked.append(blob)
            if len(picked) >= limit:
                break
    _ = purpose
    return picked[:limit]
