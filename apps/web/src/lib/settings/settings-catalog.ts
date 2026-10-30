export type SettingsUser = {
  permissions: readonly string[];
} | null;

function hasPermission(user: SettingsUser, resource: string, action: string): boolean {
  if (!user) return false;
  if (user.permissions.includes('*:*')) return true;
  return user.permissions.includes(`${resource}:${action}`);
}

export type SettingsGroupId =
  | 'personal'
  | 'platform'
  | 'crm'
  | 'integrations'
  | 'access'
  | 'security';

type PermissionPair = readonly [resource: string, action: string];

export type SettingsEntry = {
  id: string;
  group: SettingsGroupId;
  href: string;
  /** Dashboard settings tab. Null means a separate existing route. */
  tab: string | null;
  /** Admin shell label key when this entry is shown there. */
  adminNavKey?: string;
  anyOf: readonly PermissionPair[];
  /** Signed-in user only. Not an admin setting. */
  personal?: boolean;
};

const PLATFORM_TABS: Array<Omit<SettingsEntry, 'group' | 'href'> & { tab: string }> = [
  { id: 'company', tab: 'company', anyOf: [['company', 'view'], ['settings', 'view']] },
  { id: 'offices', tab: 'offices', anyOf: [['offices', 'view'], ['settings', 'view']] },
  { id: 'brand', tab: 'brand', anyOf: [['brand', 'view'], ['brand', 'manage'], ['settings', 'view']] },
  {
    id: 'brandAssets',
    tab: 'brandAssets',
    anyOf: [['brand', 'view'], ['brand', 'manage'], ['settings', 'view']],
  },
  {
    id: 'organization',
    tab: 'organization',
    anyOf: [['organization', 'view'], ['settings', 'view']],
  },
  { id: 'localization', tab: 'localization', anyOf: [['settings', 'view']] },
  { id: 'currency', tab: 'currency', anyOf: [['settings', 'view']] },
  { id: 'documents', tab: 'documents', anyOf: [['settings', 'view']] },
  { id: 'notifications', tab: 'notifications', anyOf: [['settings', 'view']] },
  { id: 'ai', tab: 'ai', anyOf: [['settings', 'view']] },
  { id: 'storage', tab: 'storage', anyOf: [['settings', 'view']] },
];

function platformEntry(tab: (typeof PLATFORM_TABS)[number]): SettingsEntry {
  return {
    ...tab,
    group: 'platform',
    href: `/dashboard/settings?tab=${tab.tab}`,
  };
}

export const SETTINGS_CATALOG: readonly SettingsEntry[] = [
  {
    id: 'profile',
    group: 'personal',
    href: '/dashboard/profile',
    tab: null,
    anyOf: [],
    personal: true,
  },
  ...PLATFORM_TABS.map(platformEntry),
  {
    id: 'integrations',
    group: 'integrations',
    href: '/dashboard/settings?tab=integrations',
    tab: 'integrations',
    anyOf: [['settings', 'view']],
  },
  {
    id: 'communicationAccounts',
    group: 'integrations',
    href: '/workspaces/crm/settings/communication-accounts',
    tab: null,
    anyOf: [['crm', 'read']],
  },
  {
    id: 'crmSettings',
    group: 'crm',
    href: '/workspaces/crm/settings',
    tab: null,
    anyOf: [['crm', 'read']],
  },
  {
    id: 'users',
    group: 'access',
    href: '/dashboard/admin/users',
    tab: null,
    adminNavKey: 'users',
    anyOf: [['users', 'view'], ['users', 'manage']],
  },
  {
    id: 'teams',
    group: 'access',
    href: '/dashboard/admin/teams',
    tab: null,
    adminNavKey: 'teams',
    anyOf: [['organization', 'view'], ['company', 'view']],
  },
  {
    id: 'roles',
    group: 'access',
    href: '/dashboard/admin/roles',
    tab: null,
    adminNavKey: 'roles',
    anyOf: [['roles', 'view'], ['roles', 'manage']],
  },
  {
    id: 'permissions',
    group: 'access',
    href: '/dashboard/admin/permissions',
    tab: null,
    adminNavKey: 'permissions',
    anyOf: [['roles', 'view'], ['roles', 'manage']],
  },
  {
    id: 'security',
    group: 'security',
    href: '/dashboard/admin/security',
    tab: null,
    adminNavKey: 'security',
    anyOf: [['security', 'view']],
  },
  {
    id: 'authentication',
    group: 'security',
    href: '/dashboard/admin/authentication',
    tab: null,
    adminNavKey: 'authentication',
    anyOf: [['security', 'view']],
  },
  {
    id: 'sessions',
    group: 'security',
    href: '/dashboard/admin/sessions',
    tab: null,
    adminNavKey: 'sessions',
    anyOf: [['security', 'view']],
  },
  {
    id: 'apiKeys',
    group: 'security',
    href: '/dashboard/admin/api-keys',
    tab: null,
    adminNavKey: 'apiKeys',
    anyOf: [['security', 'view']],
  },
  {
    id: 'secrets',
    group: 'security',
    href: '/dashboard/admin/secrets',
    tab: null,
    adminNavKey: 'secrets',
    anyOf: [['security', 'view']],
  },
  {
    id: 'audit',
    group: 'security',
    href: '/dashboard/admin/audit',
    tab: null,
    adminNavKey: 'audit',
    anyOf: [['activity', 'view'], ['security', 'view']],
  },
  {
    id: 'compliance',
    group: 'security',
    href: '/dashboard/admin/compliance',
    tab: null,
    adminNavKey: 'compliance',
    anyOf: [['security', 'view'], ['compliance', 'view']],
  },
  {
    id: 'incidents',
    group: 'security',
    href: '/dashboard/admin/incidents',
    tab: null,
    adminNavKey: 'incidents',
    anyOf: [['security', 'view']],
  },
];

function allows(user: SettingsUser, entry: SettingsEntry): boolean {
  if (!user) return false;
  if (entry.personal) return true;
  return entry.anyOf.some(([resource, action]) => hasPermission(user, resource, action));
}

export function visibleSettingsEntries(user: SettingsUser): SettingsEntry[] {
  if (!user) return [];
  return SETTINGS_CATALOG.filter((entry) => allows(user, entry));
}

export function isSettingsTabAllowed(user: SettingsUser, tab: string): boolean {
  return visibleSettingsEntries(user).some((entry) => entry.tab === tab);
}

export function settingsEntriesByGroup(user: SettingsUser, group: SettingsGroupId): SettingsEntry[] {
  return visibleSettingsEntries(user).filter((entry) => entry.group === group);
}

export function duplicateSettingHrefs(entries: readonly SettingsEntry[]): string[] {
  const seen = new Set<string>();
  const duplicates = new Set<string>();
  for (const entry of entries) {
    if (seen.has(entry.href)) duplicates.add(entry.href);
    seen.add(entry.href);
  }
  return [...duplicates];
}
