"""Dump ORNEK_00001 and Temple exteriors for visual inspection."""

from pathlib import Path

from investhome_api.db.session import SessionLocal
from investhome_api.services.creative_director.phase5_5a_ai_visual_art_director import load_grade_a_reference_images
from investhome_api.services.creative_director.temple_exterior_catalog import load_temple_exteriors

OUT = Path("/tmp/phase8-2-inspect")


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    db = SessionLocal()
    loaded, provenance, ok = load_grade_a_reference_images(db)
    by_name = {name: image for name, image in loaded}
    src = by_name["ORNEK_00001.jpg"]
    src.save(OUT / "ORNEK_00001.png")
    (OUT / "ornek-size.txt").write_text(f"{src.size} ok={ok}\n{provenance}\n", encoding="utf-8")
    catalog = load_temple_exteriors(db)
    lines = []
    for i, item in enumerate(catalog):
        preview = item["preview"]
        preview.save(OUT / f"ext-{i:02d}-{item['filename'][:40]}.png")
        lines.append(
            f"{i}\t{item['asset_id']}\t{item['filename']}\tsky={item['sky_area']:.3f}\thard={item['hard_coverage']:.3f}\tcx={item['architecture_centroid_x']:.3f}\tsource={item['source'].size}"
        )
    (OUT / "exteriors.txt").write_text("\n".join(lines), encoding="utf-8")
    print("\n".join(lines))
    print("ORNEK", src.size)


if __name__ == "__main__":
    main()
