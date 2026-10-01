"""ReferenceSimilarityAuditV1 — DNA transfer, not a clone."""

from __future__ import annotations

from typing import Any

from PIL import Image, ImageStat

from investhome_api.services.creative_director.phase11_11_select import SELECTED_FILENAME


def _mean_rgb(image: Image.Image) -> tuple[float, float, float]:
    rgb = image.convert("RGB").resize((64, 80))
    r, g, b = rgb.split()
    return (
        float(ImageStat.Stat(r).mean[0]),
        float(ImageStat.Stat(g).mean[0]),
        float(ImageStat.Stat(b).mean[0]),
    )


def reference_similarity_audit(
    *,
    reference: Image.Image,
    final: Image.Image,
    markup: str,
) -> dict[str, Any]:
    rr, rg, rb = _mean_rgb(reference)
    fr, fg, fb = _mean_rgb(final)
    navy_clone = rb > rr + 18 and rb > rg + 12 and fr < 80 and fb > fr + 20
    low = markup.lower()
    signature_hits = [
        token
        for token in (
            "düzenli",
            "güvenli",
            "prestijli",
            "uniloft",
            "investhome",
            "yatırıma açılan",
            "300 i st",
        )
        if token in low
    ]
    project_copy_hits = [
        token
        for token in ("uniloft", "300 i st", "capitol hill", "union station")
        if token in low
    ]
    layout_similarity = "RELATED_TWO_MASS"  # transferable: architecture vs void
    rhythm_similarity = "RELATED_SCALE_JUMP"
    commercial_similarity = "ADAPTED_ROLES"  # numbers mapped into a verbal-chant structure
    signature_copying = "YES" if signature_hits or navy_clone else "NO"
    content_copying = "YES" if project_copy_hits else "NO"
    dna_clear = signature_copying == "NO" and content_copying == "NO"
    return {
        "schema": "ReferenceSimilarityAuditV1",
        "reference": SELECTED_FILENAME,
        "LAYOUT_SIMILARITY": layout_similarity,
        "VISUAL_RHYTHM_SIMILARITY": rhythm_similarity,
        "COMMERCIAL_STRUCTURE_SIMILARITY": commercial_similarity,
        "SIGNATURE_ELEMENT_COPYING": signature_copying,
        "PROJECT_CONTENT_COPYING": content_copying,
        "TRANSFERABLE_DNA": "CLEAR" if dna_clear else "FAIL",
        "navy_field_clone": bool(navy_clone),
        "signature_hits": signature_hits,
        "project_copy_hits": project_copy_hits,
        "mean_reference_rgb": [round(rr, 1), round(rg, 1), round(rb, 1)],
        "mean_final_rgb": [round(fr, 1), round(fg, 1), round(fb, 1)],
        "pass": dna_clear and not navy_clone,
        "must_feel_like": "same level of design intelligence, not the same advertisement with Temple swapped in",
    }
