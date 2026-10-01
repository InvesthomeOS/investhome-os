"""Creative Master Library — approved visual systems for production.

Masters are professionally designed editable scenes. The user never sees
master names. Production routing is not activated until human approval.
"""

from __future__ import annotations

import re
from typing import Any
from uuid import uuid5, NAMESPACE_URL

from investhome_api.services.creative_director.phase5_workflow import REQUIRED_FACTS

CANVAS = {"width": 1088, "height": 1360, "aspect": "4:5"}
APPROVAL_CANDIDATE = "CANDIDATE_PENDING_HUMAN_REVIEW"
APPROVAL_APPROVED = "APPROVED"

MASTER_EDITORIAL_ID = str(uuid5(NAMESPACE_URL, "investhome:creative-master:editorial-architectural-v1"))
MASTER_COMMERCIAL_ID = str(uuid5(NAMESPACE_URL, "investhome:creative-master:premium-commercial-v1"))
MASTER_MINIMAL_ID = str(uuid5(NAMESPACE_URL, "investhome:creative-master:minimal-luxury-v1"))
MASTER_COMMERCIAL_FINAL_ID = str(
    uuid5(NAMESPACE_URL, "investhome:creative-master:premium-commercial-v1-final-54a")
)
MASTER_COMMERCIAL_R1_ID = str(
    uuid5(NAMESPACE_URL, "investhome:creative-master:premium-commercial-v1-final-54a-r1")
)
MASTER_PRICE_REVISION_V2_ID = str(
    uuid5(NAMESPACE_URL, "investhome:creative-master:premium-commercial-v1-r1-price-revision-v2")
)

APPROVED_R1_ASSET_ID = "32f6deee-ca4d-45a5-8dc3-303052609d35"

SEMANTIC_SLOTS = (
    "headline",
    "price",
    "discount",
    "discount_label",
    "unit_type",
    "cta",
    "project_logo",
    "project_photo",
)


def _facts(facts: dict[str, str] | None = None) -> dict[str, str]:
    data = dict(REQUIRED_FACTS)
    if facts:
        data.update(facts)
    return data


def _shell(body: str, extra_css: str) -> str:
    return f"""<!DOCTYPE html>
<html lang="tr">
<head>
<meta charset="utf-8"/>
<style>
html,body{{margin:0;padding:0;width:1088px;height:1360px;overflow:hidden;background:#0c0e12;}}
{{{{FONT_CSS}}}}
#stage{{position:relative;width:1088px;height:1360px;overflow:hidden;}}
img[data-semantic="project_photo"]{{position:absolute;inset:0;width:1088px;height:1360px;object-fit:fill;display:block;}}
[data-semantic="project_logo"] svg{{width:100%;height:auto;display:block;max-height:52px;}}
{extra_css}
</style>
</head>
<body>
<div id="stage">{body}</div>
</body>
</html>
"""


def scene_editorial_architectural(facts: dict[str, str] | None = None) -> str:
    """Architecture-magazine system. Type lives in the right sky, clear of the spire.

    Reconstructs Phase 5.0 design behavior: large editorial display, one commercial
    lockup, restrained gold, photographic integration. Does not copy 5.0 pixels.
    """
    f = _facts(facts)
    css = """
.air{position:absolute;inset:0;background:linear-gradient(90deg,transparent 64%,rgba(232,226,214,.07) 100%);pointer-events:none;}
.logo{position:absolute;right:48px;top:32px;width:128px;}
.col{position:absolute;right:44px;top:88px;width:400px;color:#161C24;text-align:left;}
.kicker{font-family:'Source Sans 3',sans-serif;font-weight:500;font-size:12px;letter-spacing:.46em;color:#161C24;}
.display{font-family:'Cormorant Garamond',serif;font-weight:600;font-size:64px;line-height:.84;letter-spacing:.02em;margin-top:4px;color:#C9A56A;}
.rule{width:36px;height:1px;background:#C9A56A;margin:12px 0 12px;border:0;}
.price{font-family:'Cormorant Garamond',serif;font-weight:500;font-size:28px;letter-spacing:.04em;line-height:1;color:#161C24;}
.meta{margin-top:8px;display:flex;align-items:baseline;gap:10px;flex-wrap:wrap;}
.discount{font-family:'Cormorant Garamond',serif;font-weight:600;font-size:20px;color:#C9A56A;letter-spacing:.04em;}
.discount-label{font-family:'Source Sans 3',sans-serif;font-weight:500;font-size:11px;letter-spacing:.20em;color:#3A414C;}
.unit{font-family:'Source Sans 3',sans-serif;font-weight:400;font-size:11px;letter-spacing:.22em;color:#3A414C;}
.cta{margin-top:12px;font-family:'Source Sans 3',sans-serif;font-weight:600;font-size:11px;letter-spacing:.36em;color:#161C24;border-bottom:1px solid #C9A56A;padding-bottom:6px;display:inline-block;}
.sr{position:absolute;width:1px;height:1px;overflow:hidden;clip:rect(0,0,0,0);}
"""
    body = f"""
<img data-semantic="project_photo" src="{{{{PHOTO_SRC}}}}" alt=""/>
<div class="air" aria-hidden="true"></div>
<div class="logo" data-semantic="project_logo">{{{{LOGO_MARKUP}}}}</div>
<div class="col">
  <div data-semantic="headline">
    <span class="sr">{f["headline"]}</span>
    <div class="kicker">ALIRKEN</div>
    <div class="display">KAZAN</div>
  </div>
  <div class="rule" aria-hidden="true"></div>
  <div class="price" data-semantic="price">{f["list_price"]}</div>
  <div class="meta">
    <span class="discount" data-semantic="discount">{f["discount"]}</span>
    <span class="discount-label" data-semantic="discount_label">{f["discount_label"]}</span>
    <span class="unit" data-semantic="unit_type">{f["unit"]} {f["unit_label"]}</span>
  </div>
  <div class="cta" data-semantic="cta">{f["cta"]}</div>
</div>
"""
    return _shell(body, css)


