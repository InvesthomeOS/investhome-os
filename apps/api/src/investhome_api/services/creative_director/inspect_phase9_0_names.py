from uuid import UUID
from sqlalchemy import select
from investhome_api.db.session import SessionLocal
from investhome_api.models.creative_studio_media import CreativeStudioMediaAsset
from investhome_api.services.creative_director.phase5_workflow import TEMPLE_PROJECT_ID

db = SessionLocal()
rows = db.scalars(
    select(CreativeStudioMediaAsset).where(
        CreativeStudioMediaAsset.linked_project_id == UUID(TEMPLE_PROJECT_ID),
        CreativeStudioMediaAsset.archived_at.is_(None),
    )
).all()
for r in sorted(rows, key=lambda x: str(x.filename or "")):
    print(f"{r.id}\t{r.filename}\t{r.width}x{r.height}\t{r.content_type}")
print("COUNT", len(rows))
