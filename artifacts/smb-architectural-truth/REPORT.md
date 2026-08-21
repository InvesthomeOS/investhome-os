# SMB Flow + Architectural Truth Lock — Report

**Status:** READY FOR REAL SMB + ARCHITECTURAL TRUTH REVIEW  
**Visual Quality PASS declared:** NO (user visual approval required)

## Numbered report (1–28)

1. **Golden pipeline locked:** Prompt → Intent → Project Context → Drive/ML → Smart Asset Selection → CD → Production Brief → Golden Finished-Ad Provider → SMB.
2. **Default production mode:** `finished_ad` (not `editable_finished_ad`). Editable renderer is NOT primary designer.
3. **SMB production path verified (code):** Creative Studio → Social Media Builder → Project → AI Design → **Oluştur** → finished-ad canvas → revision mode → **AI ile Düzenle**.
4. **Finished-ad selected:** AI Design switches to revision mode; primary button = `AI ile Düzenle` (`revisionPrimary` / `aiRevision.submit`).
5. **Cursor artifacts = QA only** under `artifacts/smb-architectural-truth/`; real OS API path exercised end-to-end.
6. **Master fidelity:** `master_finished_ad_asset_id` set once on first finished-ad; never overwritten.
7. **Revision source:** Always MASTER + cumulative ops — never prior revision raster (`source_is_master=true` on r1–r4).
8. **Undo/Redo:** GPT=0 cursor path unchanged (not re-run in this harness; prior golden suite confirmed).
9. **Architectural Truth Lock module:** `quality_lock/architecture_truth.py` — classification, freedom levels, selection pools, fail-closed guard.
10. **Classifications used:** EXTERIOR_APPROVED / HISTORIC / ADDITION / HISTORIC_PLUS_ADDITION, INTERIOR_APPROVED, FLOORPLAN, LOCATION, NEIGHBORHOOD, LIFESTYLE, LOGO_*.
11. **Creative freedom:** LEVEL 0 STRICT (exterior), LEVEL 1 CONTROLLED (interior), LEVEL 2 CREATIVE (lifestyle/place) — wired into Design Direction + Production Brief.
12. **CD / Production Brief receive:** `asset_id`, `classification`, `architecture_locked`, `creative_freedom_level`, `project_relation`, `approved_status`.
13. **Provider prompt:** ARCHITECTURAL TRUTH LOCK block — use supplied architecture exactly; no redesign/regenerate/replace/extend/remove/reinterpret.
14. **Architecture Truth Guard:** fail-closed before/after generate; no silent publish of invented architecture.
15. **Asset authority:** Drive/ML approved project assets preferred; fake architecture fallback FORBIDDEN.
16. **Location campaigns:** choose approved exterior options A/B/C/D only — never invent Temple exterior.
17. **Historic+Addition:** required only when brief demands it; missing approved H+A → FAIL CLOSED (no invent).
18. **Unit tests:** 38 passed (`test_architectural_truth_lock` + quality lock + RI v2).
19. **Revision prompt fix:** `GptImageDesignRequest.instruction` max_length 8000→12000 + truncate safety (fixed 500s after truth prompt growth).
20. **Classify fix:** `visual_subject=INTERIOR` wins over folder `02_RENDER` (no false EXTERIOR from “render”).
21. **Live INTERIOR generate:** campaign `de913af0-de19-4986-867e-7948d0fa1439` · finished-ad · source `c3d11c35-…` · `IH_DC_TMP_001_Render_Living_Room_001.jpg` · **INTERIOR_APPROVED** · locked=true · freedom=**1**.
22. **Live revisions r1–r4:** all `IMAGE_REQUIRED`, master unchanged, source=master, quality_guard structural **pass**.
23. **Revision drift (vs master):** r1 ΔB +0.72 / ΔC +1.50 · r2 ΔB −0.44 / ΔC +0.22 · r3 ΔB +1.25 / ΔC +2.42 · r4 ΔB +5.29 / ΔC +3.34 — within guard thresholds; r4 highest drift (move headline).
24. **Live ARCHITECTURE (Historic+Addition required):** **FAIL CLOSED** — approved H+A render missing among Drive candidates; explicit missing-asset path; **no invention**.
25. **Live LOCATION:** source `299bd265-…` · `IH_DC_TMP_001_Render_Exterior_Day_004.jpg` · **EXTERIOR_APPROVED** · locked=true · freedom=**0**.
26. **Provider calls this run:** generate interior 1 + revisions 4 + location 1 = **6**; Historic+Addition generate **0** (fail-closed).
27. **Kept intact:** Golden finished-ad designer, CD, Production Brief, Drive/ML, Smart Asset Selection, Claim/Language/Logo locks, RI v2, Right Edit Panel, Bottom Bar, Undo/Redo, master strategy.
28. **Not done / not claimed:** Visual Quality PASS; full interactive browser SMB screenshots in this pass (API = same guards SMB uses); editable primary designer; invented Addition.

## Artifacts

`artifacts/smb-architectural-truth/` — PNGs, JSON guards, `summary.json`, `run_live_truth.py`

## Final

**FINAL STATUS: READY FOR REAL SMB + ARCHITECTURAL TRUTH REVIEW**  
**DO NOT CLAIM VISUAL QUALITY PASS.**  
**USER VISUAL APPROVAL REQUIRED.**