def scene_premium_commercial(facts: dict[str, str] | None = None) -> str:
    """Offer-led system. Price is the largest type; discount stays typographic."""
    f = _facts(facts)
    css = """
.logo{position:absolute;left:40px;top:32px;width:128px;}
.mast{position:absolute;left:40px;top:100px;width:220px;color:#161C24;}
.mast .line{font-family:'Cormorant Garamond',serif;font-weight:600;font-size:30px;line-height:.92;letter-spacing:.04em;}
.mast .unit{margin-top:14px;font-family:'Source Sans 3',sans-serif;font-weight:400;font-size:12px;letter-spacing:.24em;color:#3A414C;}
.mast .cta{margin-top:16px;font-family:'Source Sans 3',sans-serif;font-weight:600;font-size:11px;letter-spacing:.32em;color:#161C24;border-bottom:1px solid #C9A56A;padding-bottom:6px;display:inline-block;}
.lockup{position:absolute;right:44px;top:88px;width:420px;color:#161C24;}
.price{font-family:'Cormorant Garamond',serif;font-weight:600;font-size:52px;line-height:.90;letter-spacing:.01em;}
.stack{margin-top:10px;}
.discount{display:block;font-family:'Cormorant Garamond',serif;font-weight:600;font-size:32px;color:#C9A56A;letter-spacing:.02em;}
.discount-label{display:block;margin-top:4px;font-family:'Source Sans 3',sans-serif;font-weight:500;font-size:11px;letter-spacing:.24em;color:#3A414C;}
.sr{position:absolute;width:1px;height:1px;overflow:hidden;clip:rect(0,0,0,0);}
"""
    body = f"""
<img data-semantic="project_photo" src="{{{{PHOTO_SRC}}}}" alt=""/>
<div class="logo" data-semantic="project_logo">{{{{LOGO_MARKUP}}}}</div>
<div class="mast" data-semantic="headline">
  <span class="sr">{f["headline"]}</span>
  <div class="line">ALIRKEN</div>
  <div class="line">KAZAN</div>
  <div class="unit" data-semantic="unit_type">{f["unit"]} {f["unit_label"]}</div>
  <div class="cta" data-semantic="cta">{f["cta"]}</div>
</div>
<div class="lockup">
  <div class="price" data-semantic="price">{f["list_price"]}</div>
  <div class="stack">
    <span class="discount" data-semantic="discount">{f["discount"]}</span>
    <span class="discount-label" data-semantic="discount_label">{f["discount_label"]}</span>
  </div>
</div>
"""
    return _shell(body, css)


