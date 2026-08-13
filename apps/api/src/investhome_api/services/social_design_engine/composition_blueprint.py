"""Internal CompositionBlueprint — how a CreativePlan fits the actual canvas.

Not a production UI object. Strategies, not five fixed templates.
Geometry is normalized 0–100 so format reflow is relational, not a stretch.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Literal

CompositionFamilyKind = Literal[
    "EDITORIAL_HERO",
    "ARCHITECTURAL_MINIMAL",
    "INVESTMENT_GRID",
    "LUXURY_BRAND",
    "LIFESTYLE_EDITORIAL",
    "SPLIT_LAYOUT",
    "OVERLAY_PANEL",
    "STATEMENT_LAYOUT",
    "ASYMMETRIC_EDITORIAL",
    "LOWER_THIRD",
    "FLOATING_DATA",
    "IMAGE_DOMINANT",
]

COMPOSITION_FAMILIES: frozenset[str] = frozenset(
    {
        "EDITORIAL_HERO",
        "ARCHITECTURAL_MINIMAL",
        "INVESTMENT_GRID",
        "LUXURY_BRAND",
        "LIFESTYLE_EDITORIAL",
        "SPLIT_LAYOUT",
        "OVERLAY_PANEL",
        "STATEMENT_LAYOUT",
        "ASYMMETRIC_EDITORIAL",
        "LOWER_THIRD",
        "FLOATING_DATA",
        "IMAGE_DOMINANT",
    }
)

HeadlineRegionKind = Literal[
    "top_left",
    "top",
    "top_right",
    "left",
    "right",
    "center",
    "bottom_left",
    "bottom",
    "lower_third",
    "asymmetric_offset",
]
MetricRegionKind = Literal[
    "none",
    "lower_band",
    "side_panel",
    "floating_group",
    "grid_block",
    "under_headline",
    "split_column",
]
CtaPlacementKind = Literal[
    "none",
    "under_headline",
    "bottom",
    "panel",
    "opposite_brand",
    "lower_third",
]
BrandLockupKind = Literal["none", "horizontal", "stacked", "compact"]
MetricLayoutKind = Literal[
    "HORIZONTAL_ROW",
    "2X2_GRID",
    "VERTICAL_STACK",
    "FLOATING_GROUP",
    "SIDE_PANEL",
]
SplitRatioKind = Literal["30/70", "40/60", "50/50"]
GroupKind = Literal["HEADLINE", "METRIC", "BRAND_LOCKUP", "CTA", "SUPPORTING_COPY"]
WeightRole = Literal["dominant", "supporting", "tertiary"]
AlignKind = Literal["left", "center", "right"]

METRIC_LAYOUT_TO_ELEMENT: dict[str, str] = {
    "HORIZONTAL_ROW": "horizontal",
    "2X2_GRID": "cards",
    "VERTICAL_STACK": "stacked",
    "FLOATING_GROUP": "horizontal",
    "SIDE_PANEL": "stacked",
}


@dataclass
class NormRect:
    """Normalized canvas rectangle. Origin top-left. Units: 0–100."""

    x: float = 0.0
    y: float = 0.0
    w: float = 0.0
    h: float = 0.0

    def clamped(self) -> NormRect:
        x = max(0.0, min(100.0, float(self.x)))
        y = max(0.0, min(100.0, float(self.y)))
        w = max(0.0, min(100.0 - x, float(self.w)))
        h = max(0.0, min(100.0 - y, float(self.h)))
        return NormRect(x=x, y=y, w=w, h=h)

    def intersects(self, other: NormRect, gap: float = 0.0) -> bool:
        a = self.clamped()
        b = other.clamped()
        return not (
            a.x + a.w + gap <= b.x
            or b.x + b.w + gap <= a.x
            or a.y + a.h + gap <= b.y
            or b.y + b.h + gap <= a.y
        )

    def area(self) -> float:
        c = self.clamped()
        return max(0.0, c.w) * max(0.0, c.h)

    def center(self) -> tuple[float, float]:
        c = self.clamped()
        return (c.x + c.w / 2.0, c.y + c.h / 2.0)


@dataclass
class GridSpec:
    columns: int = 12
    rows: int = 12
    gutter: float = 1.2
    margin_x: float = 7.0
    margin_y: float = 7.0


@dataclass
class OverlayRegion:
    kind: str = "subtle-top"
    region: NormRect = field(default_factory=lambda: NormRect(0, 0, 100, 28))
    strength: str = "subtle"


@dataclass
class VisualWeight:
    dominant: str = "image"
    supporting: str = "headline"
    tertiary: str | None = None


@dataclass
class ImageCrop:
    """Relative crop of the cover. Identity crop unless the family needs a shift."""

    x: float = 0.0
    y: float = 0.0
    w: float = 100.0
    h: float = 100.0
    focal_bias: str = "center"


@dataclass
class ImageAnalysis:
    """Approximate image reading. Heuristic from asset metadata — no hardcoded project coords."""

    subject: str = "unknown"
    brightness: str = "mixed"
    busy: bool = False
    empty: bool = False
    skyline: bool = False
    horizon_y: float = 32.0
    major_lines: list[str] = field(default_factory=lambda: ["horizontal"])
    center_of_gravity: tuple[float, float] = (50.0, 52.0)
    focal_region: NormRect = field(default_factory=lambda: NormRect(22.0, 28.0, 56.0, 52.0))
    negative_space: NormRect = field(default_factory=lambda: NormRect(6.0, 6.0, 88.0, 22.0))
    safe_zones: list[NormRect] = field(default_factory=list)
    protected_focal: NormRect = field(default_factory=lambda: NormRect(22.0, 28.0, 56.0, 52.0))
    tags: list[str] = field(default_factory=list)
    filename: str = ""


@dataclass
class CompositionGroup:
    kind: GroupKind
    region: NormRect
    alignment: AlignKind = "left"
    spacing_inside: float = 1.4
    members: list[str] = field(default_factory=list)
    weight: WeightRole = "supporting"


@dataclass
class CompositionBlueprint:
    """Canvas-aware composition. Persisted; never recomputed on reload."""

    composition_family: CompositionFamilyKind
    focal_region: NormRect
    content_zone: NormRect
    negative_space: NormRect
    image_crop: ImageCrop = field(default_factory=ImageCrop)
    headline_region: NormRect = field(default_factory=NormRect)
    support_region: NormRect | None = None
    metric_region: NormRect | None = None
    brand_region: NormRect | None = None
    cta_region: NormRect | None = None
    alignment: AlignKind = "left"
    grid: GridSpec = field(default_factory=GridSpec)
    overlay_regions: list[OverlayRegion] = field(default_factory=list)
    visual_weight: VisualWeight = field(default_factory=VisualWeight)
    safe_zones: list[NormRect] = field(default_factory=list)
    groups: list[CompositionGroup] = field(default_factory=list)
    headline_region_kind: HeadlineRegionKind = "top_left"
    metric_region_kind: MetricRegionKind = "none"
    cta_placement: CtaPlacementKind = "bottom"
    brand_lockup: BrandLockupKind = "compact"
    metric_layout: MetricLayoutKind | None = None
    split_ratio: SplitRatioKind | None = None
    overlay_token: str = "subtle-top"
    format_preset: str = "square"
    decisions: list[str] = field(default_factory=list)
    diversity_key: str = ""

    def diversity_tokens(self) -> list[str]:
        return [
            self.composition_family,
            f"headline:{self.headline_region_kind}",
            f"metric:{self.metric_region_kind}",
            f"cta:{self.cta_placement}",
        ]


def _rect_from_dict(raw: Any) -> NormRect | None:
    if not isinstance(raw, dict):
        return None
    try:
        return NormRect(
            x=float(raw.get("x", 0)),
            y=float(raw.get("y", 0)),
            w=float(raw.get("w", raw.get("width", 0))),
            h=float(raw.get("h", raw.get("height", 0))),
        ).clamped()
    except (TypeError, ValueError):
        return None


def _rect_to_dict(rect: NormRect | None) -> dict[str, float] | None:
    if rect is None:
        return None
    c = rect.clamped()
    return {"x": round(c.x, 3), "y": round(c.y, 3), "w": round(c.w, 3), "h": round(c.h, 3)}


def composition_blueprint_to_dict(bp: CompositionBlueprint) -> dict[str, Any]:
    payload = asdict(bp)
    payload["focal_region"] = _rect_to_dict(bp.focal_region)
    payload["content_zone"] = _rect_to_dict(bp.content_zone)
    payload["negative_space"] = _rect_to_dict(bp.negative_space)
    payload["headline_region"] = _rect_to_dict(bp.headline_region)
    payload["support_region"] = _rect_to_dict(bp.support_region)
    payload["metric_region"] = _rect_to_dict(bp.metric_region)
    payload["brand_region"] = _rect_to_dict(bp.brand_region)
    payload["cta_region"] = _rect_to_dict(bp.cta_region)
    payload["safe_zones"] = [_rect_to_dict(z) for z in bp.safe_zones]
    payload["overlay_regions"] = [
        {
            "kind": o.kind,
            "region": _rect_to_dict(o.region),
            "strength": o.strength,
        }
        for o in bp.overlay_regions
    ]
    payload["groups"] = [
        {
            "kind": g.kind,
            "region": _rect_to_dict(g.region),
            "alignment": g.alignment,
            "spacing_inside": g.spacing_inside,
            "members": list(g.members),
            "weight": g.weight,
        }
        for g in bp.groups
    ]
    payload["image_crop"] = asdict(bp.image_crop)
    payload["visual_weight"] = asdict(bp.visual_weight)
    payload["grid"] = asdict(bp.grid)
    payload["diversity_tokens"] = bp.diversity_tokens()
    return payload


def composition_blueprint_from_dict(raw: Any) -> CompositionBlueprint | None:
    if not isinstance(raw, dict):
        return None
    family = str(raw.get("composition_family") or "")
    if family not in COMPOSITION_FAMILIES:
        return None
    headline = _rect_from_dict(raw.get("headline_region")) or NormRect(8, 8, 70, 18)
    content = _rect_from_dict(raw.get("content_zone")) or headline
    focal = _rect_from_dict(raw.get("focal_region")) or NormRect(22, 28, 56, 52)
    negative = _rect_from_dict(raw.get("negative_space")) or NormRect(6, 6, 88, 22)
    crop_raw = raw.get("image_crop") if isinstance(raw.get("image_crop"), dict) else {}
    weight_raw = raw.get("visual_weight") if isinstance(raw.get("visual_weight"), dict) else {}
    grid_raw = raw.get("grid") if isinstance(raw.get("grid"), dict) else {}
    overlays: list[OverlayRegion] = []
    for item in raw.get("overlay_regions") or []:
        if not isinstance(item, dict):
            continue
        region = _rect_from_dict(item.get("region")) or NormRect(0, 0, 100, 28)
        overlays.append(
            OverlayRegion(
                kind=str(item.get("kind") or "subtle-top"),
                region=region,
                strength=str(item.get("strength") or "subtle"),
            )
        )
    groups: list[CompositionGroup] = []
    for item in raw.get("groups") or []:
        if not isinstance(item, dict):
            continue
        region = _rect_from_dict(item.get("region"))
        if region is None:
            continue
        kind = str(item.get("kind") or "HEADLINE")
        if kind not in {"HEADLINE", "METRIC", "BRAND_LOCKUP", "CTA", "SUPPORTING_COPY"}:
            continue
        align = str(item.get("alignment") or "left")
        if align not in {"left", "center", "right"}:
            align = "left"
        weight = str(item.get("weight") or "supporting")
        if weight not in {"dominant", "supporting", "tertiary"}:
            weight = "supporting"
        groups.append(
            CompositionGroup(
                kind=kind,  # type: ignore[arg-type]
                region=region,
                alignment=align,  # type: ignore[arg-type]
                spacing_inside=float(item.get("spacing_inside") or 1.4),
                members=list(item.get("members") or []),
                weight=weight,  # type: ignore[arg-type]
            )
        )
    safe_zones = [_rect_from_dict(z) for z in (raw.get("safe_zones") or [])]
    align = str(raw.get("alignment") or "left")
    if align not in {"left", "center", "right"}:
        align = "left"
    metric_layout = raw.get("metric_layout")
    if metric_layout not in METRIC_LAYOUT_TO_ELEMENT:
        metric_layout = None
    split = raw.get("split_ratio")
    if split not in {"30/70", "40/60", "50/50"}:
        split = None
    try:
        return CompositionBlueprint(
            composition_family=family,  # type: ignore[arg-type]
            focal_region=focal,
            content_zone=content,
            negative_space=negative,
            image_crop=ImageCrop(
                x=float(crop_raw.get("x", 0) or 0),
                y=float(crop_raw.get("y", 0) or 0),
                w=float(crop_raw.get("w", 100) or 100),
                h=float(crop_raw.get("h", 100) or 100),
                focal_bias=str(crop_raw.get("focal_bias") or "center"),
            ),
            headline_region=headline,
            support_region=_rect_from_dict(raw.get("support_region")),
            metric_region=_rect_from_dict(raw.get("metric_region")),
            brand_region=_rect_from_dict(raw.get("brand_region")),
            cta_region=_rect_from_dict(raw.get("cta_region")),
            alignment=align,  # type: ignore[arg-type]
            grid=GridSpec(
                columns=int(grid_raw.get("columns") or 12),
                rows=int(grid_raw.get("rows") or 12),
                gutter=float(grid_raw.get("gutter") or 1.2),
                margin_x=float(grid_raw.get("margin_x") or 7.0),
                margin_y=float(grid_raw.get("margin_y") or 7.0),
            ),
            overlay_regions=overlays,
            visual_weight=VisualWeight(
                dominant=str(weight_raw.get("dominant") or "image"),
                supporting=str(weight_raw.get("supporting") or "headline"),
                tertiary=weight_raw.get("tertiary"),
            ),
            safe_zones=[z for z in safe_zones if z is not None],
            groups=groups,
            headline_region_kind=raw.get("headline_region_kind") or "top_left",
            metric_region_kind=raw.get("metric_region_kind") or "none",
            cta_placement=raw.get("cta_placement") or "bottom",
            brand_lockup=raw.get("brand_lockup") or "compact",
            metric_layout=metric_layout,  # type: ignore[arg-type]
            split_ratio=split,  # type: ignore[arg-type]
            overlay_token=str(raw.get("overlay_token") or "subtle-top"),
            format_preset=str(raw.get("format_preset") or "square"),
            decisions=list(raw.get("decisions") or []),
            diversity_key=str(raw.get("diversity_key") or ""),
        )
    except (TypeError, ValueError, KeyError):
        return None


def blueprint_from_post(post: dict[str, Any] | None) -> CompositionBlueprint | None:
    if not isinstance(post, dict):
        return None
    for candidate in (
        post.get("compositionBlueprint"),
        post.get("composition_blueprint"),
    ):
        bp = composition_blueprint_from_dict(candidate)
        if bp is not None:
            return bp
    meta = post.get("generationMeta") if isinstance(post.get("generationMeta"), dict) else {}
    if isinstance(meta, dict):
        bp = composition_blueprint_from_dict(meta.get("composition_blueprint"))
        if bp is not None:
            return bp
    return None
