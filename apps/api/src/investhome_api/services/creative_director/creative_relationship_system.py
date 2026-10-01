"""CreativeRelationshipGraphV1, CreativeGroupV2, gravity, and reading flow."""

from __future__ import annotations

from typing import Any


def relationship(
    relationship_type: str,
    source: str,
    target: str,
    *,
    strength: float,
    visual_reason: str,
    preferred_distance: float,
    preferred_alignment: str,
    allowed_variance: float = 0.04,
    collision_behavior: str = "KEEP_GROUP",
    responsive_behavior: str = "SCALE_AS_UNIT",
) -> dict[str, Any]:
    return {
        "relationship_type": relationship_type,
        "source_element": source,
        "target_element": target,
        "strength": round(strength, 3),
        "visual_reason": visual_reason,
        "preferred_distance": preferred_distance,
        "preferred_alignment": preferred_alignment,
        "allowed_variance": allowed_variance,
        "collision_behavior": collision_behavior,
        "responsive_behavior": responsive_behavior,
    }


def temple_relationship_graph(*, mode: str) -> dict[str, Any]:
    edges = [
        relationship("CONNECTED_TO", "headline_alirken", "headline_kazan", strength=1.0, visual_reason="campaign pair", preferred_distance=0.02, preferred_alignment="left"),
        relationship("BELONGS_TO", "discount", "offer_group", strength=1.0, visual_reason="offer statement", preferred_distance=0.01, preferred_alignment="lockup"),
        relationship("BELONGS_TO", "price", "offer_group", strength=1.0, visual_reason="offer statement", preferred_distance=0.02, preferred_alignment="lockup"),
        relationship("SUPPORTS", "unit_type", "price", strength=0.85, visual_reason="unit qualifies price", preferred_distance=0.018, preferred_alignment="left"),
        relationship("ANCHORED_TO", "campaign_group", "architecture_axis", strength=0.9, visual_reason="campaign rides architecture", preferred_distance=0.06, preferred_alignment="edge"),
        relationship("BALANCES", "brand_group", "campaign_group", strength=0.88, visual_reason="logo is counterweight not free rectangle", preferred_distance=0.08, preferred_alignment="baseline"),
        relationship("CLOSES", "cta", "reading_flow", strength=0.95, visual_reason="editorial closure", preferred_distance=0.03, preferred_alignment="lockup"),
        relationship("CONNECTS", "graphic_rule", "price", strength=0.7, visual_reason="rule binds offer", preferred_distance=0.01, preferred_alignment="width"),
        relationship("PROTECTS", "negative_space", "architecture", strength=0.92, visual_reason="architecture remains readable", preferred_distance=0.12, preferred_alignment="center"),
        relationship("BALANCES", "commercial_group", "architecture_mass", strength=0.8, visual_reason="mass equilibrium", preferred_distance=0.18, preferred_alignment="axis"),
        relationship("ALIGNS_WITH", "type_group", "architectural_edge", strength=0.75, visual_reason="type meets architecture", preferred_distance=0.04, preferred_alignment="edge"),
        relationship("SHARES_BASELINE_WITH", "logo", "brand_caption", strength=0.6, visual_reason="brand system", preferred_distance=0.02, preferred_alignment="baseline"),
    ]
    if mode == "GROUND_PLANE":
        edges.append(relationship("ANCHORED_TO", "offer_group", "ground_plane", strength=0.95, visual_reason="ground lockup", preferred_distance=0.04, preferred_alignment="horizon"))
    else:
        edges.append(relationship("CONNECTED_TO", "offer_group", "campaign_group", strength=0.96, visual_reason="offer continues campaign column", preferred_distance=0.04, preferred_alignment="left"))
    return {"schema": "CreativeRelationshipGraphV1", "mode": mode, "edges": edges}


