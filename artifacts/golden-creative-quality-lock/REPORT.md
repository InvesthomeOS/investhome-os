# Golden Creative Quality Lock — Hybrid AI Design Report

**Status:** READY FOR GOLDEN CREATIVE QUALITY REVIEW  
**Visual Quality PASS declared:** NO (user visual approval required)

## Numbered report (1–20)

1. **Architecture decision:** DESIGN QUALITY FIRST, EDITABILITY SECOND — GPT Image / finished-ad is primary designer; full layer reconstruction is NOT production default.
2. **Default generate mode:** `finished_ad` (API schema + web `generateCreativeDirectorAd` + SMB Oluştur path).
3. **Legacy opt-in:** `editable_finished_ad` remains available when explicitly requested; not used by SMB generate.
4. **SMB hydration:** `createFinishedAdCanvasPost` with `editableFinishedAd=false` → single full-bleed IMAGE raster (no design_spec layer stack).
5. **Golden master ID:** `master_asset_id` ↔ `master_finished_ad_asset_id` set once on first finished-ad; never overwritten.
6. **Revision routing:** Non-editable campaigns force `IMAGE_REQUIRED`; `LAYER_ONLY` only when `production_mode=editable_finished_ad`.
7. **Fidelity lock:** Creative revisions always source immutable MASTER + cumulative ops — never prior revision raster.
8. **Quality guard (generate):** Structural checks (logo lock, claims, headline/CTA/language) → status `review` (never auto Visual Quality PASS).
9. **Quality guard (revise):** Brightness/contrast/color/dimension drift vs master; fail rejects revision.
10. **Kept intact:** Revision Intelligence v2, Right Edit Panel, Bottom Bar, Undo/Redo, Claim Guard, Language/Logo locks, Creative Director, Production Brief, Smart Asset Selection.
11. **NOT used:** editable renderer as primary designer; VLD/native social/design; Canva clone; recursive AI-raster edits.
12. **Unit tests:** 54 passed (RI v2, revision, finished_ad default, quality lock, editable legacy).
13. **Live A — LIFESTYLE:** campaign `cc010ded-2010-4cd7-a1cd-e95e3af46144` · asset `ad1dc95b-b0fb-4e36-bb20-e793dc9e77f5` · PNG `A_lifestyle-final.png` · GPT=1 · no design_spec.
14. **Live B — PRICE Unit 204:** campaign `858a3fc3-ccea-4c77-869d-448fd7153c7a` · asset `67a76648-45c9-48be-9c3e-7efef8944ad1` · PNG `B_price-final.png` · GPT=1 · $400k/$300k/~25%.
15. **Live C — LOCATION Adams Morgan:** campaign `84af2de0-642c-4170-ae84-98b8a23427b9` · asset `d594b6f3-ecc8-402d-932c-e343327fcebb` · PNG `C_location-final.png` · GPT=1.
16. **Revision suite (on B):** (1) headline → Zamansız Bir Yaşam (2) logo −20% (3) remove CTA — all `IMAGE_REQUIRED`, master unchanged, source=master, quality_guard structural pass.
17. **Undo/Redo:** undo GPT=0 restored prior tip; redo GPT=0 restored latest tip.
18. **Provider calls:** generate 3 + revise 3 + undo/redo 0 = **6 total**.
19. **vs golden baseline / fail fidelity-v2:** same finished_ad GPT Image path as Quality Lock era; deliberately NOT fidelity-v2 layer templates (overflow/white boxes/gold bars). New A/B/C are for human review, not declared PASS.
20. **Final gate:** READY FOR GOLDEN CREATIVE QUALITY REVIEW — **DO NOT CLAIM VISUAL QUALITY PASS.**

## Artifacts

`artifacts/golden-creative-quality-lock/` — A/B/C PNGs + JSON + revision PNGs + `summary.json` / `report.json`
