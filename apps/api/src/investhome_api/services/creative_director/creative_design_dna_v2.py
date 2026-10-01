"""CreativeDesignDNAV2 — concrete design intelligence from Grade-A DESIGN_REFERENCES.

Principles, not template coordinates. Never copy another project's content.
"""

from __future__ import annotations

from typing import Any

from investhome_api.services.creative_director.ai_visual_art_director import GRADE_A_REFERENCES

SCHEMA = "CreativeDesignDNAV2"

FORBIDDEN_LITERAL_COPY = (
    "another project's architecture pixels",
    "another project's interior pixels",
    "another project's logo",
    "another project's financial facts",
    "exact headline wording",
    "exact badge/circle devices from a reference",
    "exact coordinate lockups",
    "UniLoft name or Uniloft campaign copy",
)

# Locked Grade-A ids from CreativeReferenceLibrary uuid5, plus live Media Library asset ids.
GRADE_A_MEDIA = {
    "ORNEK_00013.jpg": "a60a051f-5895-47df-958b-a738cbaf7d1f",
    "ORNEK_00001.jpg": "1d61bf43-5c14-446a-bf4d-96b29435876e",
    "ORNEK_00006.jpg": "be3741ba-bd2a-4d10-87bd-e91e80d12af7",
    "ORNEK_00015.jpg": "e4129917-b4b1-44bc-a389-69fbf9a4eab6",
    "ORNEK_00011.jpg": "8fe5f79f-bf1d-4d8d-ac0d-df4345e3f169",
    "ORNEK_00008.jpg": "2537b300-8955-4e1a-b892-624d7db19fb7",
}


def _base(
    *,
    filename: str,
    reference_id: str,
    media_asset_id: str,
    visual_idea: str,
    composition_logic: str,
    dominant_mass: str,
    secondary_mass: str,
    negative_space_logic: str,
    reading_path: str,
    typography_system: str,
    photography_role: str,
    graphic_devices: list[str],
    commercial_hierarchy: list[str],
    emotional_character: str,
    memorable_gesture: str,
    transferable_principles: list[str],
    suitable_campaign_types: list[str],
    strength_score: int,
    notes: str = "",
) -> dict[str, Any]:
    return {
        "schema": SCHEMA,
        "reference_id": reference_id,
        "media_asset_id": media_asset_id,
        "filename": filename,
        "grade": "A",
        "visual_idea": visual_idea,
        "composition_logic": composition_logic,
        "dominant_mass": dominant_mass,
        "secondary_mass": secondary_mass,
        "negative_space_logic": negative_space_logic,
        "reading_path": reading_path,
        "typography_system": typography_system,
        "photography_role": photography_role,
        "graphic_devices": graphic_devices,
        "commercial_hierarchy": commercial_hierarchy,
        "emotional_character": emotional_character,
        "memorable_gesture": memorable_gesture,
        "transferable_principles": transferable_principles,
        "forbidden_literal_copy": list(FORBIDDEN_LITERAL_COPY),
        "suitable_campaign_types": suitable_campaign_types,
        "strength_score": strength_score,
        "notes": notes,
        "source": "pixel_analysis_of_DESIGN_REFERENCES",
    }


