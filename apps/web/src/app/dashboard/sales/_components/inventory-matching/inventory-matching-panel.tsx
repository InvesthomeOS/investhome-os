'use client';

import Link from 'next/link';
import { useCallback, useEffect, useMemo, useState } from 'react';
import { useTranslations } from 'next-intl';

import { Button, StatusChip } from '@investhome/ui';

import { hasPermission } from '@/lib/api/auth';
import {
  addShortlistItem,
  compareInventoryAssets,
  createInventoryMatch,
  createShortlist,
  createSoftHoldFromSales,
  favoriteInventoryMatch,
  fetchInventoryMatches,
  fetchInventoryPreferences,
  fetchShortlists,
  rejectInventoryMatch,
  saveInventoryPreferences,
  searchInventoryForMatching,
  setPrimaryInventoryMatch,
  type CompareAssetItem,
  type InventoryMatch,
  type InventoryPreference,
  type InventorySearchResultItem,
  type MatchRejectionReason,
  type SalesShortlist,
} from '@/lib/api/sales-inventory-matching';
import { createProposalFromShortlist } from '@/lib/api/sales-proposals';
import { useAuth } from '@/lib/auth/auth-context';
import { useSalesInventoryMatchingLabels } from '@/lib/i18n/sales-inventory-matching-labels';

import { InventoryCompareView } from './inventory-compare-view';
import { InventoryRejectionModal } from './inventory-rejection-modal';
import { InventorySearchCriteriaForm } from './inventory-search-criteria-form';
import { ReservationActionPanel } from './reservation-action-panel';
import { ShortlistPanel } from './shortlist-panel';

interface InventoryMatchingPanelProps {
  leadId?: string;
  opportunityId?: string;
}