def scene_premium_commercial_final(facts: dict[str, str] | None = None) -> str:
    """Phase 5.4A child of Master B. Same split DNA; production-scale hierarchy.

    Does not replace the Phase 5.4 candidate library. CTA lives in the lower
    quiet region. Type stays off the spire. No cards, panels, or pills.
    """
    f = _facts(facts)
    css = """
.air-right{position:absolute;right:0;top:0;width:46%;height:30%;background:linear-gradient(90deg,transparent 0%,rgba(236,230,218,.10) 100%);pointer-events:none;}
.air-left{position:absolute;left:0;top:0;width:30%;height:28%;background:linear-gradient(90deg,rgba(236,230,218,.07) 0%,transparent 100%);pointer-events:none;}
.ground{position:absolute;left:0;bottom:0;width:46%;height:24%;background:linear-gradient(to top,rgba(10,12,16,.46) 0%,rgba(10,12,16,.12) 52%,transparent 100%);pointer-events:none;}
[data-semantic="project_logo"] svg{max-height:64px;}
.logo{position:absolute;left:40px;top:30px;width:156px;}
.mast{position:absolute;left:40px;top:112px;width:252px;color:#161C24;}
.mast .line{font-family:'Cormorant Garamond',serif;font-weight:600;letter-spacing:.03em;line-height:.90;}
.mast .line.a{font-size:40px;}
.mast .line.b{font-size:54px;margin-top:2px;}
.mast .rule{width:36px;height:1px;background:#C9A56A;margin:18px 0 16px;border:0;}
.mast .unit{font-family:'Source Sans 3',sans-serif;font-weight:500;font-size:14px;letter-spacing:.28em;color:#3A414C;}
.lockup{position:absolute;right:40px;top:72px;width:456px;color:#161C24;text-align:left;}
.price{font-family:'Cormorant Garamond',serif;font-weight:600;font-size:62px;line-height:.90;letter-spacing:.005em;}
.lockup .rule{width:44px;height:1px;background:#C9A56A;margin:16px 0 14px;border:0;}
.discount{display:block;font-family:'Cormorant Garamond',serif;font-weight:600;font-size:46px;color:#C9A56A;letter-spacing:.02em;line-height:.92;}
.discount-label{display:block;margin-top:8px;font-family:'Source Sans 3',sans-serif;font-weight:600;font-size:13px;letter-spacing:.26em;color:#161C24;}
.cta-wrap{position:absolute;left:40px;bottom:54px;width:420px;}
.cta{font-family:'Source Sans 3',sans-serif;font-weight:600;font-size:13px;letter-spacing:.40em;color:#F4EFE6;}
.cta:before{content:"";display:block;width:40px;height:1px;background:#C9A56A;margin-bottom:14px;}
.sr{position:absolute;width:1px;height:1px;overflow:hidden;clip:rect(0,0,0,0);}
"""
    body = f"""
<img data-semantic="project_photo" src="{{{{PHOTO_SRC}}}}" alt=""/>
<div class="air-left" aria-hidden="true"></div>
<div class="air-right" aria-hidden="true"></div>
<div class="ground" aria-hidden="true"></div>
<div class="logo" data-semantic="project_logo">{{{{LOGO_MARKUP}}}}</div>
<div class="mast" data-semantic="headline">
  <span class="sr">{f["headline"]}</span>
  <div class="line a">ALIRKEN</div>
  <div class="line b">KAZAN</div>
  <div class="rule" aria-hidden="true"></div>
  <div class="unit" data-semantic="unit_type">{f["unit"]} {f["unit_label"]}</div>
</div>
<div class="lockup">
  <div class="price" data-semantic="price">{f["list_price"]}</div>
  <div class="rule" aria-hidden="true"></div>
  <div>
    <span class="discount" data-semantic="discount">{f["discount"]}</span>
    <span class="discount-label" data-semantic="discount_label">{f["discount_label"]}</span>
  </div>
</div>
<div class="cta-wrap">
  <div class="cta" data-semantic="cta">{f["cta"]}</div>
</div>
"""
    return _shell(body, css)


