"""Factory for storage provider instances."""

from functools import lru_cache

from investhome_api.config.settings import get_settings
from investhome_api.models.document import StorageProvider
from investhome_api.services.storage.base import StorageProviderBase
from investhome_api.services.storage.local import LocalStorageProvider


@lru_cache
def get_storage_provider() -> StorageProviderBase:
    settings = get_settings()
    provider = settings.document_storage_provider.lower()
    if provider in ("local", ""):
        return LocalStorageProvider(settings.document_storage_root)
    # Cloud providers: stub local until Phase 2 cloud integration
    return LocalStorageProvider(settings.document_storage_root)


def provider_enum() -> StorageProvider:
    settings = get_settings()
    mapping = {
        "local": StorageProvider.LOCAL,
        "s3": StorageProvider.S3,
        "gcs": StorageProvider.GCS,
        "azure": StorageProvider.AZURE,
    }
    return mapping.get(settings.document_storage_provider.lower(), StorageProvider.LOCAL)
