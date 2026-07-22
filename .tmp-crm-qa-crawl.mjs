/**
 * CRM QA crawl helpers — run via browser CDP evaluate (paste body).
 * This file documents the route list used for QA.
 */
export const CRM_STATIC_ROUTES = [
  '/workspaces/crm',
  '/workspaces/crm/dashboard',
  '/workspaces/crm/contacts',
  '/workspaces/crm/contacts/new',
  '/workspaces/crm/contacts/import',
  '/workspaces/crm/companies',
  '/workspaces/crm/companies/new',
  '/workspaces/crm/companies/import',
  '/workspaces/crm/relationships',
  '/workspaces/crm/relationships/new',
  '/workspaces/crm/relationships/network',
  '/workspaces/crm/relationships/intelligence',
  '/workspaces/crm/timeline',
  '/workspaces/crm/activities',
  '/workspaces/crm/tasks',
  '/workspaces/crm/calendar',
  '/workspaces/crm/notes',
  '/workspaces/crm/files',
  '/workspaces/crm/tags',
  '/workspaces/crm/communication',
  '/workspaces/crm/communication/calls',
  '/workspaces/crm/communication/meetings',
  '/workspaces/crm/communication/templates',
  '/workspaces/crm/communication/sequences',
  '/workspaces/crm/communication/signatures',
  '/workspaces/crm/communication/analytics',
  '/workspaces/crm/communication/preferences',
  '/workspaces/crm/documents',
  '/workspaces/crm/search',
  '/workspaces/crm/search/advanced',
  '/workspaces/crm/search/saved',
  '/workspaces/crm/reports',
  '/workspaces/crm/settings',
];

export const RELATED_ROUTES = [
  '/dashboard',
  '/dashboard/leads',
  '/dashboard/sales',
  '/workspaces/marketing/dashboard',
];

/** Patterns that indicate raw i18n keys or untranslated codes */
export const RAW_KEY_RE =
  /\b(crm\.[a-zA-Z0-9_.]+|activity\.[a-zA-Z0-9_.]+|common\.[a-zA-Z0-9_.]+|[a-z]+(?:[A-Z][a-z]+)+\.[a-zA-Z0-9_.]+)\b/;