def scene_premium_commercial_r1(facts: dict[str, str] | None = None) -> str:
    """Phase 5.4A-R1. Same 5.4A composition; offer grouping + CTA closure only."""
    f = _facts(facts)
    css = """
.air-right{position:absolute;right:0;top:0;width:46%;height:30%;background:linear-gradient(90deg,transparent 0%,rgba(236,230,218,.10) 100%);pointer-events:none;}
.air-left{position:absolute;left:0;top:0;width:30%;height:28%;background:linear-gradient(90deg,rgba(236,230,218,.07) 0%,transparent 100%);pointer-events:none;}
.ground{position:absolute;left:0;bottom:0;width:56%;height:30%;background:linear-gradient(to top,rgba(10,12,16,.58) 0%,rgba(10,12,16,.16) 46%,transparent 100%);pointer-events:none;}
[data-semantic="project_logo"] svg{max-height:64px;}
.logo{position:absolute;left:40px;top:30px;width:156px;}
.mast{position:absolute;left:40px;top:112px;width:252px;color:#161C24;}
.mast .line{font-family:'Cormorant Garamond',serif;font-weight:600;letter-spacing:.03em;line-height:.90;}
.mast .line.a{font-size:40px;}
.mast .line.b{font-size:54px;margin-top:2px;}
.mast .rule{width:36px;height:1px;background:#C9A56A;margin:18px 0 16px;border:0;}
.mast .unit{font-family:'Source Sans 3',sans-serif;font-weight:500;font-size:14px;letter-spacing:.28em;color:#3A414C;}
.lockup{position:absolute;right:40px;top:72px;width:456px;color:#161C24;text-align:left;}
.price{font-family:'Cormorant Garamond',serif;font-weight:600;font-size:62px;line-height:.90;letter-spacing:.005em;}
.lockup .rule{width:280px;height:1px;background:#C9A56A;margin:8px 0 10px;border:0;}
.offer{display:flex;align-items:baseline;gap:12px;}
.discount{font-family:'Cormorant Garamond',serif;font-weight:600;font-size:42px;color:#C9A56A;letter-spacing:.02em;line-height:1;}
.discount-label{font-family:'Source Sans 3',sans-serif;font-weight:600;font-size:16px;letter-spacing:.18em;color:#161C24;}
.cta-wrap{position:absolute;left:40px;bottom:118px;width:560px;}
.cta{font-family:'Source Sans 3',sans-serif;font-weight:600;font-size:20px;letter-spacing:.16em;color:#F7F2EA;display:inline-block;min-width:420px;padding:13px 0 12px;border-top:1px solid #C9A56A;border-bottom:1px solid #C9A56A;}
.sr{position:absolute;width:1px;height:1px;overflow:hidden;clip:rect(0,0,0,0);}
"""
    body = f"""
<img data-semantic="project_photo" src="{{{{PHOTO_SRC}}}}" alt=""/>
<div class="air-left" aria-hidden="true"></div>
<div class="air-right" aria-hidden="true"></div>
<div class="ground" aria-hidden="true"></div>
<div class="logo" data-semantic="project_logo">{{{{LOGO_MARKUP}}}}</div>
<div class="mast" data-semantic="headline">
  <span class="sr">{f["headline"]}</span>
  <div class="line a">ALIRKEN</div>
  <div class="line b">KAZAN</div>
  <div class="rule" aria-hidden="true"></div>
  <div class="unit" data-semantic="unit_type">{f["unit"]} {f["unit_label"]}</div>
</div>
<div class="lockup">
  <div class="price" data-semantic="price">{f["list_price"]}</div>
  <div class="rule" aria-hidden="true"></div>
  <div class="offer">
    <span class="discount" data-semantic="discount">{f["discount"]}</span>
    <span class="discount-label" data-semantic="discount_label">{f["discount_label"]}</span>
  </div>
</div>
<div class="cta-wrap">
  <div class="cta" data-semantic="cta">{f["cta"]}</div>
</div>
"""
    return _shell(body, css)


LOCKED_R1_CHROME = """
.air-right{position:absolute;right:0;top:0;width:46%;height:30%;background:linear-gradient(90deg,transparent 0%,rgba(236,230,218,.10) 100%);pointer-events:none;}
.air-left{position:absolute;left:0;top:0;width:30%;height:28%;background:linear-gradient(90deg,rgba(236,230,218,.07) 0%,transparent 100%);pointer-events:none;}
.ground{position:absolute;left:0;bottom:0;width:56%;height:30%;background:linear-gradient(to top,rgba(10,12,16,.58) 0%,rgba(10,12,16,.16) 46%,transparent 100%);pointer-events:none;}
[data-semantic="project_logo"] svg{max-height:64px;}
.logo{position:absolute;left:40px;top:30px;width:156px;}
.mast{position:absolute;left:40px;top:112px;width:252px;color:#161C24;}
.mast .line{font-family:'Cormorant Garamond',serif;font-weight:600;letter-spacing:.03em;line-height:.90;}
.mast .line.a{font-size:40px;}
.mast .line.b{font-size:54px;margin-top:2px;}
.mast .rule{width:36px;height:1px;background:#C9A56A;margin:18px 0 16px;border:0;}
.mast .unit{font-family:'Source Sans 3',sans-serif;font-weight:500;font-size:14px;letter-spacing:.28em;color:#3A414C;}
.cta-wrap{position:absolute;left:40px;bottom:118px;width:560px;}
.cta{font-family:'Source Sans 3',sans-serif;font-weight:600;font-size:20px;letter-spacing:.16em;color:#F7F2EA;display:inline-block;min-width:420px;padding:13px 0 12px;border-top:1px solid #C9A56A;border-bottom:1px solid #C9A56A;}
.sr{position:absolute;width:1px;height:1px;overflow:hidden;clip:rect(0,0,0,0);}
"""

