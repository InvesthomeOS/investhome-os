"""Idempotent marketing demo — campaigns, sources, audiences, segments, content, attribution stubs."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from investhome_api.db.demo.markers import DEMO_METADATA, INTEGRATED_DEMO_SOURCE
from investhome_api.db.session import SessionLocal
from investhome_api.models.lead import Lead
from investhome_api.models.marketing import (
    MarketingAudience,
    MarketingAudienceMode,
    MarketingAudienceStatus,
    MarketingAudienceType,
    MarketingCampaign,
    MarketingCampaignObjective,
    MarketingCampaignPrimaryChannel,
    MarketingCampaignStatus,
    MarketingCampaignType,
    MarketingChannel,
    MarketingChannelCategory,
    MarketingChannelStatus,
    MarketingConnectionStatus,
    MarketingContentAsset,
    MarketingContentType,
    MarketingLeadContext,
    MarketingLeadHandoffStatus,
    MarketingLeadSource,
    MarketingLeadSourceType,
    MarketingSegment,
    MarketingSegmentType,
    SegmentCalculationStatus,
)
from investhome_api.models.marketing_attribution import (
    AttributionModelType,
    MarketingAttributionModel,
)
from investhome_api.models.marketing_lead_attribution import (
    MarketingAttributionSource,
    MarketingLeadAttribution,
)
from investhome_api.models.project import Project
from investhome_api.models.user_auth import User

LEAD_SOURCES = [
    ("DEMO-SRC-WEB", "Website Organic", MarketingLeadSourceType.ORGANIC),
    ("DEMO-SRC-META", "Meta Ads", MarketingLeadSourceType.PAID),
    ("DEMO-SRC-REF", "Partner Referral", MarketingLeadSourceType.REFERRAL),
    ("DEMO-SRC-EVT", "Cityscape Exhibition", MarketingLeadSourceType.EVENT),
]

CAMPAIGNS = [
    ("DEMO-CMP-TEMPLE", "Temple Launch Awareness", MarketingCampaignType.PROJECT_LAUNCH, "PRJ-TEMP-001"),
    ("DEMO-CMP-UNI", "UniLoft Leasing Push", MarketingCampaignType.BUYER_ACQUISITION, "PRJ-UNIL-002"),
    ("DEMO-CMP-NOMA", "NoMa Investor Acquisition", MarketingCampaignType.INVESTOR_ACQUISITION, "PRJ-NOMA-006"),
    ("DEMO-CMP-NURTURE", "DC Buyer Nurture", MarketingCampaignType.NURTURE, None),
    ("DEMO-CMP-RETARGET", "Site Visitor Retargeting", MarketingCampaignType.RETARGETING, None),
]


def seed_marketing(session: Session | None = None) -> dict[str, int]:
    own_session = session is None
    session = session or SessionLocal()
    counts = {
        "channels": 0,
        "lead_sources": 0,
        "campaigns": 0,
        "audiences": 0,
        "segments": 0,
        "content": 0,
        "lead_contexts": 0,
        "attributions": 0,
        "touchpoints": 0,
        "journeys": 0,
        "attrib_models": 0,
    }
    try:
        owner = session.scalar(select(User).where(User.email == "marketing@investhome.demo"))
        owner_id = owner.id if owner else None
        projects = {p.project_code: p for p in session.scalars(select(Project)).all()}

        # Channel
        channel = session.scalar(
            select(MarketingChannel).where(MarketingChannel.name == "Demo Paid Social")
        )
        if channel is None:
            channel = MarketingChannel(
                name="Demo Paid Social",
                category=MarketingChannelCategory.PAID_SOCIAL,
                provider="meta",
                status=MarketingChannelStatus.ACTIVE,
                connection_status=MarketingConnectionStatus.NOT_CONNECTED,
                metadata_json=dict(DEMO_METADATA),
                is_demo=True,
            )
            session.add(channel)
            session.flush()
            counts["channels"] += 1

        source_by_code: dict[str, MarketingLeadSource] = {}
        for tracking, name, source_type in LEAD_SOURCES:
            existing = session.scalar(
                select(MarketingLeadSource).where(MarketingLeadSource.tracking_code == tracking)
            )
            if existing is not None:
                source_by_code[tracking] = existing
                continue
            src = MarketingLeadSource(
                name=name,
                normalized_name=name.lower().replace(" ", "_"),
                source_type=source_type,
                channel_id=channel.id,
                tracking_code=tracking,
                description=f"Demo lead source — {INTEGRATED_DEMO_SOURCE}",
                is_active=True,
                metadata_json=dict(DEMO_METADATA),
                is_demo=True,
                created_by_user_id=owner_id,
            )
            session.add(src)
            session.flush()
            source_by_code[tracking] = src
            counts["lead_sources"] += 1

        campaign_by_code: dict[str, MarketingCampaign] = {}
        now = datetime.now(UTC)
        for code, name, ctype, project_code in CAMPAIGNS:
            existing = session.scalar(
                select(MarketingCampaign).where(MarketingCampaign.code == code)
            )
            if existing is not None:
                campaign_by_code[code] = existing
                continue
            project = projects.get(project_code) if project_code else None
            lead_source = source_by_code.get("DEMO-SRC-META")
            camp = MarketingCampaign(
                name=name,
                code=code,
                description=f"Demo campaign — {INTEGRATED_DEMO_SOURCE}",
                objective=MarketingCampaignObjective.LEAD_GENERATION,
                campaign_type=ctype,
                status=MarketingCampaignStatus.ACTIVE,
                owner_user_id=owner_id,
                target_project_id=project.id if project else None,
                lead_source_id=lead_source.id if lead_source else None,
                primary_channel=MarketingCampaignPrimaryChannel.META,
                start_date=now - timedelta(days=30),
                end_date=now + timedelta(days=60),
                budget_amount=Decimal("25000.00"),
                budget_currency="USD",
                tags=["demo", "integrated"],
                metadata_json=dict(DEMO_METADATA),
                is_demo=True,
                created_by_user_id=owner_id,
            )
            session.add(camp)
            session.flush()
            campaign_by_code[code] = camp
            counts["campaigns"] += 1

        # Audience + segment
        audience = session.scalar(
            select(MarketingAudience).where(MarketingAudience.name == "Demo DC Prospects")
        )
        if audience is None:
            audience = MarketingAudience(
                name="Demo DC Prospects",
                description=f"Demo audience — {INTEGRATED_DEMO_SOURCE}",
                audience_type=MarketingAudienceType.STATIC,
                mode=MarketingAudienceMode.STATIC,
                status=MarketingAudienceStatus.ACTIVE,
                source=INTEGRATED_DEMO_SOURCE,
                estimated_size=120,
                metadata_json=dict(DEMO_METADATA),
                is_demo=True,
                created_by_user_id=owner_id,
            )
            session.add(audience)
            counts["audiences"] += 1

        segment = session.scalar(
            select(MarketingSegment).where(MarketingSegment.name == "Demo High Intent Buyers")
        )
        if segment is None:
            segment = MarketingSegment(
                name="Demo High Intent Buyers",
                description=f"Demo segment — {INTEGRATED_DEMO_SOURCE}",
                segment_type=MarketingSegmentType.DYNAMIC,
                rules_json={"demo_seed": True, "source": INTEGRATED_DEMO_SOURCE},
                calculation_status=SegmentCalculationStatus.NOT_CALCULATED,
                estimated_size=45,
                metadata_json=dict(DEMO_METADATA),
                is_demo=True,
                created_by_user_id=owner_id,
            )
            session.add(segment)
            counts["segments"] += 1

        # Content items
        for idx, (code, camp) in enumerate(list(campaign_by_code.items())[:4], start=1):
            content_name = f"Demo Brochure — {camp.name}"
            existing = session.scalar(
                select(MarketingContentAsset).where(MarketingContentAsset.name == content_name)
            )
            if existing is not None:
                continue
            session.add(
                MarketingContentAsset(
                    name=content_name,
                    content_type=MarketingContentType.DOCUMENT,
                    format="pdf",
                    campaign_id=camp.id,
                    status="published",
                    metadata_json=dict(DEMO_METADATA),
                    is_demo=True,
                    created_by_user_id=owner_id,
                )
            )
            counts["content"] += 1

        # Attribution model stub
        attrib_model = session.scalar(
            select(MarketingAttributionModel).where(
                MarketingAttributionModel.name == "Demo Last Touch"
            )
        )
        if attrib_model is None:
            attrib_model = MarketingAttributionModel(
                name="Demo Last Touch",
                model_type=AttributionModelType.LAST_TOUCH.value,
                config_json=dict(DEMO_METADATA),
                is_default=False,
                is_active=True,
                description=f"Demo attribution model — {INTEGRATED_DEMO_SOURCE}",
                created_by_user_id=owner_id,
            )
            session.add(attrib_model)
            session.flush()
            counts["attrib_models"] += 1

        # Link demo leads to campaigns/sources
        demo_leads = list(session.scalars(select(Lead).where(Lead.is_demo.is_(True)).limit(15)).all())
        campaign_list = list(campaign_by_code.values())
        source_list = list(source_by_code.values())
        for i, lead in enumerate(demo_leads):
            camp = campaign_list[i % len(campaign_list)] if campaign_list else None
            src = source_list[i % len(source_list)] if source_list else None

            ctx = session.scalar(
                select(MarketingLeadContext).where(MarketingLeadContext.lead_id == lead.id)
            )
            if ctx is None:
                session.add(
                    MarketingLeadContext(
                        lead_id=lead.id,
                        campaign_id=camp.id if camp else None,
                        source_id=src.id if src else None,
                        channel_id=channel.id,
                        marketing_status="engaged",
                        handoff_status=MarketingLeadHandoffStatus.READY,
                        attribution_json=dict(DEMO_METADATA),
                        metadata_json=dict(DEMO_METADATA),
                        is_demo=True,
                    )
                )
                counts["lead_contexts"] += 1

            attr = session.scalar(
                select(MarketingLeadAttribution).where(MarketingLeadAttribution.lead_id == lead.id)
            )
            if attr is None and camp is not None:
                session.add(
                    MarketingLeadAttribution(
                        lead_id=lead.id,
                        campaign_id=camp.id,
                        attribution_source=MarketingAttributionSource.MANUAL,
                        utm_source="demo",
                        utm_medium="integrated_seed",
                        utm_campaign=camp.code,
                        first_touch_at=now - timedelta(days=10),
                        attribution_reason=f"Seeded by {INTEGRATED_DEMO_SOURCE}",
                        created_by_user_id=owner_id,
                    )
                )
                counts["attributions"] += 1

        if own_session:
            session.commit()
        else:
            session.flush()
        return counts
    finally:
        if own_session:
            session.close()
