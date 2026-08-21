# Editability report — Editable Layer Fidelity v2

## Layer counts (live Temple)

| Design | Total | Text | Logo | Shape | Overlay/Gradient | CTA | Badge | Raster decorative |
|--------|------:|-----:|-----:|------:|-----------------:|----:|------:|------------------:|
| A Lifestyle | 11 | 4 | 1 | 2 | 2 | 1 | 0 | 0 |
| B Price | 15 | 7 | 1 | 3 | 1 | 1 | 1 | 0 |
| C Location | 11 | 4 | 1 | 2 | 2 | 1 | 0 | 0 |

## Semantic editability
- Headline, supporting copy, prices, badge, CTA, logo: editable layers
- Gradients/overlays/frames/dividers: editable SHAPE primitives (not baked into master photo)
- Master background: locked; revisions do not re-rasterize photograph for LAYER_ONLY

## A revision regression (LAYER_ONLY)
1. Headline → "Zamansız Bir Yaşam" — GPT=0, unexpected_mutation=0, bg asset unchanged
2. Logo +20% — GPT=0, unexpected_mutation=0, bg asset unchanged
3. CTA → "Detayları İncele" — GPT=0, unexpected_mutation=0, bg asset unchanged

Background pixel diff expectation: **0** (master_background asset_id preserved).
GPT Image during layer revisions: **0**.
