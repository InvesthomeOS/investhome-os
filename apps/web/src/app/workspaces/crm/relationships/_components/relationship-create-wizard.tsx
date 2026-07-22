'use client';

import { useState } from 'react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { useTranslations } from 'next-intl';
import { useMutation, useQuery } from '@tanstack/react-query';

import { Button, ErrorState, LoadingState } from '@investhome/ui';

import { crmLabel } from '@/lib/crm/crm-labels';
import { useCrmAccess } from '@/lib/crm/use-crm-access';
import { contactQueries } from '@/workspaces/crm/hooks/use-contacts';
import { relationshipMutations } from '@/workspaces/crm/hooks/use-relationships';
import type { RelationshipEntityType } from '@/workspaces/crm/api/relationships';

const STEPS = [
  'entities',
  'type',
  'reciprocal',
  'category',
  'strength',
  'confidential',
  'notes',
  'duplicates',
  'review',
  'confirm',
] as const;

const RELATIONSHIP_TYPES = [
  'colleague',
  'partner',
  'parent',
  'subsidiary',
  'client',
  'vendor',
  'referred_by',
  'referred_to',
  'investor',
  'advisor',
  'employs',
  'employed_by',
  'other',
];

const RECIPROCAL_MAP: Record<string, string> = {
  parent: 'subsidiary',
  subsidiary: 'parent',
  referred_by: 'referred_to',
  referred_to: 'referred_by',
  client: 'vendor',
  vendor: 'client',
  investor: 'investee',
  advisor: 'advisee',
  employs: 'employed_by',
  employed_by: 'employs',
  colleague: 'colleague',
  partner: 'partner',
  other: 'other',
};

