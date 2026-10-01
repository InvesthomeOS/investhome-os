from io import BytesIO
from pathlib import Path
from uuid import UUID

from PIL import Image
from sqlalchemy import select

from investhome_api.db.session import SessionLocal
from investhome_api.models.creative_studio_media import CreativeStudioMediaAsset
from investhome_api.services.creative_director.phase5_workflow import _read_bytes

OUT = Path("/tmp/phase9-0-shortlist")
NAMES = (
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


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    db = SessionLocal()
    rows = list(db.scalars(select(CreativeStudioMediaAsset).where(CreativeStudioMediaAsset.filename.in_(NAMES))).all())
    by = {str(r.filename): r for r in rows}
    for name in NAMES:
        row = by.get(name)
        if row is None:
            print("MISSING", name)
            continue
        img = Image.open(BytesIO(_read_bytes(db, row.id))).convert("RGB")
        prev = img.copy()
        prev.thumbnail((900, 1100), Image.Resampling.LANCZOS)
        safe = name.replace("IH_DC_TMP_001_Render_", "").replace(" ", "_")
        prev.save(OUT / f"{safe}.png")
        print(f"{row.id}\t{name}\t{img.size}")


if __name__ == "__main__":
    main()