def group_v2(
    group_id: str,
    children: list[str],
    bbox: tuple[float, float, float, float],
    *,
    visual_mass: float,
    priority: int,
    anchor: str,
    relationship_to_photo: str,
    relationship_to_other_groups: str,
    minimum_clear_space: float = 0.03,
    maximum_separation: float = 0.08,
    internal_alignment: str = "left",
    internal_spacing: float = 0.012,
) -> dict[str, Any]:
    x, y, w, h = bbox
    return {
        "schema": "CreativeGroupV2",
        "group_id": group_id,
        "children": children,
        "group_bbox": {"x": round(x, 4), "y": round(y, 4), "w": round(w, 4), "h": round(h, 4)},
        "internal_grid": "stack" if h >= w else "row",
        "internal_alignment": internal_alignment,
        "internal_spacing_system": internal_spacing,
        "visual_mass": round(visual_mass, 4),
        "priority": priority,
        "anchor": anchor,
        "relationship_to_photo": relationship_to_photo,
        "relationship_to_other_groups": relationship_to_other_groups,
        "minimum_clear_space": minimum_clear_space,
        "maximum_separation": maximum_separation,
    }


def _mask_com(mask: Any) -> tuple[float, float]:
    from PIL import Image

    if not isinstance(mask, Image.Image):
        return 0.52, 0.48
    small = mask.convert("L").resize((40, 50), Image.Resampling.BOX)
    px = small.load()
    acc_x = acc_y = wsum = 0.0
    for y in range(small.height):
        for x in range(small.width):
            v = int(px[x, y])
            if v < 40:
                continue
            acc_x += x * v
            acc_y += y * v
            wsum += v
    if wsum <= 0:
        return 0.52, 0.48
    return round(acc_x / wsum / max(small.width - 1, 1), 4), round(acc_y / wsum / max(small.height - 1, 1), 4)


def compositional_gravity(occupancy: Any, objects: dict[str, Any]) -> dict[str, Any]:
    occ = occupancy if isinstance(occupancy, dict) else {}
    layers = occ.get("layers") or {}
    photo = _mask_com(layers.get("hard_protected") or layers.get("collision_core"))
    arch_x = float(occ.get("architecture_centroid_x") or photo[0])
    arch = (round(arch_x, 4), round(photo[1], 4))

    def _com(roles: tuple[str, ...]) -> tuple[float, float]:
        acc_x = acc_y = area = 0.0
        for role in roles:
            box = (objects.get(role) or {}).get("bounds") or {}
            w = float(box.get("w") or 0)
            h = float(box.get("h") or 0)
            if w <= 0 or h <= 0:
                continue
            acc_x += (float(box["x"]) + w / 2) * w * h
            acc_y += (float(box["y"]) + h / 2) * w * h
            area += w * h
        if area <= 0:
            return 0.5, 0.5
        return round(acc_x / area, 4), round(acc_y / area, 4)

    type_c = _com(("headline", "unit_type", "cta", "discount_label"))
    commercial_c = _com(("price", "discount", "discount_label", "unit_type"))
    graphic_c = (0.22, 0.18)
    overall = (
        round((photo[0] * 0.45 + type_c[0] * 0.2 + commercial_c[0] * 0.2 + arch[0] * 0.15), 4),
        round((photo[1] * 0.45 + type_c[1] * 0.2 + commercial_c[1] * 0.2 + arch[1] * 0.15), 4),
    )
    return {
        "schema": "CompositionalGravityEngineV1",
        "photo_center_of_mass": [round(photo[0], 4), round(photo[1], 4)],
        "architecture_center_of_mass": [round(arch[0], 4), round(arch[1], 4)],
        "graphic_center_of_mass": graphic_c,
        "type_center_of_mass": type_c,
        "commercial_center_of_mass": commercial_c,
        "overall_center_of_mass": overall,
        "corner_fill_forbidden": True,
    }


