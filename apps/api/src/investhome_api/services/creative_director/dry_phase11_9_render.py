"""Phase 11.9 dry render — field + object + one 4:5. No critic. No R1."""

from __future__ import annotations

from io import BytesIO
from pathlib import Path
from uuid import UUID

from PIL import Image

from investhome_api.db.session import SessionLocal
from investhome_api.models.creative_director_campaign import CreativeDirectorCampaign
from investhome_api.models.user_auth import User
from investhome_api.services.creative_director.phase5_premium_commercial_final import _png
from investhome_api.services.creative_director.phase5_workflow import (
    LOCKED_LOGO_ASSET_ID,
    PRODUCTION_CAMPAIGN_ID,
    TEMPLE_PROJECT_ID,
    _read_bytes,
)
from investhome_api.services.creative_director.phase11_9_compose import compose_hybrid_v2
from investhome_api.services.creative_director.phase11_9_field import generate_register_field
from investhome_api.services.creative_director.phase11_9_strategy import DAY009_ASSET_ID, DAY009_CROP, DAY009_FILENAME
from investhome_api.services.creative_director.phase11_9_integrate import lantern_preserved, punch_residual_sky
from investhome_api.services.creative_director.project_object_extraction_v2 import extract_project_object_v2, inspect_fringe, EDGE_BACKGROUNDS
from investhome_api.services.creative_director.project_reality_firewall_v1 import run_project_reality_firewall
from investhome_api.services.gpt_image_design.client import reset_provider_call_count

OUT = Path("/tmp/phase11-9-hybrid-v2-creative-proof")


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    db = SessionLocal()
    row = db.get(CreativeDirectorCampaign, UUID(PRODUCTION_CAMPAIGN_ID))
    assert row is not None
    user = db.get(User, row.created_by_user_id) or db.query(User).first()
    assert user is not None
    reset_provider_call_count()
    field_pack = generate_register_field(
        db,
        user,
        project_id=UUID(TEMPLE_PROJECT_ID),
        session_id="phase11_9_dry",
        reuse_path=OUT / "04-generated-field.png" if (OUT / "04-generated-field.png").is_file() else None,
    )
    field = field_pack["image"]
    firewall = run_project_reality_firewall(field)
    print("firewall", firewall.get("status"), "reused", field_pack.get("reused"))
    if firewall.get("status") != "PASS":
        raise SystemExit(f"firewall fail {firewall}")
    (OUT / "04-generated-field.png").write_bytes(_png(field))
    source = Image.open(BytesIO(_read_bytes(db, UUID(DAY009_ASSET_ID)))).convert("RGB")
    obj, meta = extract_project_object_v2(
        source, crop_box=DAY009_CROP, filename=DAY009_FILENAME, asset_id=DAY009_ASSET_ID
    )
    obj = punch_residual_sky(obj)
    print("object", obj.size, "lantern", lantern_preserved(obj))
    for name, color in EDGE_BACKGROUNDS.items():
        print("edge", name, inspect_fringe(obj, color).get("pass"))
    logo = _read_bytes(db, UUID(LOCKED_LOGO_ASSET_ID))
    final, _markup, compose_meta, layers = compose_hybrid_v2(field=field, obj=obj, logo_bytes=logo)
    (OUT / "05-project-object.png").write_bytes(_png(layers["placed"]))
    (OUT / "06-scene-integration-proof.png").write_bytes(_png(layers["fused"]))
    (OUT / "09-hybrid-v2-final.png").write_bytes(_png(final))
    print("hierarchy", compose_meta.get("hierarchy", {}).get("pass"), compose_meta.get("optical"))
    print("size", final.size)


if __name__ == "__main__":
    main()
