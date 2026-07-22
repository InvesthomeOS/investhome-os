"""Knowledge Hub configuration — controlled category taxonomy."""

from __future__ import annotations

SEED_CATEGORIES: list[dict[str, str]] = [
    {"code": "contracts", "name_en": "Contracts", "name_tr": "Sözleşmeler", "description": "Legal agreements and contracts"},
    {"code": "legal", "name_en": "Legal", "name_tr": "Hukuki", "description": "Legal opinions, filings, compliance"},
    {"code": "financial", "name_en": "Financial", "name_tr": "Finansal", "description": "Statements, invoices, reports"},
    {"code": "investor", "name_en": "Investor", "name_tr": "Yatırımcı", "description": "Investor communications and offerings"},
    {"code": "project", "name_en": "Project", "name_tr": "Proje", "description": "Project plans and deliverables"},
    {"code": "marketing", "name_en": "Marketing", "name_tr": "Pazarlama", "description": "Campaign and brand materials"},
    {"code": "construction", "name_en": "Construction", "name_tr": "İnşaat", "description": "Drawings, permits, inspections"},
    {"code": "permits", "name_en": "Permits", "name_tr": "İzinler", "description": "Regulatory permits and licenses"},
    {"code": "insurance", "name_en": "Insurance", "name_tr": "Sigorta", "description": "Policies and claims"},
    {"code": "tax", "name_en": "Tax", "name_tr": "Vergi", "description": "Tax filings and certificates"},
    {"code": "correspondence", "name_en": "Correspondence", "name_tr": "Yazışmalar", "description": "Letters and emails"},
    {"code": "photos", "name_en": "Photos", "name_tr": "Fotoğraflar", "description": "Site and property photos"},
    {"code": "presentations", "name_en": "Presentations", "name_tr": "Sunumlar", "description": "Decks and briefings"},
    {"code": "other", "name_en": "Other", "name_tr": "Diğer", "description": "Uncategorized knowledge assets"},
]
