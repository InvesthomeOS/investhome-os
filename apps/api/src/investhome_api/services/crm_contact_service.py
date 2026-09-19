"""CRM contact query and serialization service — re-exports from crm.contact_service."""

from investhome_api.services.crm.contact_service import (  # noqa: F401
    contact_list_meta,
    count_active_contacts,
    count_contacts_with_email,
    count_contacts_with_phone,
    count_favorite_contacts,
    fetch_favorite_contacts,
    fetch_pinned_companies,
    fetch_recent_contacts,
    fetch_recently_updated_contacts,
    list_crm_contacts,
    serialize_contact,
)
