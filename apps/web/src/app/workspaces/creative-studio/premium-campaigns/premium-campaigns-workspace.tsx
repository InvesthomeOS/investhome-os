'use client';

import type { Route } from 'next';
import Link from 'next/link';
import { useEffect, useState } from 'react';
import { useTranslations } from 'next-intl';

import { StatusChip } from '@investhome/ui';

import { CsPageHeader } from '../_components/cs-page-header';
import { PREMIUM_CAMPAIGNS_ROUTE } from '../_components/ds/creative-studio-ds-model';
import {
  fetchCreativeStudioMediaBlob,
  listPremiumCampaigns,
  type PremiumCampaignCard,
  type PremiumCampaignFormatId,
} from '@/lib/api/creative-studio';

import '../_components/ds/creative-studio-ds.css';
import './premium-campaigns.css';

const FORMAT_ORDER: PremiumCampaignFormatId[] = ['4:5', '9:16', '1:1'];

function FormatChips({
  formats,
  labelFor,
}: {
  formats: PremiumCampaignFormatId[];
  labelFor: (fmt: PremiumCampaignFormatId) => string;
}) {
  return (
    <ul className="pc-card__formats">
      {FORMAT_ORDER.filter((fmt) => formats.includes(fmt)).map((fmt) => (
        <li key={fmt}>
          <StatusChip tone="info">{labelFor(fmt)}</StatusChip>
        </li>
      ))}
    </ul>
  );
}

export function PremiumCampaignsWorkspace() {
  const t = useTranslations('creativeStudio.ds');
  const [campaigns, setCampaigns] = useState<PremiumCampaignCard[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [thumbs, setThumbs] = useState<Record<string, string>>({});

  useEffect(() => {
    let cancelled = false;
    void listPremiumCampaigns()
      .then(async (response) => {
        if (cancelled) return;
        setCampaigns(response.campaigns);
        const next: Record<string, string> = {};
        await Promise.all(
          response.campaigns.map(async (campaign) => {
            if (!campaign.preview_asset_id) return;
            const blob = await fetchCreativeStudioMediaBlob(campaign.preview_asset_id);
            next[campaign.id] = URL.createObjectURL(blob);
          }),
        );
        if (!cancelled) setThumbs(next);
      })
      .catch(() => {
        if (!cancelled) setError(t('premium.loadError'));
      });
    return () => {
      cancelled = true;
    };
  }, [t]);

  useEffect(() => {
    return () => {
      Object.values(thumbs).forEach((url) => URL.revokeObjectURL(url));
    };
  }, [thumbs]);

  return (
    <main className="dashboard pc-page" data-testid="premium-campaigns-page">
      <CsPageHeader
        title={t('premium.listTitle')}
        subtitle={t('premium.listSubtitle')}
        titleIcon="target"
        backHref="/workspaces/creative-studio"
        backLabel={t('premium.backStudio')}
        testId="premium-campaigns-header"
      />

      {error ? <p className="pc-empty">{error}</p> : null}
      {campaigns && campaigns.length === 0 ? <p className="pc-empty">{t('premium.empty')}</p> : null}

      <section className="pc-grid" aria-label={t('premium.listTitle')}>
        {(campaigns ?? []).map((campaign) => (
          <Link
            key={campaign.id}
            href={`${PREMIUM_CAMPAIGNS_ROUTE}/${campaign.id}` as Route}
            className="pc-card"
            data-testid={`pc-card-${campaign.id}`}
          >
            <span className="pc-card__preview">
              {thumbs[campaign.id] ? (
                // eslint-disable-next-line @next/next/no-img-element
                <img src={thumbs[campaign.id]} alt="" />
              ) : (
                <span className="pc-card__ph" aria-hidden="true" />
              )}
            </span>
            <span className="pc-card__body">
              <strong>{campaign.title}</strong>
              {campaign.subtitle ? <span className="pc-card__offer">{campaign.subtitle}</span> : null}
              <span className="pc-card__project">{campaign.project}</span>
              <FormatChips
                formats={campaign.available_formats}
                labelFor={(fmt) => t(`premium.formats.${fmt}`)}
              />
              {campaign.updated_at ? (
                <span className="pc-card__meta">
                  {t('premium.updated')}
                </span>
              ) : null}
              <span className="cs-ds__tool-launch">
                {t('premium.open')}
              </span>
            </span>
          </Link>
        ))}
      </section>
    </main>
  );
}
