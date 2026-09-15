"""Explicit Bitrix Aşama → Investhome Sales Opportunity stage mapping.

Never fuzzy-maps. Unknown values stay historical and unmapped.
"""

from __future__ import annotations

from investhome_api.models.sales import OpportunityStage

# Exact Bitrix Aşama strings from Aktif Müşteriler.xls / Junklar.xls.
BITRIX_STAGE_POTANSIYEL = "Potansiyel"
BITRIX_STAGE_TEKLIF = "Ön Bilgi / Teklif Aşaması"
BITRIX_STAGE_LONG_TERM = "Uzun Dönem Yatırımcı"
BITRIX_STAGE_AGENCY = "Acenta Müşterileri"
BITRIX_STAGE_PARTNERSHIP = "Proje Ortaklığı"
BITRIX_STAGE_JUNK = "Junk Lead"

# Conservative equivalents only. "Teklif Aşaması" is literally a proposal stage;
# "Potansiyel" is the early open Bitrix working stage and maps to Sales `new`.
SAFE_BITRIX_STAGE_TO_SALES: dict[str, OpportunityStage] = {
    BITRIX_STAGE_POTANSIYEL: OpportunityStage.NEW,
    BITRIX_STAGE_TEKLIF: OpportunityStage.PROPOSAL_PREPARATION,
}

# Customer segments / relationship labels, not Investhome pipeline stages.
UNMAPPED_REVIEW_STAGES: frozenset[str] = frozenset(
    {
        BITRIX_STAGE_LONG_TERM,
        BITRIX_STAGE_AGENCY,
        BITRIX_STAGE_PARTNERSHIP,
    }
)

PIPELINE_EXCLUDED_STAGES: frozenset[str] = frozenset({BITRIX_STAGE_JUNK})

STAGE_MAPPING_NOTES: dict[str, str] = {
    BITRIX_STAGE_POTANSIYEL: "Exact early-funnel Bitrix stage → Sales new.",
    BITRIX_STAGE_TEKLIF: "Exact 'Teklif Aşaması' → Sales proposal_preparation (not assumed sent).",
    BITRIX_STAGE_LONG_TERM: "Relationship segment, not a Sales pipeline stage. Historical only.",
    BITRIX_STAGE_AGENCY: "Customer origin segment, not a Sales pipeline stage. Historical only.",
    BITRIX_STAGE_PARTNERSHIP: "Partnership label, not a Sales pipeline stage. Historical only.",
    BITRIX_STAGE_JUNK: "Junk list. Excluded from Pipeline.",
}


def normalize_bitrix_stage(value: str | None) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def map_bitrix_stage(value: str | None) -> OpportunityStage | None:
    stage = normalize_bitrix_stage(value)
    if not stage:
        return None
    return SAFE_BITRIX_STAGE_TO_SALES.get(stage)


def is_pipeline_excluded_stage(value: str | None) -> bool:
    stage = normalize_bitrix_stage(value)
    return bool(stage and stage in PIPELINE_EXCLUDED_STAGES)


def is_unmapped_review_stage(value: str | None) -> bool:
    stage = normalize_bitrix_stage(value)
    return bool(stage and stage in UNMAPPED_REVIEW_STAGES)
