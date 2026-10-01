"""Creative Font Registry — role-based campaign typography.

Scans legally supplied brand/creative font directories and the runtime
inventory. Never claims a premium face that is not actually present.
DejaVu is recorded as a last-resort technical fallback, not a campaign face.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from PIL import ImageFont

ROLES = (
    "DISPLAY_SERIF",
    "DISPLAY_SANS",
    "EDITORIAL_SERIF",
    "EDITORIAL_SANS",
    "BODY",
    "COMMERCIAL_NUMBER",
    "CTA",
    "BRAND",
)

_CREATIVE_DIR_NAMES = ("assets/creative/fonts", "assets/brand/fonts", "apps/web/public/brand/fonts")
_RUNTIME_ROOTS = (
    Path("/usr/local/share/fonts/investhome"),
    Path("/usr/share/fonts"),
    Path("/usr/local/share/fonts"),
    Path("C:/Windows/Fonts"),
)

_PREMIUM_OPEN = (
    "cormorant",
    "source sans",
    "sourcesans",
    "source serif",
    "eb garamond",
    "libre baskerville",
    "playfair",
    "ibm plex",
    "source serif",
)
_BRAND_HINTS = ("helvetica", "neue", "myriad")
_SYSTEM_DISPLAY = ("georgia", "garamond", "didot", "times")
_LIBERATION = ("liberation",)
_DEJAVU = ("dejavu",)


def _walk_parents(start: Path) -> list[Path]:
    out = [start]
    out.extend(start.parents)
    return out


def registry_roots() -> list[Path]:
    roots: list[Path] = []
    here = Path(__file__).resolve()
    for parent in _walk_parents(here):
        for rel in _CREATIVE_DIR_NAMES:
            roots.append(parent / Path(rel))
        roots.append(parent / "creative" / "fonts")
    roots.extend(_RUNTIME_ROOTS)
    seen: set[str] = set()
    unique: list[Path] = []
    for path in roots:
        key = str(path).lower()
        if key in seen:
            continue
        seen.add(key)
        unique.append(path)
    return unique


def _iter_font_files(root: Path) -> list[Path]:
    if not root.exists() or not root.is_dir():
        return []
    files: list[Path] = []
    for path in root.rglob("*"):
        if path.suffix.lower() in {".ttf", ".otf", ".ttc"} and path.is_file():
            files.append(path)
    return files


def inspect_font_files() -> list[dict[str, Any]]:
    found: list[dict[str, Any]] = []
    seen: set[str] = set()
    for root in registry_roots():
        for path in _iter_font_files(root):
            key = str(path.resolve()).lower()
            if key in seen:
                continue
            seen.add(key)
            name = path.name.lower()
            family = path.stem.replace("-VF", "").replace("_", " ")
            found.append(
                {
                    "path": str(path),
                    "file": path.name,
                    "family": family,
                    "root": str(root),
                    "brand_kit": any(h in name for h in _BRAND_HINTS),
                    "premium_open": any(h in name or h in family.lower() for h in _PREMIUM_OPEN),
                    "system_display": any(h in name for h in _SYSTEM_DISPLAY),
                    "liberation": any(h in name for h in _LIBERATION),
                    "dejavu": any(h in name for h in _DEJAVU),
                    "variable": "vf" in name or "[" in path.name,
                }
            )
    return found


def _score_for_role(item: dict[str, Any], role: str) -> int:
    name = (item.get("file") or "").lower()
    serif_role = role in {"DISPLAY_SERIF", "EDITORIAL_SERIF", "COMMERCIAL_NUMBER"}
    sans_role = not serif_role
    score = 0
    if item.get("brand_kit") and sans_role:
        score += 100
    if item.get("premium_open"):
        if serif_role and "cormorant" in name:
            score += 90
        elif sans_role and "source" in name and "sans" in name:
            score += 90
        elif serif_role and "serif" in name:
            score += 80
        else:
            score += 50
    if item.get("system_display") and serif_role:
        score += 40
    if item.get("liberation"):
        score += 15
    if item.get("dejavu"):
        score -= 50
    if "bold" in name or "700" in name:
        if role in {"DISPLAY_SERIF", "DISPLAY_SANS", "COMMERCIAL_NUMBER", "CTA"}:
            score += 4
    return score


def _weight_for_role(role: str) -> int:
    return {
        "DISPLAY_SERIF": 650,
        "DISPLAY_SANS": 600,
        "EDITORIAL_SERIF": 500,
        "EDITORIAL_SANS": 400,
        "BODY": 400,
        "COMMERCIAL_NUMBER": 600,
        "CTA": 600,
        "BRAND": 400,
    }.get(role, 500)


def load_font(path: str | None, size: int, *, weight: int | None = None) -> ImageFont.ImageFont:
    if not path:
        return ImageFont.load_default()
    font = ImageFont.truetype(path, size=max(8, int(size)))
    if weight is None:
        return font
    try:
        setter = getattr(font, "set_variation_by_axes", None)
        if callable(setter):
            setter([float(weight)])
    except Exception:
        pass
    return font


def resolve_role(role: str, inventory: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    files = inventory if inventory is not None else inspect_font_files()
    ranked = sorted(files, key=lambda item: _score_for_role(item, role), reverse=True)
    chosen = ranked[0] if ranked else None
    fallback_used = False
    if chosen and chosen.get("dejavu") and not chosen.get("premium_open") and not chosen.get("brand_kit"):
        fallback_used = True
    return {
        "role": role,
        "font_family": None if chosen is None else chosen.get("family"),
        "font_file": None if chosen is None else chosen.get("file"),
        "font_path": None if chosen is None else chosen.get("path"),
        "font_weight": _weight_for_role(role),
        "font_style": "normal",
        "premium_open": bool(chosen and chosen.get("premium_open")),
        "brand_kit": bool(chosen and chosen.get("brand_kit")),
        "dejavu": bool(chosen and chosen.get("dejavu")),
        "fallback_used": fallback_used or chosen is None,
        "fallback_kind": (
            "none"
            if chosen and (chosen.get("premium_open") or chosen.get("brand_kit"))
            else "system_display"
            if chosen and chosen.get("system_display")
            else "liberation"
            if chosen and chosen.get("liberation")
            else "dejavu_last_resort"
            if chosen and chosen.get("dejavu")
            else "missing"
        ),
    }


def build_font_registry() -> dict[str, Any]:
    inventory = inspect_font_files()
    roles = {role: resolve_role(role, inventory) for role in ROLES}
    premium = any(r.get("premium_open") or r.get("brand_kit") for r in roles.values())
    dejavu_only = bool(inventory) and all(i.get("dejavu") for i in inventory)
    return {
        "schema": "CreativeFontRegistryV1",
        "inventory": inventory,
        "roles": roles,
        "premium_or_brand_available": premium,
        "dejavu_only": dejavu_only,
        "brand_kit_expected": ["Helvetica Neue"],
        "brand_kit_present": any(i.get("brand_kit") for i in inventory),
        "limitation": (
            None
            if premium
            else (
                "No brand-kit or premium/open display face was found. "
                "DejaVu is a technical last resort and is not a campaign typeface."
                if dejavu_only or not inventory
                else "Only generic system/open faces were found; no brand-kit Helvetica Neue."
            )
        ),
    }


def font_for_role(registry: dict[str, Any], role: str, size: int) -> ImageFont.ImageFont:
    spec = dict((registry.get("roles") or {}).get(role) or resolve_role(role))
    return load_font(spec.get("font_path"), size, weight=int(spec.get("font_weight") or 500))