LOCKED_R1_BODY_CHROME = """
<img data-semantic="project_photo" src="{{PHOTO_SRC}}" alt=""/>
<div class="air-left" aria-hidden="true"></div>
<div class="air-right" aria-hidden="true"></div>
<div class="ground" aria-hidden="true"></div>
<div class="logo" data-semantic="project_logo">{{LOGO_MARKUP}}</div>
"""


def scene_premium_commercial_price_revision(facts: dict[str, str] | None = None) -> str:
    """Approved R1 chrome locked. Only the commercial lockup reflows."""
    f = _facts(facts)
    launch = f.get("launch_price") or "438.750 USD"
    listed = f.get("list_price_struck") or "675.000 USD"
    savings = f.get("savings") or "236.250 USD"
    savings_label = f.get("savings_label") or "KAZANCINIZ"
    css = (
        LOCKED_R1_CHROME
        + """
.lockup{position:absolute;right:40px;top:72px;width:456px;color:#161C24;text-align:left;}
.launch{font-family:'Cormorant Garamond',serif;font-weight:600;font-size:52px;line-height:.90;letter-spacing:.005em;}
.struck{margin-top:6px;font-family:'Cormorant Garamond',serif;font-weight:500;font-size:20px;letter-spacing:.03em;color:#5C6370;text-decoration:line-through;text-decoration-color:#161C24;}
.savings{margin-top:10px;display:flex;align-items:baseline;gap:12px;}
.savings .amount{font-family:'Cormorant Garamond',serif;font-weight:600;font-size:26px;color:#C9A56A;letter-spacing:.02em;}
.savings .label{font-family:'Source Sans 3',sans-serif;font-weight:600;font-size:12px;letter-spacing:.22em;color:#161C24;}
.lockup .rule{width:280px;height:1px;background:#C9A56A;margin:10px 0 10px;border:0;}
.offer{display:flex;align-items:baseline;gap:12px;}
.discount{font-family:'Cormorant Garamond',serif;font-weight:600;font-size:36px;color:#C9A56A;letter-spacing:.02em;line-height:1;}
.discount-label{font-family:'Source Sans 3',sans-serif;font-weight:600;font-size:15px;letter-spacing:.18em;color:#161C24;}
"""
    )
    body = f"""
{LOCKED_R1_BODY_CHROME}
<div class="mast" data-semantic="headline">
  <span class="sr">{f["headline"]}</span>
  <div class="line a">ALIRKEN</div>
  <div class="line b">KAZAN</div>
  <div class="rule" aria-hidden="true"></div>
  <div class="unit" data-semantic="unit_type">{f["unit"]} {f["unit_label"]}</div>
</div>
<div class="lockup">
  <div class="launch" data-semantic="price" data-role="PRIMARY_PRICE">{launch}</div>
  <div class="struck" data-semantic="list_price" data-state="struck">{listed}</div>
  <div class="savings">
    <span class="amount" data-semantic="savings">{savings}</span>
    <span class="label" data-semantic="savings_label">{savings_label}</span>
  </div>
  <div class="rule" aria-hidden="true"></div>
  <div class="offer">
    <span class="discount" data-semantic="discount">{f["discount"]}</span>
    <span class="discount-label" data-semantic="discount_label">{f["discount_label"]}</span>
  </div>
</div>
<div class="cta-wrap">
  <div class="cta" data-semantic="cta">{f["cta"]}</div>
</div>
"""
    return _shell(body, css)


def build_premium_commercial_r1_master(facts: dict[str, str] | None = None) -> dict[str, Any]:
    f = _facts(facts)
    protected = [
        "headline must not cross the spire",
        "logo must not collide with the spire",
        "price must not destroy the primary façade",
        "CTA must not hide key project architecture",
        "no AI redraw of Day_004",
        "uniform crop/scale only",
        "preserve Phase 5.4A crop, grade, and split composition",
    ]
    return _master(
        master_id=MASTER_COMMERCIAL_R1_ID,
        name_internal="premium_commercial_v1_final_54a_r1",
        creative_family="PREMIUM_COMMERCIAL",
        scene_markup=scene_premium_commercial_r1(f),
        photo_slot={"semantic": "project_photo", "fit": "cover_locked_4x5", "hero": True},
        logo_slot={"semantic": "project_logo", "placement": "top_left_sky"},
        graphic_surfaces=["right_sky_air_veil", "left_sky_air_veil", "lower_left_photographic_fade", "gold_rules"],
        color_roles={"ink": "#161C24", "gold": "#C9A56A", "cta": "#F7F2EA", "support": "#3A414C"},
        content_capacity="price_primary_full_offer",
        adaptation_rules=[
            "Phase 5.4A composition is locked",
            "price and discount read as one offer lockup",
            "CTA is an editorial inscription closer, not a button",
            "do not introduce cards, badges, pills, or a solid panel",
        ],
        protected_photo_rules=protected,
        quality_score=9.0,
        source_provenance="phase5_4a_human_approved_base_final_art_polish",
    )


