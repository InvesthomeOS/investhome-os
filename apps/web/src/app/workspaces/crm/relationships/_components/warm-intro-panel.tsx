'use client';

import { useState } from 'react';
import { useTranslations } from 'next-intl';
import { useQuery } from '@tanstack/react-query';

import { ErrorState, LoadingState } from '@investhome/ui';

import { relationshipQueries } from '@/workspaces/crm/hooks/use-relationships';
import type { RelationshipEntityType } from '@/workspaces/crm/api/relationships';

type Props = {
  sourceEntityType: RelationshipEntityType;
  sourceEntityId: string;
  defaultTargetType?: RelationshipEntityType;
  defaultTargetId?: string;
};

export function WarmIntroPanel({
  sourceEntityType,
  sourceEntityId,
  defaultTargetType,
  defaultTargetId,
}: Props) {
  const t = useTranslations('crm.relationships.intro');
  const [targetType, setTargetType] = useState<RelationshipEntityType>(defaultTargetType ?? 'contact');
  const [targetId, setTargetId] = useState(defaultTargetId ?? '');
  const [strategy, setStrategy] = useState('shortest');

  const pathsQuery = useQuery({
    ...relationshipQueries.introductionPaths({
      source_entity_type: sourceEntityType,
      source_entity_id: sourceEntityId,
      target_entity_type: targetType,
      target_entity_id: targetId,
      strategy,
    }),
    enabled: Boolean(targetId),
  });

  return (
    <div className="crm-warm-intro">
      <h3>{t('title')}</h3>
      <p>{t('description')}</p>

      <div className="crm-warm-intro-form">
        <label>
          {t('targetType')}
          <select value={targetType} onChange={(e) => setTargetType(e.target.value as RelationshipEntityType)}>
            <option value="contact">{t('contact')}</option>
            <option value="company">{t('company')}</option>
          </select>
        </label>
        <label>
          {t('targetId')}
          <input
            type="text"
            value={targetId}
            onChange={(e) => setTargetId(e.target.value)}
            placeholder={t('targetIdPlaceholder')}
          />
        </label>
        <label>
          {t('strategy')}
          <select value={strategy} onChange={(e) => setStrategy(e.target.value)}>
            <option value="shortest">{t('shortest')}</option>
            <option value="strongest">{t('strongest')}</option>
            <option value="highest_influence">{t('highestInfluence')}</option>
            <option value="all">{t('all')}</option>
          </select>
        </label>
      </div>

      {pathsQuery.isLoading && <LoadingState label={t('searching')} />}
      {pathsQuery.isError && <ErrorState title={t('searchFailed')} message={t('searchFailed')} />}

      {pathsQuery.data?.paths?.length === 0 && targetId && (
        <p>{t('noPaths')}</p>
      )}

      {pathsQuery.data?.paths?.map((path, idx) => (
        <article key={idx} className="crm-intro-path">
          <header>
            <strong>{t('path', { number: idx + 1 })}</strong>
            <span>
              {t('hops', { count: path.total_hops })} · {t('score', { value: path.total_score })} · {path.strategy}
            </span>
          </header>
          <ol>
            {path.steps.map((step, stepIdx) => (
              <li key={stepIdx}>
                <span>{step.node.label}</span>
                {step.explanation && <small>{step.explanation}</small>}
              </li>
            ))}
          </ol>
        </article>
      ))}
    </div>
  );
}
