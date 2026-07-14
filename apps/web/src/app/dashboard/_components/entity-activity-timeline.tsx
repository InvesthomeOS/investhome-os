'use client';

import { useCallback, useEffect, useState } from 'react';
import { useLocale, useTranslations } from 'next-intl';

import {
  fetchEntityActivity,
  formatActivityDate,
  metadataForI18n,
  type ActivityEntityType,
  type ActivityLogEntry,
} from '@/lib/api/activity';
import { useActivityLabels } from '@/lib/i18n/activity-labels';

interface EntityActivityTimelineProps {
  entityType: ActivityEntityType;
  entityId: string;
  title?: string;
  limit?: number;
}

export function EntityActivityTimeline({
  entityType,
  entityId,
  title,
  limit = 15,
}: EntityActivityTimelineProps) {
  const t = useTranslations('activity');
  const locale = useLocale();
  const { getDescription } = useActivityLabels();
  const [items, setItems] = useState<ActivityLogEntry[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    setError(false);
    try {
      const response = await fetchEntityActivity(entityType, entityId, limit);
      setItems(response.items);
    } catch {
      setError(true);
      setItems([]);
    } finally {
      setLoading(false);
    }
  }, [entityId, entityType, limit]);

  useEffect(() => {
    void load();
  }, [load]);

  return (
    <section className="activity-timeline">
      <h3 className="leads-form__section-title">{title ?? t('timeline.title')}</h3>
      {loading && <p className="leads__state">{t('timeline.loading')}</p>}
      {error && (
        <div className="leads__state leads__state--error">
          <p>{t('timeline.error')}</p>
          <button type="button" className="leads__button leads__button--secondary" onClick={() => void load()}>
            {t('timeline.retry')}
          </button>
        </div>
      )}
      {!loading && !error && items.length === 0 && (
        <p className="leads__state">{t('timeline.empty')}</p>
      )}
      {!loading && !error && items.length > 0 && (
        <ol className="activity-timeline__list">
          {items.map((item) => (
            <li key={item.id} className="activity-timeline__item">
              <time className="activity-timeline__time" dateTime={item.created_at}>
                {formatActivityDate(item.created_at, locale)}
              </time>
              <div className="activity-timeline__body">
                <p className="activity-timeline__summary">
                  {getDescription(item.description_key, metadataForI18n(item.metadata))}
                </p>
                {item.actor_name && (
                  <span className="activity-timeline__actor">{item.actor_name}</span>
                )}
              </div>
            </li>
          ))}
        </ol>
      )}
    </section>
  );
}