def build_premium_commercial_final_master(facts: dict[str, str] | None = None) -> dict[str, Any]:
    f = _facts(facts)
    protected = [
        "headline must not cross the spire",
        "logo must not collide with the spire",
        "price must not destroy the primary façade",
        "CTA must not hide key project architecture",
        "no AI redraw of Day_004",
        "uniform crop/scale only",
    ]
    return _master(
        master_id=MASTER_COMMERCIAL_FINAL_ID,
        name_internal="premium_commercial_v1_final_54a",
        creative_family="PREMIUM_COMMERCIAL",
        scene_markup=scene_premium_commercial_final(f),
        photo_slot={"semantic": "project_photo", "fit": "cover_locked_4x5", "hero": True},
        logo_slot={"semantic": "project_logo", "placement": "top_left_sky"},
        graphic_surfaces=["right_sky_air_veil", "left_sky_air_veil", "lower_left_photographic_fade", "gold_rules"],
        color_roles={"ink": "#161C24", "gold": "#C9A56A", "cta": "#F4EFE6", "support": "#3A414C"},
        content_capacity="price_primary_full_offer",
        adaptation_rules=[
            "preserve Master B split: brand left, offer right, architecture center, CTA lower quiet",
            "headline and price are the two major visual anchors",
            "discount stays typographic, never a medallion",
            "do not introduce cards, badges, pills, or a solid panel",
        ],
        protected_photo_rules=protected,
        quality_score=8.8,
        source_provenance="human_selected_phase5_4_master_b_production_finalization",
    )


def scene_minimal_luxury(facts: dict[str, str] | None = None) -> str:
    """Brand-led calm. Right ~55% of the frame stays photographic."""
    f = _facts(facts)
    css = """
.base{position:absolute;left:0;bottom:0;width:44%;height:30%;background:linear-gradient(to top,rgba(10,12,16,.50) 0%,rgba(10,12,16,.12) 58%,transparent 100%);pointer-events:none;}
.logo{position:absolute;left:44px;top:44px;width:132px;}
.head{position:absolute;left:44px;top:136px;width:236px;}
.head .line{font-family:'Cormorant Garamond',serif;font-weight:500;font-size:28px;line-height:.98;letter-spacing:.16em;color:#161C24;}
.quiet{position:absolute;left:44px;bottom:64px;width:360px;color:#F4EFE6;}
.price{font-family:'Cormorant Garamond',serif;font-weight:500;font-size:26px;letter-spacing:.08em;}
.meta{margin-top:12px;font-family:'Source Sans 3',sans-serif;font-weight:400;font-size:11px;letter-spacing:.20em;color:#E4DCCF;}
.discount{color:#C9A56A;letter-spacing:.16em;}
.cta{margin-top:20px;font-family:'Source Sans 3',sans-serif;font-weight:500;font-size:11px;letter-spacing:.38em;color:#F4EFE6;}
.sr{position:absolute;width:1px;height:1px;overflow:hidden;clip:rect(0,0,0,0);}
"""
    body = f"""
<img data-semantic="project_photo" src="{{{{PHOTO_SRC}}}}" alt=""/>
<div class="base" aria-hidden="true"></div>
<div class="logo" data-semantic="project_logo">{{{{LOGO_MARKUP}}}}</div>
<div class="head" data-semantic="headline">
  <span class="sr">{f["headline"]}</span>
  <div class="line">ALIRKEN</div>
  <div class="line">KAZAN</div>
</div>
<div class="quiet">
  <div class="price" data-semantic="price">{f["list_price"]}</div>
  <div class="meta">
    <span data-semantic="discount" class="discount">{f["discount"]}</span>
    <span data-semantic="discount_label"> {f["discount_label"]}</span>
    <span>  ·  </span>
    <span data-semantic="unit_type">{f["unit"]} {f["unit_label"]}</span>
  </div>
  <div class="cta" data-semantic="cta">{f["cta"]}</div>
</div>
"""
    return _shell(body, css)


