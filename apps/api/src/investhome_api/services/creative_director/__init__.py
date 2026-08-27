"""Creative Director & AI Orchestration foundation.

GPT interprets a natural-language brief, researches Drive/RAG, locks real project
assets, and returns a structured Creative Brief + durable Campaign Context.

Image generation is a separate step: generate_ad_from_campaign reuses GPT Image
PROJECT MODE against the stored Campaign Context (does not rewrite CD brief logic).
AI revision starts from master_creative.current_cover_asset_id (visual source
of truth). master_asset_id remains the immutable v1 original unless the user
explicitly reverts. Edit Map is OS data coupled to one cover raster.
"""

from investhome_api.services.creative_director.generate_ad import generate_ad_from_campaign
from investhome_api.services.creative_director.revision import (
    redo_campaign_revision,
    revise_ad_from_campaign,
    undo_campaign_revision,
)
from investhome_api.services.creative_director.service import (
    create_campaign,
    get_campaign,
)

__all__ = [
    "create_campaign",
    "get_campaign",
    "revise_ad_from_campaign",
    "undo_campaign_revision",
    "redo_campaign_revision",
    "generate_ad_from_campaign",
]
