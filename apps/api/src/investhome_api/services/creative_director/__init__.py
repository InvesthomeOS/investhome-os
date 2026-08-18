"""Creative Director & AI Orchestration foundation.

GPT interprets a natural-language brief, researches Drive/RAG, locks real project
assets, and returns a structured Creative Brief + durable Campaign Context.

This package does NOT generate images.
"""

from investhome_api.services.creative_director.service import (
    create_campaign,
    get_campaign,
    revise_campaign_stub,
)

__all__ = [
    "create_campaign",
    "get_campaign",
    "revise_campaign_stub",
]
