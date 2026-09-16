"""Reciprocal relationship type mapping — single record, derived reciprocal labels."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from investhome_api.models.crm_relationship import (
    CrmRelationshipCategory,
    CrmRelationshipTypeConfig,
)

DEFAULT_TYPE_CONFIGS: list[dict] = [
    {
        "relationship_type": "parent",
        "reciprocal_type": "subsidiary",
        "category": CrmRelationshipCategory.ORGANIZATIONAL,
        "is_directional": True,
        "label": "Parent",
        "reciprocal_label": "Subsidiary",
        "prevents_hierarchy_cycle": True,
    },
    {
        "relationship_type": "subsidiary",
        "reciprocal_type": "parent",
        "category": CrmRelationshipCategory.ORGANIZATIONAL,
        "is_directional": True,
        "label": "Subsidiary",
        "reciprocal_label": "Parent",
        "prevents_hierarchy_cycle": True,
    },
    {
        "relationship_type": "referred_by",
        "reciprocal_type": "referred_to",
        "category": CrmRelationshipCategory.REFERRAL,
        "is_directional": True,
        "label": "Referred By",
        "reciprocal_label": "Referred To",
        "prevents_hierarchy_cycle": False,
    },
    {
        "relationship_type": "referred_to",
        "reciprocal_type": "referred_by",
        "category": CrmRelationshipCategory.REFERRAL,
        "is_directional": True,
        "label": "Referred To",
        "reciprocal_label": "Referred By",
        "prevents_hierarchy_cycle": False,
    },
    {
        "relationship_type": "partner",
        "reciprocal_type": "partner",
        "category": CrmRelationshipCategory.COMMERCIAL,
        "is_directional": False,
        "label": "Partner",
        "reciprocal_label": "Partner",
        "prevents_hierarchy_cycle": False,
    },
    {
        "relationship_type": "client",
        "reciprocal_type": "vendor",
        "category": CrmRelationshipCategory.COMMERCIAL,
        "is_directional": True,
        "label": "Client",
        "reciprocal_label": "Vendor",
        "prevents_hierarchy_cycle": False,
    },
    {
        "relationship_type": "vendor",
        "reciprocal_type": "client",
        "category": CrmRelationshipCategory.COMMERCIAL,
        "is_directional": True,
        "label": "Vendor",
        "reciprocal_label": "Client",
        "prevents_hierarchy_cycle": False,
    },
    {
        "relationship_type": "investor",
        "reciprocal_type": "investee",
        "category": CrmRelationshipCategory.INVESTMENT,
        "is_directional": True,
        "label": "Investor",
        "reciprocal_label": "Investee",
        "prevents_hierarchy_cycle": False,
    },
    {
        "relationship_type": "investee",
        "reciprocal_type": "investor",
        "category": CrmRelationshipCategory.INVESTMENT,
        "is_directional": True,
        "label": "Investee",
        "reciprocal_label": "Investor",
        "prevents_hierarchy_cycle": False,
    },
    {
        "relationship_type": "affiliate",
        "reciprocal_type": "affiliate",
        "category": CrmRelationshipCategory.ORGANIZATIONAL,
        "is_directional": False,
        "label": "Affiliate",
        "reciprocal_label": "Affiliate",
        "prevents_hierarchy_cycle": False,
    },
    {
        "relationship_type": "competitor",
        "reciprocal_type": "competitor",
        "category": CrmRelationshipCategory.COMMERCIAL,
        "is_directional": False,
        "label": "Competitor",
        "reciprocal_label": "Competitor",
        "prevents_hierarchy_cycle": False,
    },
    {
        "relationship_type": "colleague",
        "reciprocal_type": "colleague",
        "category": CrmRelationshipCategory.PERSONAL,
        "is_directional": False,
        "label": "Colleague",
        "reciprocal_label": "Colleague",
        "prevents_hierarchy_cycle": False,
    },
    {
        "relationship_type": "advisor",
        "reciprocal_type": "advisee",
        "category": CrmRelationshipCategory.OPERATIONAL,
        "is_directional": True,
        "label": "Advisor",
        "reciprocal_label": "Advisee",
        "prevents_hierarchy_cycle": False,
    },
    {
        "relationship_type": "advisee",
        "reciprocal_type": "advisor",
        "category": CrmRelationshipCategory.OPERATIONAL,
        "is_directional": True,
        "label": "Advisee",
        "reciprocal_label": "Advisor",
        "prevents_hierarchy_cycle": False,
    },
    {
        "relationship_type": "employs",
        "reciprocal_type": "employed_by",
        "category": CrmRelationshipCategory.ORGANIZATIONAL,
        "is_directional": True,
        "label": "Employs",
        "reciprocal_label": "Employed By",
        "prevents_hierarchy_cycle": False,
    },
    {
        "relationship_type": "employed_by",
        "reciprocal_type": "employs",
        "category": CrmRelationshipCategory.ORGANIZATIONAL,
        "is_directional": True,
        "label": "Employed By",
        "reciprocal_label": "Employs",
        "prevents_hierarchy_cycle": False,
    },
    {
        "relationship_type": "other",
        "reciprocal_type": "other",
        "category": CrmRelationshipCategory.OTHER,
        "is_directional": False,
        "label": "Other",
        "reciprocal_label": "Other",
        "prevents_hierarchy_cycle": False,
    },
    {
        "relationship_type": "contact_company",
        "reciprocal_type": "company_contact",
        "category": CrmRelationshipCategory.ORGANIZATIONAL,
        "is_directional": True,
        "label": "Company Contact",
        "reciprocal_label": "Has Contact",
        "prevents_hierarchy_cycle": False,
    },
    {
        "relationship_type": "company_contact",
        "reciprocal_type": "contact_company",
        "category": CrmRelationshipCategory.ORGANIZATIONAL,
        "is_directional": True,
        "label": "Has Contact",
        "reciprocal_label": "Company Contact",
        "prevents_hierarchy_cycle": False,
    },
]


def seed_type_configs(db: Session) -> None:
    existing = {row.relationship_type for row in db.scalars(select(CrmRelationshipTypeConfig)).all()}
    for config in DEFAULT_TYPE_CONFIGS:
        if config["relationship_type"] in existing:
            continue
        db.add(CrmRelationshipTypeConfig(**config))
    db.flush()


def get_type_config(db: Session, relationship_type: str) -> CrmRelationshipTypeConfig | None:
    return db.scalar(
        select(CrmRelationshipTypeConfig).where(
            CrmRelationshipTypeConfig.relationship_type == relationship_type,
            CrmRelationshipTypeConfig.is_active.is_(True),
        )
    )


def resolve_reciprocal_type(db: Session, relationship_type: str) -> tuple[str | None, str | None]:
    config = get_type_config(db, relationship_type)
    if not config:
        return None, None
    return config.reciprocal_type, config.reciprocal_label


def resolve_category(db: Session, relationship_type: str) -> CrmRelationshipCategory:
    config = get_type_config(db, relationship_type)
    if config:
        return config.category
    return CrmRelationshipCategory.OTHER


def prevents_hierarchy_cycle(db: Session, relationship_type: str) -> bool:
    config = get_type_config(db, relationship_type)
    return bool(config and config.prevents_hierarchy_cycle)


def get_reciprocal_display_label(db: Session, relationship_type: str) -> str | None:
    _, label = resolve_reciprocal_type(db, relationship_type)
    return label