def _master(
    *,
    master_id: str,
    name_internal: str,
    creative_family: str,
    scene_markup: str,
    photo_slot: dict[str, Any],
    logo_slot: dict[str, Any],
    graphic_surfaces: list[str],
    color_roles: dict[str, str],
    content_capacity: str,
    adaptation_rules: list[str],
    protected_photo_rules: list[str],
    quality_score: float,
    source_provenance: str,
) -> dict[str, Any]:
    return {
        "schema": "CreativeMasterSceneV1",
        "master_id": master_id,
        "name_internal": name_internal,
        "creative_family": creative_family,
        "canvas_ratio": "4:5",
        "canvas": dict(CANVAS),
        "scene_markup": scene_markup,
        "scene_type": "HTML_SVG",
        "semantic_slots": list(SEMANTIC_SLOTS),
        "photo_slots": [photo_slot],
        "logo_slot": logo_slot,
        "typography_roles": {
            "DISPLAY_SERIF": "Cormorant Garamond",
            "EDITORIAL_SANS": "Source Sans 3",
        },
        "font_roles": {
            "headline": "DISPLAY_SERIF",
            "price": "DISPLAY_SERIF",
            "discount": "DISPLAY_SERIF",
            "support": "EDITORIAL_SANS",
            "cta": "EDITORIAL_SANS",
        },
        "graphic_surfaces": graphic_surfaces,
        "color_roles": color_roles,
        "content_capacity": content_capacity,
        "adaptation_rules": adaptation_rules,
        "protected_photo_rules": protected_photo_rules,
        "quality_score": quality_score,
        "approval_status": APPROVAL_CANDIDATE,
        "source_provenance": source_provenance,
        "created_at": None,
    }


def build_creative_master_library(facts: dict[str, str] | None = None) -> dict[str, Any]:
    f = _facts(facts)
    protected = [
        "headline must not cross the spire",
        "logo must not collide with the spire",
        "price must not destroy the primary façade",
        "CTA must not hide key project architecture",
        "no AI redraw of Day_004",
        "uniform crop/scale only",
    ]
    masters = [
        _master(
            master_id=MASTER_EDITORIAL_ID,
            name_internal="editorial_architectural_v1",
            creative_family="EDITORIAL_ARCHITECTURAL",
            scene_markup=scene_editorial_architectural(f),
            photo_slot={"semantic": "project_photo", "fit": "cover_locked_4x5", "hero": True},
            logo_slot={"semantic": "project_logo", "placement": "top_right_sky"},
            graphic_surfaces=["right_sky_air_veil", "single_gold_rule"],
            color_roles={"ink": "#161C24", "gold": "#C9A56A", "support": "#3A414C"},
            content_capacity="full_campaign_story_as_one_right_lockup",
            adaptation_rules=[
                "headline may scale 88–120px",
                "commercial group stays one column",
                "do not introduce cards, badges, or a solid panel",
                "keep type in the right sky, clear of the spire",
            ],
            protected_photo_rules=protected,
            quality_score=9.0,
            source_provenance="phase5_0_design_behavior_reconstructed_not_pixels",
        ),
        _master(
            master_id=MASTER_COMMERCIAL_ID,
            name_internal="premium_commercial_v1",
            creative_family="PREMIUM_COMMERCIAL",
            scene_markup=scene_premium_commercial(f),
            photo_slot={"semantic": "project_photo", "fit": "cover_locked_4x5", "hero": True},
            logo_slot={"semantic": "project_logo", "placement": "top_left_sky"},
            graphic_surfaces=["none_price_led_typography_only"],
            color_roles={"ink": "#161C24", "gold": "#C9A56A", "support": "#3A414C"},
            content_capacity="price_primary_full_offer",
            adaptation_rules=[
                "price is the largest type and may scale 56–76px",
                "discount stays typographic, never a medallion",
                "masthead remains left of the spire",
                "commercial lockup remains one right-side system",
            ],
            protected_photo_rules=protected,
            quality_score=8.6,
            source_provenance="purpose_designed_premium_offer_system",
        ),
        _master(
            master_id=MASTER_MINIMAL_ID,
            name_internal="minimal_luxury_v1",
            creative_family="MINIMAL_LUXURY",
            scene_markup=scene_minimal_luxury(f),
            photo_slot={"semantic": "project_photo", "fit": "cover_locked_4x5", "hero": True},
            logo_slot={"semantic": "project_logo", "placement": "top_left_sky_small"},
            graphic_surfaces=["lower_left_photographic_fade"],
            color_roles={"headline": "#161C24", "ink": "#F4EFE6", "gold": "#C9A56A"},
            content_capacity="low_copy_brand_led",
            adaptation_rules=[
                "do not add surfaces",
                "keep the right 55% of the frame free of type",
                "headline stays a single modest line in the left sky",
                "commercial lockup stays compact at the lower left",
            ],
            protected_photo_rules=protected,
            quality_score=8.4,
            source_provenance="purpose_designed_minimal_luxury_system",
        ),
    ]
    return {
        "schema": "CreativeMasterLibraryV1",
        "approval_policy": "only_APPROVED_masters_may_enter_production",
        "user_facing_templates": False,
        "live_routing_active": False,
        "reference_library": build_creative_reference_library(),
        "learning_store": empty_learning_store(),
        "masters": masters,
    }


