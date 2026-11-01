'use client';

import { investorChrome } from '@/app/investor/_components/investor-labels';

import { useTranslations } from 'next-intl';

import Link from 'next/link';
import type { Route } from 'next';

import type { MessagingSearchResult } from '../../_data/messaging-types';
import { formatInvestorDateTime } from '../../_data/mock-data';

interface GlobalSearchPanelProps {
  results: MessagingSearchResult[];
  query: string;
  onClose: () => void;
}

const TYPE_LABELS: Record<MessagingSearchResult['type'], string> = {
  conversation: 'Conversation',
  message: 'Message',
  announcement: 'Announcement',
  notification: 'Notification',
  task: 'Task',
};

export function GlobalSearchPanel({ results, query, onClose }: GlobalSearchPanelProps) {
  const tChrome = useTranslations('investorPortal.chrome');
  if (!query.trim()) return null;

  return (
    <div className="inv-global-search" role="region" aria-label={tChrome('k0144dae8fb')}>
      <div className="inv-global-search__header">
        <span>
          {results.length} result{results.length !== 1 ? 's' : ''} for &ldquo;{query}&rdquo;
        </span>
        <button type="button" onClick={onClose} aria-label={tChrome('k7e9ff47d1e')}>
          ×
        </button>
      </div>
      {results.length === 0 ? (
        <p className="inv-global-search__empty">{tChrome('ke3d92ad624')}</p>
      ) : (
        <ul className="inv-global-search__list">
          {results.slice(0, 12).map((result) => (
            <li key={`${result.type}-${result.id}`}>
              <Link
                href={result.href as Route}
                className="inv-global-search__item"
                onClick={onClose}
              >
                <span className="inv-global-search__type">{investorChrome(tChrome, TYPE_LABELS[result.type])}</span>
                <strong>{result.title}</strong>
                <span className="inv-global-search__subtitle">{result.subtitle}</span>
                <time dateTime={result.timestamp}>
                  {formatInvestorDateTime(result.timestamp)}
                </time>
              </Link>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