export function InventoryMatchingPanel({ leadId, opportunityId }: InventoryMatchingPanelProps) {
  const t = useTranslations('salesInventoryMatching');
  const { user } = useAuth();
  const labels = useSalesInventoryMatchingLabels();

  const [preferences, setPreferences] = useState<InventoryPreference | null>(null);
  const [searchResults, setSearchResults] = useState<InventorySearchResultItem[]>([]);
  const [matches, setMatches] = useState<InventoryMatch[]>([]);
  const [shortlists, setShortlists] = useState<SalesShortlist[]>([]);
  const [compareItems, setCompareItems] = useState<CompareAssetItem[]>([]);
  const [compareSelection, setCompareSelection] = useState<string[]>([]);
  const [rejectMatchId, setRejectMatchId] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [searching, setSearching] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const canMatch = hasPermission(user, 'sales', 'add_inventory_match');
  const canSavePrefs = hasPermission(user, 'sales', 'save_inventory_preferences');
  const canShortlist = hasPermission(user, 'sales', 'create_shortlist');
  const canCompare = hasPermission(user, 'sales', 'compare_inventory');
  const canSoftHold = hasPermission(user, 'sales', 'create_soft_hold');
  const canSetPrimary = hasPermission(user, 'sales', 'set_primary_inventory');
  const canCreateProposal = hasPermission(user, 'sales', 'create_proposal');

  const contextParams = useMemo(
    () => ({ leadId, opportunityId }),
    [leadId, opportunityId],
  );

  const reload = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [pref, matchList, shortlistList] = await Promise.all([
        fetchInventoryPreferences(contextParams),
        fetchInventoryMatches({ ...contextParams, excludeRejected: false }),
        fetchShortlists(contextParams),
      ]);
      setPreferences(pref);
      setMatches(matchList);
      setShortlists(shortlistList);
    } catch (e) {
      setError(e instanceof Error ? e.message : t('errors.loadFailed'));
    } finally {
      setLoading(false);
    }
  }, [contextParams, t]);

  useEffect(() => {
    void reload();
  }, [reload]);

  const handleSavePreferences = async (values: Partial<InventoryPreference>) => {
    const saved = await saveInventoryPreferences({
      ...values,
      lead_id: leadId,
      opportunity_id: opportunityId,
    });
    setPreferences(saved);
  };

  const handleSearch = async (criteria: Record<string, unknown>) => {
    setSearching(true);
    try {
      const res = await searchInventoryForMatching({
        ...criteria,
        lead_id: leadId,
        opportunity_id: opportunityId,
        exclude_rejected: true,
      });
      setSearchResults(res.items);
    } finally {
      setSearching(false);
    }
  };

  const handleMatch = async (assetId: string) => {
    await createInventoryMatch({
      lead_id: leadId,
      opportunity_id: opportunityId,
      inventory_asset_id: assetId,
      relationship_type: 'matched',
    });
    await reload();
  };

  const handleReject = async (reason: MatchRejectionReason, notes?: string) => {
    if (!rejectMatchId) return;
    await rejectInventoryMatch(rejectMatchId, { rejection_reason: reason, notes });
    setRejectMatchId(null);
    await reload();
  };

  const favorites = matches.filter((m) => m.relationship_type === 'favorite' && m.status !== 'rejected');
  const rejected = matches.filter((m) => m.status === 'rejected' || m.relationship_type === 'rejected');
  const primary = matches.find((m) => m.is_primary);

  const toggleCompare = (assetId: string) => {
    setCompareSelection((prev) => {
      if (prev.includes(assetId)) return prev.filter((id) => id !== assetId);
      if (prev.length >= 5) return prev;
      return [...prev, assetId];
    });
  };

  const runCompare = async () => {
    if (compareSelection.length < 2) return;
    const items = await compareInventoryAssets(compareSelection);
    setCompareItems(items);
  };

  if (loading) return <p className="sales-muted">{t('loading')}</p>;
  if (error) return <p className="sales-error">{error}</p>;

  return (
    <div className="inventory-matching-panel">
      <section className="inventory-matching-section">
        <h3>{t('sections.searchCriteria')}</h3>
        <InventorySearchCriteriaForm
          preferences={preferences}
          canSave={canSavePrefs}
          onSave={handleSavePreferences}
          onSearch={handleSearch}
          searching={searching}
        />
      </section>

      <section className="inventory-matching-section">
        <h3>{t('sections.matchingResults')}</h3>
        {searchResults.length === 0 ? (
          <p className="sales-muted">{t('empty.searchResults')}</p>
        ) : (
          <ul className="inventory-match-list">
            {searchResults.map((item) => (
              <li key={item.asset_id} className="inventory-match-card">
                <div className="inventory-match-card__header">
                  <Link href={`/dashboard/inventory?id=${item.asset_id}`}>
                    {item.display_id ?? item.system_code}
                  </Link>
                  {item.is_stale && <StatusChip tone="warning">{t('badges.stale')}</StatusChip>}
                </div>
                <dl className="inventory-match-card__meta">
                  <div><dt>{t('fields.availability')}</dt><dd>{labels.getAvailabilityLabel(item.availability_status)}</dd></div>
                  <div><dt>{t('fields.price')}</dt><dd>{item.list_price ? `${item.list_price} ${item.currency}` : t('priceHidden')}</dd></div>
                  <div><dt>{t('fields.area')}</dt><dd>{item.interior_area_sqft ?? '—'}</dd></div>
                </dl>
                <div className="inventory-match-card__actions">
                  {canCompare && (
                    <Button variant="ghost" onClick={() => toggleCompare(item.asset_id)}>
                      {compareSelection.includes(item.asset_id) ? t('actions.compareSelected') : t('actions.compare')}
                    </Button>
                  )}
                  {canMatch && (
                    <Button variant="secondary" onClick={() => void handleMatch(item.asset_id)}>
                      {t('actions.match')}
                    </Button>
                  )}
                </div>
              </li>
            ))}
          </ul>
        )}
      </section>

      {canShortlist && (
        <section className="inventory-matching-section">
          <h3>{t('sections.shortlists')}</h3>
          <ShortlistPanel
            shortlists={shortlists}
            canCreateProposal={canCreateProposal && Boolean(opportunityId)}
            onCreate={async (title) => {
              await createShortlist({ lead_id: leadId, opportunity_id: opportunityId, title });
              await reload();
            }}
            onAddItem={async (shortlistId, assetId) => {
              await addShortlistItem(shortlistId, { inventory_asset_id: assetId });
              await reload();
            }}
            onCreateProposal={
              opportunityId
                ? async (shortlistId, title) => {
                    const proposal = await createProposalFromShortlist({
                      opportunity_id: opportunityId,
                      shortlist_id: shortlistId,
                      title,
                      lead_id: leadId,
                    });
                    window.location.href = `/dashboard/sales/proposals/${proposal.id}`;
                  }
                : undefined
            }
            onReload={reload}
          />
        </section>
      )}

      <section className="inventory-matching-section">
        <h3>{t('sections.favorites')}</h3>
        {favorites.length === 0 ? (
          <p className="sales-muted">{t('empty.favorites')}</p>
        ) : (
          <ul className="inventory-match-list">
            {favorites.map((m) => (
              <li key={m.id}>{m.asset_display_id ?? m.inventory_asset_id.slice(0, 8)}</li>
            ))}
          </ul>
        )}
      </section>

      {primary && (
        <section className="inventory-matching-section">
          <h3>{t('sections.primary')}</h3>
          <p>{primary.asset_display_id} {primary.is_stale && <StatusChip tone="warning">{t('badges.stale')}</StatusChip>}</p>
        </section>
      )}

      <section className="inventory-matching-section">
        <h3>{t('sections.rejected')}</h3>
        {rejected.length === 0 ? (
          <p className="sales-muted">{t('empty.rejected')}</p>
        ) : (
          <ul className="inventory-match-list">
            {rejected.map((m) => (
              <li key={m.id}>
                {m.asset_display_id} — {m.rejection_reason ? labels.getRejectionReasonLabel(m.rejection_reason) : '—'}
              </li>
            ))}
          </ul>
        )}
      </section>

      {canCompare && (
        <section className="inventory-matching-section">
          <h3>{t('sections.compare')}</h3>
          <div className="inventory-compare-toolbar">
            <Button disabled={compareSelection.length < 2} onClick={() => void runCompare()}>
              {t('actions.runCompare', { count: compareSelection.length })}
            </Button>
          </div>
          {compareItems.length > 0 && <InventoryCompareView items={compareItems} />}
        </section>
      )}

      {canSoftHold && (
        <section className="inventory-matching-section">
          <h3>{t('sections.reservationActions')}</h3>
          <ReservationActionPanel
            leadId={leadId}
            opportunityId={opportunityId}
            selectedAssetId={compareSelection[0] ?? searchResults[0]?.asset_id}
            onSoftHold={createSoftHoldFromSales}
            onComplete={reload}
          />
        </section>
      )}

      <InventoryRejectionModal
        open={rejectMatchId !== null}
        onClose={() => setRejectMatchId(null)}
        onConfirm={handleReject}
      />

      {matches.filter((m) => m.status === 'active' && !m.is_primary).length > 0 && canSetPrimary && (
        <section className="inventory-matching-section">
          <h3>{t('sections.activeMatches')}</h3>
          <ul className="inventory-match-list">
            {matches
              .filter((m) => m.status === 'active')
              .map((m) => (
                <li key={m.id} className="inventory-match-card">
                  <span>{m.asset_display_id}</span>
                  <div className="inventory-match-card__actions">
                    <Button variant="ghost" onClick={() => void favoriteInventoryMatch(m.id).then(reload)}>
                      {t('actions.favorite')}
                    </Button>
                    {opportunityId && (
                      <Button variant="secondary" onClick={() => void setPrimaryInventoryMatch(m.id).then(reload)}>
                        {t('actions.setPrimary')}
                      </Button>
                    )}
                    <Button variant="ghost" onClick={() => setRejectMatchId(m.id)}>
                      {t('actions.reject')}
                    </Button>
                  </div>
                </li>
              ))}
          </ul>
        </section>
      )}
    </div>
  );
}
