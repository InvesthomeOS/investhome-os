'use client';

import { useState } from 'react';
import { useTranslations } from 'next-intl';

import { Button, StatusChip } from '@investhome/ui';

import type { SalesShortlist } from '@/lib/api/sales-inventory-matching';

interface ShortlistPanelProps {
  shortlists: SalesShortlist[];
  canCreateProposal?: boolean;
  onCreate: (title: string) => Promise<void>;
  onAddItem: (shortlistId: string, assetId: string) => Promise<void>;
  onCreateProposal?: (shortlistId: string, title: string) => Promise<void>;
  onReload: () => Promise<void>;
}

export function ShortlistPanel({
  shortlists,
  canCreateProposal = false,
  onCreate,
  onAddItem,
  onCreateProposal,
  onReload,
}: ShortlistPanelProps) {
  const t = useTranslations('salesInventoryMatching');
  const [title, setTitle] = useState('');
  const [assetId, setAssetId] = useState('');

  return (
    <div className="shortlist-panel">
      <div className="shortlist-panel__create">
        <input
          placeholder={t('fields.shortlistTitle')}
          value={title}
          onChange={(e) => setTitle(e.target.value)}
        />
        <Button
          disabled={!title.trim()}
          onClick={() => {
            void onCreate(title.trim()).then(() => setTitle(''));
          }}
        >
          {t('actions.createShortlist')}
        </Button>
      </div>
      {shortlists.length === 0 ? (
        <p className="sales-muted">{t('empty.shortlists')}</p>
      ) : (
        shortlists.map((list) => (
          <article key={list.id} className="shortlist-card">
            <header>
              <h4>{list.title}</h4>
              <StatusChip tone="default">{list.status}</StatusChip>
            </header>
            <ol className="shortlist-items">
              {list.items.map((item) => (
                <li key={item.id}>
                  {item.asset_display_id ?? item.inventory_asset_id.slice(0, 8)}
                  {item.is_stale && <StatusChip tone="warning">{t('badges.stale')}</StatusChip>}
                  {item.notes && <span className="shortlist-item-notes">{item.notes}</span>}
                </li>
              ))}
            </ol>
            <div className="shortlist-panel__add">
              <input
                placeholder={t('fields.assetId')}
                value={assetId}
                onChange={(e) => setAssetId(e.target.value)}
              />
              <Button
                variant="secondary"
                disabled={!assetId.trim()}
                onClick={() => {
                  void onAddItem(list.id, assetId.trim()).then(() => {
                    setAssetId('');
                    return onReload();
                  });
                }}
              >
                {t('actions.addToShortlist')}
              </Button>
            </div>
            {canCreateProposal && onCreateProposal && list.items.length > 0 ? (
              <div className="shortlist-panel__proposal">
                <Button
                  variant="secondary"
                  onClick={() => {
                    void onCreateProposal(list.id, list.title);
                  }}
                >
                  {t('actions.createProposalFromShortlist')}
                </Button>
              </div>
            ) : null}
          </article>
        ))
      )}
    </div>
  );
}
