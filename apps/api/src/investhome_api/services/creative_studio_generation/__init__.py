"""Creative Studio shared AI generation — Phase 1 foundation.

One production generation layer reused by all builders. Retrieval uses the
existing hybrid search / ai_documents / chunks / embeddings stack — no second RAG.
"""

from investhome_api.services.creative_studio_generation.service import generate_creative_content

__all__ = ["generate_creative_content"]
