"""Numeric art direction — %35, 675.000 USD, and 2+1 are campaign actors."""

from __future__ import annotations

from typing import Any

SCHEMA = "NumericArtDirectionV1"

NUMBERS = (
    {"token": "%35", "fact": "discount", "possible_functions": ("hero", "secondary_hero", "rhythmic_device", "proof_point", "supporting_information")},
    {"token": "675.000 USD", "fact": "price", "possible_functions": ("hero", "secondary_hero", "rhythmic_device", "proof_point", "supporting_information")},
    {"token": "2+1", "fact": "unit", "possible_functions": ("hero", "secondary_hero", "rhythmic_device", "proof_point", "supporting_information")},
)

FUNCTIONS = (
    "hero",
    "secondary_hero",
    "rhythmic_device",
    "proof_point",
    "supporting_information",
)


def numeric_art_direction_contract() -> dict[str, Any]:
    return {
        "schema": SCHEMA,
        "numbers": [dict(item) for item in NUMBERS],
        "functions": list(FUNCTIONS),
        "rule": (
            "Analyze whether each number should function as hero, secondary hero, rhythmic device, "
            "proof point, or supporting information depending on campaign strategy. "
            "Do not automatically make the headline the largest object."
        ),
        "forbidden_treatments": (
            "giant %35 badge",
            "giant price box",
            "sale sticker",
            "promo burst",
            "KPI tile",
            "dashboard numeral",
        ),
        "premium_rule": "Commercial does not mean cheap promotion. A numeral may be monumental and still be designed type.",
        "status": "READY",
    }


def assign_numeric_functions(*, hierarchy: str) -> dict[str, Any]:
    """Strategy-dependent defaults. Not a template. Proof 03 must still justify each assignment."""
    mapping = {
        "OFFER_LED": {"%35": "hero", "675.000 USD": "secondary_hero", "2+1": "proof_point"},
        "PRICE_LED": {"%35": "secondary_hero", "675.000 USD": "hero", "2+1": "proof_point"},
        "ARCHITECTURE_LED": {"%35": "rhythmic_device", "675.000 USD": "proof_point", "2+1": "supporting_information"},
        "HERITAGE_LED": {"%35": "proof_point", "675.000 USD": "proof_point", "2+1": "supporting_information"},
        "PROJECT_LED": {"%35": "secondary_hero", "675.000 USD": "proof_point", "2+1": "supporting_information"},
        "LIFESTYLE_LED": {"%35": "supporting_information", "675.000 USD": "proof_point", "2+1": "proof_point"},
        "LOCATION_LED": {"%35": "supporting_information", "675.000 USD": "proof_point", "2+1": "supporting_information"},
    }
    assigned = mapping.get(hierarchy) or mapping["ARCHITECTURE_LED"]
    return {
        "schema": "NumericFunctionAssignmentV1",
        "hierarchy": hierarchy,
        "assignment": assigned,
        "note": "Defaults are starting intelligence, not locks. Each number must still participate in the visual idea.",
        "rendered": False,
    }


def numeric_art_direction_markdown() -> str:
    contract = numeric_art_direction_contract()
    lines = [
        "# 06 Numeric art direction",
        "",
        contract["rule"],
        "",
        contract["premium_rule"],
        "",
        "## Numbers in the current Temple lansman",
        "",
    ]
    for item in contract["numbers"]:
        lines.append(f"- `{item['token']}` ({item['fact']}) — possible functions: {', '.join(item['possible_functions'])}")
    lines.extend(["", "## Forbidden treatments", ""])
    for item in contract["forbidden_treatments"]:
        lines.append(f"- {item}")
    lines.extend(
        [
            "",
            "Architecture-led default for The Temple: %35 as rhythmic device, price as proof point, 2+1 as support —",
            "unless a future concept honestly makes a number the hero of the idea.",
        ]
    )
    return "\n".join(lines) + "\n"
