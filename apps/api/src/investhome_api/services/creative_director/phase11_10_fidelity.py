"""ArchitectureFidelityAuditV2 — factual identity, not pixel-identical grade."""

from __future__ import annotations

from typing import Any

from PIL import Image, ImageChops, ImageDraw, ImageOps

from investhome_api.services.creative_director.phase5_creative_quality import _font
from investhome_api.services.creative_director.project_architecture_lock import (
    architecture_integrity_qa,
    derive_architecture_mask,
)
from investhome_api.services.creative_director.structured_typography_compositor_v2 import GOLD, IVORY

SCHEMA = "ArchitectureFidelityAuditV2"


def _crop_box(mask: Image.Image, frac: tuple[float, float, float, float]) -> tuple[int, int, int, int]:
    box = mask.getbbox() or (0, 0, mask.size[0], mask.size[1])
    x0, y0, x1, y1 = box
    w, h = x1 - x0, y1 - y0
    return (
        x0 + int(w * frac[0]),
        y0 + int(h * frac[1]),
        x0 + int(w * frac[2]),
        y0 + int(h * frac[3]),
    )


def _ncc(a: Image.Image, b: Image.Image) -> float:
    ga = a.convert("L").resize((64, 64), Image.Resampling.BOX)
    gb = b.convert("L").resize((64, 64), Image.Resampling.BOX)
    pa, pb = list(ga.getdata()), list(gb.getdata())
    ma = sum(pa) / len(pa)
    mb = sum(pb) / len(pb)
    num = den_a = den_b = 0.0
    for x, y in zip(pa, pb):
        da, db = x - ma, y - mb
        num += da * db
        den_a += da * da
        den_b += db * db
    den = (den_a * den_b) ** 0.5
    return 0.0 if den <= 1e-6 else max(-1.0, min(1.0, num / den))


def architecture_fidelity_audit_v2(source: Image.Image, candidate: Image.Image) -> dict[str, Any]:
    src = source.convert("RGB")
    cand = candidate.convert("RGB")
    if cand.size != src.size:
        cand = cand.resize(src.size, Image.Resampling.LANCZOS)
    mask = derive_architecture_mask(src)
    qa = architecture_integrity_qa(src, cand, mask=mask)
    regions = {
        "SPIRE": (0.35, 0.00, 0.78, 0.42),
        "ROOF": (0.18, 0.28, 0.92, 0.52),
        "WINDOWS": (0.22, 0.40, 0.88, 0.78),
        "DOORS": (0.30, 0.70, 0.72, 0.98),
        "GEOMETRY": (0.08, 0.08, 0.92, 0.92),
        "SILHOUETTE": (0.00, 0.00, 1.00, 1.00),
        "MATERIAL_IDENTITY": (0.20, 0.35, 0.80, 0.75),
    }
    features: dict[str, Any] = {}
    fails: list[str] = []
    for name, frac in regions.items():
        box = _crop_box(mask, frac)
        a = src.crop(box)
        b = cand.crop(box)
        ncc = _ncc(a, b)
        # Material: allow grade; fail only if structure is gone.
        floor = 0.22 if name == "MATERIAL_IDENTITY" else 0.28
        if name == "SILHOUETTE":
            floor = 0.32
        passed = ncc >= floor
        if name == "SPIRE" and float(qa.get("tower_score") or 1) < 0.45:
            passed = False
        if name == "WINDOWS" and float(qa.get("window_or_facade_projection") or 1) < 0.32:
            passed = False
        if name == "GEOMETRY" and qa.get("architecture_integrity_status") == "fail":
            passed = False
        if name == "SILHOUETTE" and float(qa.get("silhouette_ncc") or ncc) < 0.28:
            passed = False
        features[name] = {"ncc": round(ncc, 4), "pass": passed, "floor": floor}
        if not passed:
            fails.append(name)
    if "SPIRE" in fails or "WINDOWS" in fails:
        features["GEOMETRY"]["pass"] = False
        if "GEOMETRY" not in fails:
            fails.append("GEOMETRY")
    overall = not fails
    return {
        "schema": SCHEMA,
        "features": features,
        "integrity_qa": qa,
        "failures": fails,
        "pass": overall,
        "note": "Factual identity required. Global grade allowed. Invented architecture is FAIL.",
    }


def architecture_fidelity_board(source: Image.Image, candidate: Image.Image, audit: dict[str, Any]) -> Image.Image:
    canvas = Image.new("RGB", (1920, 1180), (14, 12, 11))
    draw = ImageDraw.Draw(canvas)
    draw.text((28, 16), "08  ARCHITECTURE FIDELITY AUDIT V2  —  source / candidate / difference", font=_font(16), fill=GOLD)
    src = source.convert("RGB")
    cand = candidate.convert("RGB")
    if cand.size != src.size:
        cand = cand.resize(src.size, Image.Resampling.LANCZOS)
    diff = ImageOps.autocontrast(ImageChops.difference(src, cand).convert("L")).convert("RGB")
    x = 28
    for title, image in (("SOURCE", src), ("CANDIDATE", cand), ("DIFFERENCE", diff)):
        tile = image.copy()
        tile.thumbnail((600, 980), Image.Resampling.LANCZOS)
        canvas.paste(tile, (x, 56))
        draw.text((x, 1050), title, font=_font(15), fill=IVORY)
        x += 630
    y = 56
    for name, row in (audit.get("features") or {}).items():
        mark = "PASS" if row.get("pass") else "FAIL"
        draw.text((28, 1088), "", font=_font(12), fill=IVORY)
        y = 1088
    line = "   ".join(
        f"{name}: {'PASS' if (audit.get('features') or {}).get(name, {}).get('pass') else 'FAIL'}"
        for name in ("GEOMETRY", "WINDOWS", "DOORS", "ROOF", "SPIRE", "SILHOUETTE", "MATERIAL_IDENTITY")
    )
    draw.text((28, 1110), line[:140], font=_font(14), fill=GOLD if audit.get("pass") else (200, 80, 70))
    return canvas
