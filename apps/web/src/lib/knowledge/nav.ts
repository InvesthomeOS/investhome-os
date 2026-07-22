import type { Route } from 'next';
import type { IhIconName } from '@/components/icons/ih-icons';

export type KnowledgeNavItem = {
  href: Route;
  labelKey: string;
  icon: IhIconName;
};

export const KNOWLEDGE_NAV_ITEMS: readonly KnowledgeNavItem[] = [
  { href: '/dashboard/knowledge' as Route, labelKey: 'nav.overview', icon: 'home' },
  { href: '/dashboard/knowledge/documents' as Route, labelKey: 'nav.documents', icon: 'documents' },
  { href: '/dashboard/knowledge/collections' as Route, labelKey: 'nav.collections', icon: 'target' },
  { href: '/dashboard/knowledge/search' as Route, labelKey: 'nav.aiSearch', icon: 'search' },
  { href: '/dashboard/knowledge/review' as Route, labelKey: 'nav.review', icon: 'check' },
  { href: '/dashboard/knowledge/retention' as Route, labelKey: 'nav.retention', icon: 'calendar' },
  { href: '/dashboard/knowledge/audit' as Route, labelKey: 'nav.audit', icon: 'activity' },
  { href: '/dashboard/knowledge/settings' as Route, labelKey: 'nav.settings', icon: 'settings' },
] as const;