def reading_flow(objects: dict[str, Any]) -> dict[str, Any]:
    order = ("headline", "discount", "price", "project_logo", "unit_type", "cta")
    commercial = {"headline", "discount", "price", "unit_type", "cta"}
    points = []
    for role in order:
        box = (objects.get(role) or {}).get("bounds") or {}
        if not box:
            continue
        points.append((role, float(box["x"]) + float(box["w"]) / 2, float(box["y"]) + float(box["h"]) / 2))
    jumps = []
    dead_ends = []
    for i in range(len(points) - 1):
        a, b = points[i], points[i + 1]
        dist = ((a[1] - b[1]) ** 2 + (a[2] - b[2]) ** 2) ** 0.5
        jumps.append({"from": a[0], "to": b[0], "jump_distance": round(dist, 4)})
        pair = a[0] in commercial and b[0] in commercial
        if pair and dist > 0.42:
            dead_ends.append(f"{a[0]}->{b[0]}")
        if (not pair) and dist > 0.62:
            dead_ends.append(f"{a[0]}->{b[0]}")
    islands = [j for j in jumps if j["from"] in commercial and j["to"] in commercial and j["jump_distance"] > 0.38]
    return {
        "schema": "CreativeReadingFlowV1",
        "required_flow": [
            "ARCHITECTURE / CAMPAIGN IDEA",
            "ALIRKEN KAZAN",
            "%35 LANSMAN AVANTAJI",
            "675.000 USD",
            "THE TEMPLE BRAND",
            "2+1",
            "PROJEYİ KEŞFET",
        ],
        "reading_path": [p[0] for p in points],
        "jumps": jumps,
        "hierarchy_transition": "campaign_to_offer_to_brand_to_action",
        "visual_interruption": bool(islands),
        "dead_end": dead_ends,
        "return_path": [],
        "commercial_islands": bool(islands),
        "rejected": bool(dead_ends),
    }


def graph_from_reference_map(cmap: dict[str, Any]) -> dict[str, Any]:
    groups = list(cmap.get("primary_secondary_tertiary_groups") or [])
    edges = []
    if len(groups) >= 2:
        edges.append(relationship("CONNECTED_TO", groups[0]["role"], groups[1]["role"], strength=0.9, visual_reason="primary leads secondary", preferred_distance=float(cmap.get("distance_related") or 0.12), preferred_alignment="axis"))
    if len(groups) >= 3:
        edges.append(relationship("CLOSES", groups[2]["role"], groups[0]["role"], strength=0.7, visual_reason="tertiary closes reading", preferred_distance=float(cmap.get("distance_unrelated") or 0.2), preferred_alignment="flow"))
    edges.append(relationship("PROTECTS", "negative_space", "photo_mass", strength=0.85, visual_reason=str(cmap.get("negative_space_function") or "protects_photo"), preferred_distance=0.1, preferred_alignment="center"))
    edges.append(relationship("BALANCES", "typographic_mass", "photo_mass", strength=0.8, visual_reason="mass equilibrium", preferred_distance=0.18, preferred_alignment="axis"))
    return {
        "schema": "CreativeRelationshipGraphV1",
        "filename": cmap.get("filename"),
        "axis": cmap.get("dominant_compositional_axis"),
        "edges": edges,
        "groups": groups,
        "gravity": cmap.get("center_of_visual_gravity"),
    }


