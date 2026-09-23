'use client';

import Link from 'next/link';
import type { Route } from 'next';
import { useTranslations } from 'next-intl';

import { CRM_COMM_FOLDERS, type CrmCommFolderKey } from '@/workspaces/crm/types';
import { useCommunicationUiStore } from '@/workspaces/crm/stores/communication-ui-store';

const SUB_ROUTES = [
  { href: '/workspaces/crm/communication/unmatched', labelKey: 'unmatchedCommunications' },
  { href: '/workspaces/crm/communication/templates', labelKey: 'templates' },
  { href: '/workspaces/crm/communication/sequences', labelKey: 'sequences' },
  { href: '/workspaces/crm/communication/signatures', labelKey: 'signatures' },
  { href: '/workspaces/crm/communication/analytics', labelKey: 'analytics' },
  { href: '/workspaces/crm/communication/preferences', labelKey: 'preferences' },
] as const;

type CommunicationSidebarProps = {
  collapsed?: boolean;
};

export function CommunicationSidebar({ collapsed }: CommunicationSidebarProps) {
  const t = useTranslations('crm.communication');
  const tNav = useTranslations('crm.nav');
  const selectedFolder = useCommunicationUiStore((s) => s.selectedFolder);
  const setSelectedFolder = useCommunicationUiStore((s) => s.setSelectedFolder);

  if (collapsed) return null;

  return (
    <aside className="crm-communication__sidebar" aria-label={t('foldersAriaLabel')}>
      <div className="crm-communication__sidebar-section">
        <div className="crm-communication__sidebar-heading">{t('foldersHeading')}</div>
        <nav className="crm-communication__folder-list">
          {CRM_COMM_FOLDERS.map((folder) => (
            <button
              key={folder.key}
              type="button"
              className={
                selectedFolder === folder.key
                  ? 'crm-communication__folder-link crm-communication__folder-link--active'
                  : 'crm-communication__folder-link'
              }
              onClick={() => setSelectedFolder(folder.key as CrmCommFolderKey)}
            >
              {t(folder.labelKey)}
            </button>
          ))}
        </nav>
      </div>
      <div className="crm-communication__sidebar-section">
        <div className="crm-communication__sidebar-heading">{t('toolsHeading')}</div>
        <nav className="crm-communication__folder-list">
          {SUB_ROUTES.map((route) => (
            <Link key={route.href} href={route.href as Route} className="crm-communication__folder-link">
              {tNav(route.labelKey)}
            </Link>
          ))}
        </nav>
      </div>
    </aside>
  );
}