export function RelationshipCreateWizard() {
  const t = useTranslations('crm.relationships.createWizard');
  const tTypes = useTranslations('crm.relationships.types');
  const tCategories = useTranslations('crm.relationships.categories');
  const tStrengths = useTranslations('crm.relationships.strengths');
  const tCommon = useTranslations('common');
  const router = useRouter();
  const { authLoading, canCreate } = useCrmAccess();
  const [step, setStep] = useState(0);
  const [sourceId, setSourceId] = useState('');
  const [targetId, setTargetId] = useState('');
  const [sourceType] = useState<RelationshipEntityType>('contact');
  const [targetType] = useState<RelationshipEntityType>('contact');
  const [relationshipType, setRelationshipType] = useState('colleague');
  const [strength, setStrength] = useState('moderate');
  const [category, setCategory] = useState('commercial');
  const [isConfidential, setIsConfidential] = useState(false);
  const [notes, setNotes] = useState('');
  const [duplicateWarning, setDuplicateWarning] = useState<string | null>(null);

  const contactsQuery = useQuery(contactQueries.list({ page: 1, page_size: 50 }));

  const createMutation = useMutation({
    mutationFn: relationshipMutations.create,
    onSuccess: (data) => router.push(`/workspaces/crm/relationships/${data.id}`),
  });

  const checkDuplicates = async () => {
    const payload = {
      source_entity_type: sourceType,
      source_entity_id: sourceId,
      target_entity_type: targetType,
      target_entity_id: targetId,
      relationship_type: relationshipType,
    };
    const dups = await relationshipMutations.checkDuplicates(payload);
    setDuplicateWarning(dups.length > 0 ? t('duplicateFound') : null);
    return dups.length === 0;
  };

  const handleNext = async () => {
    if (STEPS[step] === 'duplicates') {
      const ok = await checkDuplicates();
      if (!ok) return;
    }
    if (step < STEPS.length - 1) setStep(step + 1);
  };

  const handleSubmit = () => {
    createMutation.mutate({
      source_entity_type: sourceType,
      source_entity_id: sourceId,
      target_entity_type: targetType,
      target_entity_id: targetId,
      relationship_type: relationshipType,
      category,
      strength,
      is_confidential: isConfidential,
      notes: notes || undefined,
    });
  };

  if (authLoading) {
    return <LoadingState label={tCommon('loading')} />;
  }

  if (!canCreate) return <ErrorState title={t('accessDenied')} message={t('accessDenied')} />;

  const currentStep = STEPS[step];
  const reciprocal = RECIPROCAL_MAP[relationshipType] ?? relationshipType;
  const typeLabel = (value: string) => crmLabel(tTypes, value);
  const categoryLabel = (value: string) => crmLabel(tCategories, value);
  const strengthLabel = (value: string) => crmLabel(tStrengths, value);

  return (
    <div className="crm-relationship-create">
      <header>
        <Link href="/workspaces/crm/relationships">{t('back')}</Link>
        <h1>{t('title')}</h1>
        <p>{t('step', { current: step + 1, total: STEPS.length, name: t(`steps.${currentStep}`) })}</p>
      </header>

      <div className="crm-create-progress">
        {STEPS.map((s, i) => (
          <span key={s} className={i <= step ? 'done' : ''} />
        ))}
      </div>

      {currentStep === 'entities' && (
        <section>
          <h2>{t('steps.entities')}</h2>
          {contactsQuery.isLoading ? (
            <LoadingState label={t('loadingContacts')} />
          ) : (
            <>
              <label>
                {t('source')}
                <select value={sourceId} onChange={(e) => setSourceId(e.target.value)}>
                  <option value="">{t('selectContact')}</option>
                  {contactsQuery.data?.items.map((c) => (
                    <option key={c.id} value={c.id}>{c.display_name}</option>
                  ))}
                </select>
              </label>
              <label>
                {t('target')}
                <select value={targetId} onChange={(e) => setTargetId(e.target.value)}>
                  <option value="">{t('selectContact')}</option>
                  {contactsQuery.data?.items.map((c) => (
                    <option key={c.id} value={c.id}>{c.display_name}</option>
                  ))}
                </select>
              </label>
            </>
          )}
        </section>
      )}

      {currentStep === 'type' && (
        <section>
          <h2>{t('steps.type')}</h2>
          <select value={relationshipType} onChange={(e) => setRelationshipType(e.target.value)}>
            {RELATIONSHIP_TYPES.map((rt) => (
              <option key={rt} value={rt}>{typeLabel(rt)}</option>
            ))}
          </select>
        </section>
      )}

      {currentStep === 'reciprocal' && (
        <section>
          <h2>{t('steps.reciprocal')}</h2>
          <p>{t('reciprocalPreview', { type: typeLabel(relationshipType), reciprocal: typeLabel(reciprocal) })}</p>
          <p>{t('singleRecordNote')}</p>
        </section>
      )}

      {currentStep === 'category' && (
        <section>
          <h2>{t('steps.category')}</h2>
          <select value={category} onChange={(e) => setCategory(e.target.value)}>
            {['organizational', 'commercial', 'personal', 'referral', 'investment', 'operational', 'other'].map(
              (c) => <option key={c} value={c}>{categoryLabel(c)}</option>,
            )}
          </select>
        </section>
      )}

      {currentStep === 'strength' && (
        <section>
          <h2>{t('steps.strength')}</h2>
          <select value={strength} onChange={(e) => setStrength(e.target.value)}>
            {['weak', 'moderate', 'strong', 'strategic'].map((s) => (
              <option key={s} value={s}>{strengthLabel(s)}</option>
            ))}
          </select>
        </section>
      )}

      {currentStep === 'confidential' && (
        <section>
          <h2>{t('steps.confidential')}</h2>
          <label>
            <input
              type="checkbox"
              checked={isConfidential}
              onChange={(e) => setIsConfidential(e.target.checked)}
            />
            {t('markConfidential')}
          </label>
        </section>
      )}

      {currentStep === 'notes' && (
        <section>
          <h2>{t('steps.notes')}</h2>
          <textarea value={notes} onChange={(e) => setNotes(e.target.value)} rows={4} />
        </section>
      )}

      {currentStep === 'duplicates' && (
        <section>
          <h2>{t('steps.duplicates')}</h2>
          {duplicateWarning ? (
            <p className="crm-error">{duplicateWarning}</p>
          ) : (
            <p>{t('noDuplicates')}</p>
          )}
        </section>
      )}

      {currentStep === 'review' && (
        <section>
          <h2>{t('steps.review')}</h2>
          <dl>
            <dt>{t('source')}</dt><dd>{sourceId}</dd>
            <dt>{t('target')}</dt><dd>{targetId}</dd>
            <dt>{t('type')}</dt><dd>{typeLabel(relationshipType)} → {typeLabel(reciprocal)}</dd>
            <dt>{t('strength')}</dt><dd>{strengthLabel(strength)}</dd>
          </dl>
        </section>
      )}

      {currentStep === 'confirm' && (
        <section>
          <h2>{t('steps.confirm')}</h2>
          <p>{t('confirmMessage')}</p>
          {createMutation.isError && (
            <p className="crm-error">
              {t('createFailed')}
              {createMutation.error instanceof Error && createMutation.error.message
                ? `: ${createMutation.error.message}`
                : ''}
            </p>
          )}
        </section>
      )}

      <footer className="crm-create-actions">
        <Button variant="secondary" disabled={step === 0} onClick={() => setStep(step - 1)}>
          {t('previous')}
        </Button>
        {step < STEPS.length - 1 ? (
          <Button onClick={handleNext} disabled={!sourceId || !targetId}>
            {t('next')}
          </Button>
        ) : (
          <Button onClick={handleSubmit} disabled={createMutation.isPending}>
            {t('submit')}
          </Button>
        )}
      </footer>
    </div>
  );
}