def groups_from_objects(objects: dict[str, Any], *, mode: str) -> list[dict[str, Any]]:
    def union(roles: tuple[str, ...]) -> tuple[float, float, float, float]:
        boxes = []
        for role in roles:
            b = (objects.get(role) or {}).get("bounds")
            if b:
                boxes.append(b)
        if not boxes:
            return 0.0, 0.0, 0.0, 0.0
        x0 = min(float(b["x"]) for b in boxes)
        y0 = min(float(b["y"]) for b in boxes)
        x1 = max(float(b["x"]) + float(b["w"]) for b in boxes)
        y1 = max(float(b["y"]) + float(b["h"]) for b in boxes)
        return x0, y0, x1 - x0, y1 - y0

    campaign = union(("headline",))
    language = mode in {"APPROVED_CONCEPT_3", "DAY007_NATIVE_APERTURE"}
    offer = union(("discount", "discount_label", "price", "unit_type")) if language else union(("discount", "discount_label", "price"))
    brand = union(("project_logo", "brand_caption")) if objects.get("brand_caption") else union(("project_logo",))
    action = union(("cta",)) if language else union(("unit_type", "cta"))
    photo_rel = "curved_editorial_aperture" if language else ("sky_veil" if mode != "GROUND_PLANE" else "ground_plane")
    groups = [
        group_v2("CAMPAIGN_GROUP", ["headline"], campaign, visual_mass=campaign[2] * campaign[3], priority=1, anchor="architecture_edge", relationship_to_photo=photo_rel, relationship_to_other_groups="leads_offer"),
        group_v2("OFFER_GROUP", ["discount", "discount_label", "price"] + (["unit_type"] if language else []), offer, visual_mass=offer[2] * offer[3], priority=2, anchor="campaign_group", relationship_to_photo=photo_rel, relationship_to_other_groups="continues_campaign"),
        group_v2("BRAND_GROUP", ["project_logo"] + (["brand_caption"] if objects.get("brand_caption") else []), brand, visual_mass=brand[2] * brand[3], priority=0 if language else 3, anchor="upper_brand_zone" if language else "campaign_baseline", relationship_to_photo=photo_rel, relationship_to_other_groups="opens_column" if language else "balances_campaign"),
        group_v2("ACTION_GROUP", ["cta"] if language else ["unit_type", "cta"], action, visual_mass=action[2] * action[3], priority=4, anchor="offer_closure", relationship_to_photo=photo_rel, relationship_to_other_groups="closes_flow"),
    ]
    if objects.get("editorial_closure"):
        closure = union(("editorial_closure",))
        groups.append(
            group_v2(
                "EDITORIAL_CLOSURE_GROUP",
                ["editorial_closure"],
                closure,
                visual_mass=closure[2] * closure[3],
                priority=5,
                anchor="bottom_canvas",
                relationship_to_photo="spans_field_photo_transition",
                relationship_to_other_groups="canvas_closure",
            )
        )
    if language:
        order = ["BRAND_GROUP", "CAMPAIGN_GROUP", "OFFER_GROUP", "ACTION_GROUP", "EDITORIAL_CLOSURE_GROUP"]
        by_id = {g["group_id"]: g for g in groups}
        groups = [by_id[k] for k in order if k in by_id]
    return groups


def concept3_relationship_graph() -> dict[str, Any]:
    edges = [
        relationship("OPENS", "brand_group", "campaign_group", strength=0.9, visual_reason="upper brand zone leads the left editorial column", preferred_distance=0.06, preferred_alignment="left"),
        relationship("CONNECTED_TO", "headline_alirken_kazan", "campaign_group", strength=1.0, visual_reason="single-line campaign statement", preferred_distance=0.01, preferred_alignment="left"),
        relationship("CONNECTED_TO", "offer_group", "campaign_group", strength=0.96, visual_reason="offer continues the vertical commercial story", preferred_distance=0.04, preferred_alignment="left"),
        relationship("BELONGS_TO", "discount", "offer_group", strength=1.0, visual_reason="advantage leads the offer", preferred_distance=0.01, preferred_alignment="lockup"),
        relationship("BELONGS_TO", "price", "offer_group", strength=1.0, visual_reason="price is the commercial proof", preferred_distance=0.02, preferred_alignment="lockup"),
        relationship("SUPPORTS", "unit_type", "price", strength=0.9, visual_reason="unit qualifies price inside the offer column", preferred_distance=0.018, preferred_alignment="left"),
        relationship("CLOSES", "cta", "reading_flow", strength=0.95, visual_reason="outlined editorial CTA closes the commercial story", preferred_distance=0.04, preferred_alignment="left"),
        relationship("CLOSES", "editorial_closure", "canvas", strength=0.88, visual_reason="bottom editorial statement closes the whole canvas", preferred_distance=0.08, preferred_alignment="center"),
        relationship("ANCHORED_TO", "gold_arc", "dark_field_edge", strength=1.0, visual_reason="arc is the photographic aperture, not a sidebar rule", preferred_distance=0.0, preferred_alignment="curve"),
        relationship("INTERACTS_WITH", "dark_field", "photograph", strength=0.94, visual_reason="field is a feathered tonal overlay, photo remains perceptible", preferred_distance=0.0, preferred_alignment="overlap"),
        relationship("BALANCES", "commercial_column", "spire_axis", strength=0.9, visual_reason="left editorial mass against the architectural spire", preferred_distance=0.22, preferred_alignment="axis"),
        relationship("PROTECTS", "left_breathing_space", "type_column", strength=0.86, visual_reason="deliberate left margin is compositional, not leftover", preferred_distance=0.05, preferred_alignment="left"),
    ]
    return {"schema": "CreativeRelationshipGraphV1", "mode": "APPROVED_CONCEPT_3", "edges": edges}
