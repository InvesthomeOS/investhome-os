"""Explicit Bitrix → canonical agreement project/group mapping.

No fuzzy matching. Unknown labels stay unknown.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from investhome_api.models.project import Project


class BitrixProjectGroup(StrEnum):
    KST_1307 = "1307_k_st"
    PENN_1313 = "1313_penn"
    HPL_1812 = "1812_h_pl"
    ONTARIO_2319 = "2319_ontario"
    REIT = "reit"
    THE_TEMPLE = "the_temple"
    UNILOFT = "uniloft"


BITRIX_PROJECT_GROUP_LABELS: dict[BitrixProjectGroup, str] = {
    BitrixProjectGroup.KST_1307: "1307 K St",
    BitrixProjectGroup.PENN_1313: "1313 Penn",
    BitrixProjectGroup.HPL_1812: "1812 H Pl",
    BitrixProjectGroup.ONTARIO_2319: "2319 Ontario",
    BitrixProjectGroup.REIT: "REIT",
    BitrixProjectGroup.THE_TEMPLE: "The Temple",
    BitrixProjectGroup.UNILOFT: "Uniloft",
}

# Exact OS project_name values used for FK resolution. REIT has none.
_OS_PROJECT_NAMES: dict[BitrixProjectGroup, tuple[str, ...]] = {
    BitrixProjectGroup.KST_1307: ("1307",),
    BitrixProjectGroup.PENN_1313: ("1313",),
    BitrixProjectGroup.HPL_1812: ("1812 H Place NE",),
    BitrixProjectGroup.ONTARIO_2319: ("2319",),
    BitrixProjectGroup.REIT: (),
    BitrixProjectGroup.THE_TEMPLE: ("The Temple",),
    BitrixProjectGroup.UNILOFT: ("UniLoft",),
}

_ALIAS_TO_GROUP: dict[str, BitrixProjectGroup] = {
    "1307 k st": BitrixProjectGroup.KST_1307,
    "1307 k street": BitrixProjectGroup.KST_1307,
    "1307": BitrixProjectGroup.KST_1307,
    "1313 penn": BitrixProjectGroup.PENN_1313,
    "1313 pennsylvania": BitrixProjectGroup.PENN_1313,
    "1313": BitrixProjectGroup.PENN_1313,
    "1812 h pl": BitrixProjectGroup.HPL_1812,
    "1812 h place": BitrixProjectGroup.HPL_1812,
    "1812 h place ne": BitrixProjectGroup.HPL_1812,
    "1812": BitrixProjectGroup.HPL_1812,
    "2319 ontario": BitrixProjectGroup.ONTARIO_2319,
    "2319": BitrixProjectGroup.ONTARIO_2319,
    "reit": BitrixProjectGroup.REIT,
    "the temple": BitrixProjectGroup.THE_TEMPLE,
    "temple": BitrixProjectGroup.THE_TEMPLE,
    "uniloft": BitrixProjectGroup.UNILOFT,
    "uni loft": BitrixProjectGroup.UNILOFT,
    "uni-loft": BitrixProjectGroup.UNILOFT,
}


@dataclass(frozen=True)
class ProjectAliasResolution:
    group: BitrixProjectGroup | None
    label: str | None
    project_id: UUID | None
    os_project_name: str | None
    unknown_value: str | None


_TR_FOLD = str.maketrans({
    "ı": "i",
    "ü": "u",
    "ö": "o",
    "ş": "s",
    "ğ": "g",
    "ç": "c",
    "â": "a",
})


def fold_alias(value: str | None) -> str:
    if not value:
        return ""
    text = unicodedata.normalize("NFKC", value)
    # Turkish İ casefolds to i + combining dot; map before casefold so headers
    # like "İlk adı" and "İş E-postası" match ASCII aliases.
    text = text.replace("\u0130", "I").replace("\u0131", "i")
    text = text.casefold()
    text = unicodedata.normalize("NFKD", text)
    text = "".join(ch for ch in text if unicodedata.category(ch) != "Mn")
    text = text.translate(_TR_FOLD)
    text = re.sub(r"[._]+", " ", text)
    text = re.sub(r"[^\w\s-]", " ", text, flags=re.UNICODE)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def resolve_project_group(value: str | None) -> BitrixProjectGroup | None:
    if not value:
        return None
    candidates = [fold_alias(value), fold_alias(Path(value).stem)]
    for folded in candidates:
        if not folded:
            continue
        stripped = re.sub(r"^anlasmalar?\s+", "", folded).strip()
        for key in (folded, stripped):
            if not key:
                continue
            if key in _ALIAS_TO_GROUP:
                return _ALIAS_TO_GROUP[key]
            stem = re.sub(r"\s+(xls|xlsx|csv)$", "", key).strip()
            if stem in _ALIAS_TO_GROUP:
                return _ALIAS_TO_GROUP[stem]
    return None


def resolve_project_alias(
    value: str | None,
    *,
    project_ids_by_name: dict[str, UUID] | None = None,
) -> ProjectAliasResolution:
    group = resolve_project_group(value)
    if group is None:
        return ProjectAliasResolution(
            group=None,
            label=None,
            project_id=None,
            os_project_name=None,
            unknown_value=(value or "").strip() or None,
        )
    names = _OS_PROJECT_NAMES[group]
    project_id = None
    os_name = None
    if project_ids_by_name:
        for name in names:
            if name in project_ids_by_name:
                project_id = project_ids_by_name[name]
                os_name = name
                break
    return ProjectAliasResolution(
        group=group,
        label=BITRIX_PROJECT_GROUP_LABELS[group],
        project_id=project_id,
        os_project_name=os_name,
        unknown_value=None,
    )


def load_project_ids_by_name(db: Session) -> dict[str, UUID]:
    rows = db.scalars(select(Project)).all()
    return {row.project_name: row.id for row in rows if row.project_name}
