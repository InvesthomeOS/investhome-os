"""Dump ORNEK_00006, approved Masters, and Temple photos for Master 03 inspection."""

from io import BytesIO
from pathlib import Path
from uuid import UUID

from PIL import Image
from sqlalchemy import select

from investhome_api.db.session import SessionLocal
from investhome_api.models.creative_studio_media import CreativeStudioMediaAsset
from investhome_api.services.creative_director.phase5_workflow import LOCKED_LOGO_ASSET_ID, TEMPLE_PROJECT_ID, _read_bytes
from investhome_api.services.creative_director.phase8_3_approve_lock import APPROVED_ASSET_ID
from investhome_api.services.creative_director.phase9_0_r3_approve_lock import APPROVED_ASSET_02

OUT = Path("/tmp/phase9-1-inspect")
ORNEK = "ORNEK_00006.jpg"
PHOTOS = (
    "IH_DC_TMP_001_Render_Exterior_Day_001.jpg",
    "IH_DC_TMP_001_Render_Exterior_Day_002.jpg",
    "IH_DC_TMP_001_Render_Exterior_Day_003.jpg",
    "IH_DC_TMP_001_Render_Exterior_Day_004.jpg",
    "IH_DC_TMP_001_Render_Exterior_Day_005.jpg",
    "IH_DC_TMP_001_Render_Exterior_Day_007.jpg",
    "IH_DC_TMP_001_Render_Exterior_Day_008.jpg",
    "IH_DC_TMP_001_Render_Exterior_Day_009.jpg",
    "IH_DC_TMP_001_Render_Exterior_Day_010.jpg",
    "IH_DC_TMP_001_Render_Exterior_Sunset_001.jpg",
    "IH_DC_TMP_001_Render_Living_Room_001.jpg",
    "IH_DC_TMP_001_Render_Living_Room_005.jpg",
    "IH_DC_TMP_001_Render_Bedroom_007.jpg",
    "01 Street Veiw.jpg",
)


def _save(img: Image.Image, name: str, size: tuple[int, int] = (900, 1100)) -> None:
    prev = img.copy()
    prev.thumbnail(size, Image.Resampling.LANCZOS)
    prev.save(OUT / name)


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    db = SessionLocal()
    ornek = db.scalars(select(CreativeStudioMediaAsset).where(CreativeStudioMediaAsset.filename == ORNEK)).first()
    if ornek is None:
        raise SystemExit("ORNEK_00006.jpg not found")
    ref = Image.open(BytesIO(_read_bytes(db, ornek.id))).convert("RGB")
    ref.save(OUT / "ORNEK_00006-full.png")
    _save(ref, "ORNEK_00006.png", (1088, 1360))
    print(f"ORNEK\t{ornek.id}\t{ORNEK}\t{ref.size}")

    m01 = Image.open(BytesIO(_read_bytes(db, UUID(APPROVED_ASSET_ID)))).convert("RGB")
    m02 = Image.open(BytesIO(_read_bytes(db, UUID(APPROVED_ASSET_02)))).convert("RGB")
    _save(m01, "master-01.png", (1088, 1360))
    _save(m02, "master-02.png", (1088, 1360))
    print(f"M01\t{APPROVED_ASSET_ID}\t{m01.size}")
    print(f"M02\t{APPROVED_ASSET_02}\t{m02.size}")

    names = list(PHOTOS)
    rows = list(db.scalars(select(CreativeStudioMediaAsset).where(CreativeStudioMediaAsset.filename.in_(names))).all())
    by = {str(r.filename): r for r in rows}
    for name in names:
        row = by.get(name)
        if row is None:
            print("MISSING", name)
            continue
        img = Image.open(BytesIO(_read_bytes(db, row.id))).convert("RGB")
        safe = name.replace("IH_DC_TMP_001_Render_", "").replace(" ", "_")
        _save(img, f"{safe}.png")
        print(f"{row.id}\t{name}\t{img.size}")

    project = UUID(TEMPLE_PROJECT_ID)
    extra = list(
        db.scalars(
            select(CreativeStudioMediaAsset).where(
                CreativeStudioMediaAsset.linked_project_id == project,
                CreativeStudioMediaAsset.archived_at.is_(None),
            )
        ).all()
    )
    for row in extra:
        name = str(row.filename or "")
        if str(row.id) == LOCKED_LOGO_ASSET_ID:
            continue
        if name in names:
            continue
        if not any(k in name.lower() for k in ("living", "bedroom", "kitchen", "amenity", "lobby", "pool", "gym", "interior", "detail", "facade")):
            continue
        try:
            img = Image.open(BytesIO(_read_bytes(db, row.id))).convert("RGB")
        except Exception:
            continue
        safe = "".join(ch if ch.isalnum() or ch in "._-" else "_" for ch in name)[:70]
        _save(img, f"extra-{safe}.png")
        print(f"EXTRA\t{row.id}\t{name}\t{img.size}")


if __name__ == "__main__":
    main()
