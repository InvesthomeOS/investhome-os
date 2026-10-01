"""Fast dump: ORNEK_00012 + Temple-linked photos only."""

from io import BytesIO
from pathlib import Path
from uuid import UUID

from PIL import Image
from sqlalchemy import select

from investhome_api.db.session import SessionLocal
from investhome_api.models.creative_studio_media import CreativeStudioMediaAsset
from investhome_api.services.creative_director.phase5_workflow import LOCKED_LOGO_ASSET_ID, TEMPLE_PROJECT_ID, _read_bytes

OUT = Path("/tmp/phase9-0-inspect")
ORNEK = "ORNEK_00012.jpg"


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    db = SessionLocal()
    ornek = db.scalars(select(CreativeStudioMediaAsset).where(CreativeStudioMediaAsset.filename == ORNEK)).first()
    if ornek is None:
        raise SystemExit("ORNEK_00012.jpg not found")
    img = Image.open(BytesIO(_read_bytes(db, ornek.id))).convert("RGB")
    img.save(OUT / "ORNEK_00012.png")
    lines = [f"ORNEK\t{ornek.id}\t{ORNEK}\t{img.size}"]
    project = UUID(TEMPLE_PROJECT_ID)
    temple = list(
        db.scalars(
            select(CreativeStudioMediaAsset).where(
                CreativeStudioMediaAsset.linked_project_id == project,
                CreativeStudioMediaAsset.archived_at.is_(None),
            )
        ).all()
    )
    for i, row in enumerate(sorted(temple, key=lambda r: str(r.filename or ""))):
        if str(row.id) == LOCKED_LOGO_ASSET_ID:
            lines.append(f"LOGO\t{row.id}\t{row.filename}")
            continue
        name = str(row.filename or "")
        try:
            photo = Image.open(BytesIO(_read_bytes(db, row.id))).convert("RGB")
        except Exception as exc:
            lines.append(f"FAIL\t{row.id}\t{name}\t{exc}")
            continue
        preview = photo.copy()
        preview.thumbnail((640, 800), Image.Resampling.LANCZOS)
        safe = "".join(ch if ch.isalnum() or ch in "._-" else "_" for ch in name)[:70]
        preview.save(OUT / f"p-{i:02d}-{safe}.png")
        lines.append(f"{i:02d}\t{row.id}\t{name}\t{photo.size}")
    (OUT / "catalog.txt").write_text("\n".join(lines), encoding="utf-8")
    print("\n".join(lines))
    print("count", len(lines))


if __name__ == "__main__":
    main()