def grade_a_design_dna() -> list[dict[str, Any]]:
    """One DNA record per locked Grade-A reference. Analyzed from actual pixels."""
    by_name = {name: rid for rid, name in GRADE_A_REFERENCES}
    return [
        _base(
            filename="ORNEK_00013.jpg",
            reference_id=by_name["ORNEK_00013.jpg"],
            media_asset_id=GRADE_A_MEDIA["ORNEK_00013.jpg"],
            visual_idea=(
                "A cropped fragment of classical architecture becomes graphic material: "
                "sunlit stone colonnade occupies the lower-left as a physical foundation, "
                "while a deep navy field becomes the entire message territory. "
                "The building is not a background; it is the lower structural mass of the page."
            ),
            composition_logic=(
                "Asymmetric two-mass page: bright carved stone vs void. "
                "Low-angle crop cuts the building into a curved silhouette that pushes into the navy. "
                "Type never sits on the photograph. Edge tension lives at the stone/navy collision."
            ),
            dominant_mass="lower-left neoclassical colonnade, tightly cropped, black-and-white against navy",
            secondary_mass="upper-right stacked declarative headline in the navy void",
            negative_space_logic="Navy field is designed emptiness, not leftover sky. It is the page.",
            reading_path="headline stack top→bottom → supporting paragraph → gold word as close → logo as quiet footer",
            typography_system=(
                "Monumental all-caps sans stack with period-stopped words. "
                "Two white lines then one gold line as the emotional land. "
                "Body is small, open leading, left of the void. "
                "No serif. Commercial facts are absent; persuasion is verbal not numeric."
            ),
            photography_role="graphic material / architectural anchor — fragment, not environment",
            graphic_devices=[
                "extreme architectural crop",
                "monochrome stone vs solid color field",
                "silhouette collision",
                "single translucent highlight on a closing phrase",
            ],
            commercial_hierarchy=[
                "WHAT: three civic virtues (order / safety / prestige)",
                "WHY: planned city + rental market as investment logic",
                "OFFER: Washington D.C. as stable location — no price",
                "NEXT: brand mark only, no web-button CTA",
            ],
            emotional_character="architectural authority; quiet civic prestige; editorial restraint",
            memorable_gesture="white curved colonnade cutting into a navy void under three period-stopped words",
            transferable_principles=[
                "A photograph may be a structural page mass, not a backdrop.",
                "Color field can be the campaign, with architecture as the other actor.",
                "Headline can be a vertical chant; gold is one word, not a theme.",
                "No price card is required when the idea is civic authority.",
            ],
            suitable_campaign_types=["flagship prestige", "city-authority launch", "brand-level investment thesis"],
            strength_score=9,
            notes="Strongest Grade-A graphic idea. Do not copy UniLoft copy or this specific colonnade.",
        ),
        _base(
            filename="ORNEK_00001.jpg",
            reference_id=by_name["ORNEK_00001.jpg"],
            media_asset_id=GRADE_A_MEDIA["ORNEK_00001.jpg"],
            visual_idea=(
                "Private morning ritual staged against a recognizable power landmark. "
                "Foreground coffee on a terrace, mid-ground railing, background Capitol — "
                "the photograph is a three-depth narrative, not a building catalog."
            ),
            composition_logic=(
                "Photo occupies almost the full canvas. A pale upper-left sky is reserved as type territory "
                "via a soft bleach, not a rectangle. Asymmetry: human/terrace weight on the right, "
                "open city on the left. The woman's gaze points at the landmark."
            ),
            dominant_mass="terrace + seated figure + city skyline occupying the lower two thirds",
            secondary_mass="left-aligned headline sitting in bleached sky",
            negative_space_logic="Real pale sky is the type field. Do not invent a box; keep photographic quiet.",
            reading_path="logo → location → three-line lifestyle headline → offer line → eye follows figure toward landmark",
            typography_system=(
                "Dark navy sans on light sky. Three-line all-caps with one heavier middle line as the hinge. "
                "Thin rule under headline. Offer is smaller, not a badge. Location is microcopy with a pin."
            ),
            photography_role="narrative scene + architectural anchor (landmark as proof of place)",
            graphic_devices=["soft top bleach/gradient", "thin rule", "location pin microcopy", "depth staging"],
            commercial_hierarchy=[
                "WHAT: sip coffee where the world is governed",
                "WHY: location prestige as lifestyle proof",
                "OFFER: early-access off-plan pricing as secondary line",
                "NEXT: brand at top, no button",
            ],
            emotional_character="urban aspiration; calm elite morning; location as privilege",
            memorable_gesture="intimate coffee in the foreground, Capitol in the same breath",
            transferable_principles=[
                "Lifestyle foreground can sell location better than a façade hero.",
                "Type should occupy real photographic quiet, not a manufactured header slab.",
                "Landmark proof must remain real photography, never generated skyline.",
                "One heavier line inside a three-line headline creates spoken rhythm.",
            ],
            suitable_campaign_types=["location-led launch", "lifestyle prestige", "early-access invitation"],
            strength_score=8,
            notes="Do not copy Uniloft terrace or Capitol-as-Uniloft. Temple may use analogous depth, not this scene.",
        ),
        _base(
            filename="ORNEK_00006.jpg",
            reference_id=by_name["ORNEK_00006.jpg"],
            media_asset_id=GRADE_A_MEDIA["ORNEK_00006.jpg"],
            visual_idea=(
                "A proposition field sits above an intimate interior that looks out to the city. "
                "Intellectual scarcity argument (top) is proven by a lived room (bottom). "
                "The chandelier against the window is the visual hinge between home and city."
            ),
            composition_logic=(
                "Horizontal split: solid taupe message field over a warm interior photograph. "
                "Interior itself is layered — brick wall left, window center, seated figure right. "
                "Risk: the split can collapse into 'header + photo' unless the interior has a clear looking-out mechanism."
            ),
            dominant_mass="lower interior with window, chandelier, sofa, brick",
            secondary_mass="upper centered type on taupe field",
            negative_space_logic="Taupe field is a designed plate, not a crop of the photo. Photo keeps its own ceiling darkness.",
            reading_path="centered headline → flourish → body → interior scene → brand on the photograph",
            typography_system=(
                "Centered sans. Light location line over bold scarcity line. "
                "Smaller body with italic project name. Decorative swirl divider. "
                "Type does not enter the room."
            ),
            photography_role="hero narrative interior; window as depth layer to the city",
            graphic_devices=["solid color proposition field", "ornamental divider", "logo over photo footer"],
            commercial_hierarchy=[
                "WHAT: new housing supply in D.C. is limited",
                "WHY: scarcity is investment strength",
                "OFFER: named project as one of those scarce assets",
                "NEXT: brand only",
            ],
            emotional_character="warm residential intimacy; quiet market confidence; dusk interior calm",
            memorable_gesture="branch chandelier silhouetted on a city window inside a lived room",
            transferable_principles=[
                "An interior is a chamber that can look toward the city's value, not a furniture catalog.",
                "A message field is allowed only if the photograph still has its own mechanism.",
                "Centered type is a choice here, not a default — reject it when the photo has a side gravity.",
                "Human scale in the room prevents the interior from becoming a show-unit still.",
            ],
            suitable_campaign_types=["interior-led residential", "scarcity argument", "looking-out chamber"],
            strength_score=7,
            notes="Near the banned 'dark header + photo' pattern. Transfer the chamber/window idea, never the split template.",
        ),
        _base(
            filename="ORNEK_00015.jpg",
            reference_id=by_name["ORNEK_00015.jpg"],
            media_asset_id=GRADE_A_MEDIA["ORNEK_00015.jpg"],
            visual_idea=(
                "A dusk interior emerges from a top-down dark veil. "
                "Foreground bar stools, stone island, and a warm still-life of fruit pull the eye into depth; "
                "the city exists as a blue-hour balcony beyond. Photography is a depth tunnel, type rides the veil."
            ),
            composition_logic=(
                "Full-bleed interior. Dark gradient occupies the upper third as a photographic shadow, not a separate card. "
                "Asymmetry: stools left, island mass right. Fruit basket is the warm visual center."
            ),
            dominant_mass="stone island and kitchen volume in the lower right",
            secondary_mass="three black stools as rhythmic foreground; type in the upper veil",
            negative_space_logic="Gradient darkness harvested from the scene's own ceiling, then extended for type.",
            reading_path="location → weight-contrasted headline → italic subline → body → fruit/island → brand on floor",
            typography_system=(
                "White sans in the veil. Headline uses internal weight contrast: bold clause, light clause. "
                "Italic invitation line. Body is two quiet lines. Project logotype sits on the island side-panel as in-scene type."
            ),
            photography_role="narrative scene + depth layer + architectural interior anchor",
            graphic_devices=["top-down photographic veil", "foreground interruption (stools)", "in-scene logotype on architecture"],
            commercial_hierarchy=[
                "WHAT: smart kitchen, simple design",
                "WHY: integrated systems and materials as lived experience",
                "OFFER: implied product world, no price",
                "NEXT: brand footer",
            ],
            emotional_character="warm residential intimacy against cool urban dusk; quiet material luxury",
            memorable_gesture="three black stools in front of a glowing fruit still-life, city dusk beyond",
            transferable_principles=[
                "A gradient is legitimate when it continues the photograph's own light, not when it is a UI overlay.",
                "Foreground objects create depth the type cannot.",
                "Headline weight contrast inside one line is more sophisticated than two fonts.",
                "A logotype may live on architecture if it feels inscribed, not stickered.",
            ],
            suitable_campaign_types=["interior product story", "material/craft launch", "dusk lifestyle"],
            strength_score=8,
        ),
        _base(
            filename="ORNEK_00011.jpg",
            reference_id=by_name["ORNEK_00011.jpg"],
            media_asset_id=GRADE_A_MEDIA["ORNEK_00011.jpg"],
            visual_idea=(
                "The project building is isolated as a hero object while the surrounding city is drained to a pale diagram. "
                "Thin pointer lines map walking time to civic landmarks. The mechanism is geographic proof, not decoration."
            ),
            composition_logic=(
                "Centered brick volume on a whitened ground. Informational type occupies the upper field. "
                "Pointers rise from the roofline. Risk: infographic can overpower the photograph if labels multiply."
            ),
            dominant_mass="full-color brick corner building in the lower center",
            secondary_mass="centered headline and walking-time callouts in the pale upper field",
            negative_space_logic="Desaturated city becomes paper. The building casts the only true photographic weight.",
            reading_path="brand → address → proximity headline → building → landmark pointers as evidence",
            typography_system=(
                "Centered copper sans headline. Small grey address. White type in a brown field for the proof sentence. "
                "Microcopy labels with walking icons. Not a luxury serif."
            ),
            photography_role="hero object; background city as graphic material",
            graphic_devices=["desaturated context", "pointer lines", "proof color field", "fade to paper"],
            commercial_hierarchy=[
                "WHAT: a few steps to the city's key points",
                "WHY: walking times to named civic anchors",
                "OFFER: location as the product",
                "NEXT: brand",
            ],
            emotional_character="urban aspiration; cartographic clarity; quiet civic confidence",
            memorable_gesture="walking-time lines radiating from a isolated brick building toward faded landmarks",
            transferable_principles=[
                "A building can be an object on a designed page, not a full-bleed wallpaper.",
                "Geographic proof should be sparse lines, not a map UI.",
                "Desaturating context is a graphic act; do not fake landmarks.",
                "Reject this DNA when it collapses into a listing card with pins.",
            ],
            suitable_campaign_types=["location/proximity", "urban convenience", "civic adjacency"],
            strength_score=7,
            notes="Transfer isolation + proof lines, never Uniloft brick or Capitol as someone else's asset.",
        ),
        _base(
            filename="ORNEK_00008.jpg",
            reference_id=by_name["ORNEK_00008.jpg"],
            media_asset_id=GRADE_A_MEDIA["ORNEK_00008.jpg"],
            visual_idea=(
                "Dusk façade photographed through foreground grasses, with a human on a ground patio. "
                "Type is placed into the darker right air of the building rather than onto a separate plate. "
                "The photograph remains the page structure."
            ),
            composition_logic=(
                "Low-angle vertical building mass left/center. Right side holds quieter façade and type. "
                "Foreground blur grasses create depth. Circular delivery badges sit on the photo — "
                "those circles are NOT transferable craft."
            ),
            dominant_mass="vertical dusk façade with lit windows",
            secondary_mass="serif gold headline in the right air; patio figure as human scale",
            negative_space_logic="Use the building's own unlit panels as type territory. Do not add a box.",
            reading_path="gold serif headline → white sans body → (ignore circles) → brand at the ground line",
            typography_system=(
                "Medium serif headline in metallic gold, right aligned. "
                "White sans body with one bolded project name. "
                "Serif/sans pairing is the craft; overlapping circles are a defect."
            ),
            photography_role="environment + architectural anchor + depth layer (grasses, patio, façade)",
            graphic_devices=["foreground bokeh grasses", "type in photographic dark", "human scale on patio"],
            commercial_hierarchy=[
                "WHAT: a living space that opens to the city",
                "WHY: terraces, loft detail, city energy brought inward",
                "OFFER: delivery timing — currently encoded as banned circle badges",
                "NEXT: brand footer",
            ],
            emotional_character="urban aspiration; dusk residential intimacy; architectural quiet",
            memorable_gesture="ornamental grasses in front of a glowing dusk façade with a person on the patio",
            transferable_principles=[
                "Type can live in the building's own shadow rather than on a header.",
                "Foreground vegetation is a depth device.",
                "Serif headline against dusk glass is a pairing, not a luxury default.",
                "Never transfer circular offer badges; art-direct delivery facts as type.",
            ],
            suitable_campaign_types=["façade dusk launch", "terrace living", "delivery-timed campaign"],
            strength_score=8,
            notes="Strip the circle badges from the DNA. Keep dusk + grasses + type-in-shadow.",
        ),
    ]


def design_dna_library() -> dict[str, Any]:
    records = grade_a_design_dna()
    return {
        "schema": "CreativeDesignDNALibraryV2",
        "grade_a_count": len(records),
        "records": records,
        "status": "READY" if len(records) == len(GRADE_A_REFERENCES) else "FAIL",
        "coordinates_are_not_the_intelligence": True,
    }
