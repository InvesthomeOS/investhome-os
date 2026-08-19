"""Creative Director & AI Orchestration foundation.

GPT interprets a natural-language brief, researches Drive/RAG, locks real project
assets, and returns a structured Creative Brief + durable Campaign Context.

Image generation is a separate step: generate_ad_from_campaign reuses GPT Image
PROJECT MODE against the stored Campaign Context (does not rewrite CD brief logic).
"""

from investhome_api.services.creative_director.generate_ad import generate_ad_from_campaign
from investhome_api.services.creative_director.service import (
    create_campaign,
    get_campaign,
    revise_campaign_stub,
)

__all__ = [
    "create_campaign",
    "get_campaign",
    "revise_campaign_stub",
    "generate_ad_from_campaign",
]