def build_creative_reference_library() -> dict[str, Any]:
    """References inform master design and later family currency. Never generate production scenes."""
    return {
        "schema": "CreativeReferenceLibraryV1",
        "purpose": ["designing_new_masters", "evaluating_whether_a_master_family_remains_visually_current"],
        "forbidden_use": "do_not_generate_production_scenes_from_zero",
        "entries": [
            {
                "reference_id": "phase5_0_quality_bar",
                "asset_id": "3647f302-325a-4f12-b3e6-07b005131485",
                "use": "design_behavior_only",
                "do_not_copy": "generated_building_pixels",
                "learn": [
                    "large editorial display",
                    "one commercial lockup",
                    "restrained gold",
                    "logo as quiet brand mark",
                    "CTA as composition, not a dashboard widget",
                    "photograph remains the hero",
                ],
            }
        ],
    }


def empty_learning_store() -> dict[str, Any]:
    return {
        "schema": "CreativeMasterLearningStoreV1",
        "ml_training_active": False,
        "records": [],
    }


def record_master_outcome(store: dict[str, Any], record: dict[str, Any]) -> dict[str, Any]:
    """Store routing/approval outcomes. Does not train a model."""
    blob = dict(store or empty_learning_store())
    records = list(blob.get("records") or [])
    records.append(
        {
            "selected_master_id": record.get("selected_master_id"),
            "adaptations": record.get("adaptations") or [],
            "revision_history": record.get("revision_history") or [],
            "final_visual_asset_id": record.get("final_visual_asset_id"),
            "approval": record.get("approval"),
            "project_type": record.get("project_type"),
            "campaign_type": record.get("campaign_type"),
            "revision_count": record.get("revision_count"),
        }
    )
    blob["records"] = records
    blob["ml_training_active"] = False
    return blob


def route_creative_master(
    *,
    user_brief: str,
    library: dict[str, Any] | None = None,
    target_ratio: str = "4:5",
    campaign_goal: str | None = None,
) -> dict[str, Any]:
    """Internal router. Never exposed as a template picker."""
    blob = library or build_creative_master_library()
    masters = [m for m in blob.get("masters") or [] if m.get("approval_status") in {APPROVAL_APPROVED, APPROVAL_CANDIDATE}]
    by_family = {str(m.get("creative_family")): m for m in masters}
    text = f"{user_brief} {campaign_goal or ''} {target_ratio}".casefold()
    if any(k in text for k in ("minimal", "sade", "marka", "brand", "sessiz", "az metin", "luxury calm")):
        chosen = by_family.get("MINIMAL_LUXURY") or masters[-1]
        reason = "Brand-led / low-copy brief routes to Minimal Luxury."
    elif any(k in text for k in ("fiyat", "price", "lansman", "%35", "indirim", "teklif", "offer", "675", "avantaj")):
        chosen = by_family.get("PREMIUM_COMMERCIAL") or masters[1]
        reason = "Price- and offer-led brief routes to Premium Commercial."
    else:
        chosen = by_family.get("EDITORIAL_ARCHITECTURAL") or masters[0]
        reason = "Architecture-led / default campaign brief routes to Editorial Architectural."
    return {
        "schema": "CreativeMasterRouterV1",
        "selected_master_id": chosen.get("master_id"),
        "selected_family": chosen.get("creative_family"),
        "selection_reason": reason,
        "adaptation_plan": {
            "preserve_creative_dna": True,
            "allowed": ["headline scale", "copy length", "photo crop within lock", "CTA width", "logo scale", "spacing"],
            "forbidden": ["replace master layout", "invent a new visual system", "generate architecture"],
            "ratio": target_ratio,
        },
        "user_visible": False,
        "live_routing_active": False,
    }


def markup_has_semantic_slots(markup: str) -> bool:
    return all(
        f'data-semantic="{slot}"' in markup or f"data-semantic='{slot}'" in markup for slot in SEMANTIC_SLOTS
    )


def families_are_distinct(library: dict[str, Any]) -> bool:
    scenes = [re.sub(r"\s+", " ", str(m.get("scene_markup") or "")) for m in library.get("masters") or []]
    if len(scenes) < 3:
        return False
    return len(set(scenes)) == len(scenes)
