'use client';

import { useState } from 'react';
import { useMutation } from '@tanstack/react-query';

import { Button, Input } from '@investhome/ui';

import { ApiError } from '@/lib/api/client';
import { ownershipShareError } from '@/lib/crm/ownership-share';
import { fetchContacts } from '@/workspaces/crm/api/contacts';
import {
  removeAgreementOwner,
  replaceAgreementOwners,
  type CrmPurchaseCard,
} from '@/workspaces/crm/api/agreements';

type Share = { contact_id: string; display_name: string; ownership_pct: string };

function asShares(card: CrmPurchaseCard): Share[] {
  return card.participants.map((owner) => ({
    contact_id: owner.contact_id,
    display_name: owner.display_name,
    ownership_pct: (owner.ownership_pct || '0').replace(/\.00$/, ''),
  }));
}

export function AgreementOwnersEditor({
  card,
  onChanged,
}: {
  card: CrmPurchaseCard;
  onChanged: () => void;
}) {
  const [shares, setShares] = useState<Share[]>(() => asShares(card));
  const [query, setQuery] = useState('');
  const [matches, setMatches] = useState<Array<{ id: string; display_name: string }>>([]);
  const [pendingRemove, setPendingRemove] = useState<Share | null>(null);
  const [error, setError] = useState<string | null>(null);

  const save = useMutation({
    mutationFn: () => {
      const message = ownershipShareError(shares.map((item) => item.ownership_pct));
      if (message) throw new Error(message);
      return replaceAgreementOwners(
        card.agreement_id,
        shares.map((item) => ({ contact_id: item.contact_id, ownership_pct: item.ownership_pct })),
      );
    },
    onSuccess: () => {
      setError(null);
      onChanged();
    },
    onError: (err: unknown) => {
      setError(err instanceof ApiError ? err.message : 'Sahiplik kaydedilemedi.');
    },
  });

  const remove = useMutation({
    mutationFn: (contactId: string) => removeAgreementOwner(card.agreement_id, contactId),
    onSuccess: () => {
      setPendingRemove(null);
      setError(null);
      onChanged();
    },
    onError: (err: unknown) => {
      setError(err instanceof ApiError ? err.message : 'Kişi ilişkiden çıkarılamadı.');
    },
  });

  const search = async () => {
    const term = query.trim();
    if (term.length < 2) return;
    const response = await fetchContacts({ search: term, page: 1, page_size: 6 });
    setMatches(response.items.map((item) => ({ id: item.id, display_name: item.display_name })));
  };

  return (
    <div className="crm-pd-owners-edit" data-testid="agreement-owners-editor">
      <p>Sahiplik düzeltmesi kişi kaydını, notları, e-postaları veya belgeleri silmez.</p>
      {shares.map((owner) => (
        <div key={owner.contact_id} className="crm-pd-owners-edit__row">
          <strong>{owner.display_name}</strong>
          <Input
            label="Pay %"
            value={owner.ownership_pct}
            onChange={(event) =>
              setShares((current) =>
                current.map((item) =>
                  item.contact_id === owner.contact_id
                    ? { ...item, ownership_pct: event.target.value }
                    : item,
                ),
              )
            }
          />
          <Button type="button" size="sm" variant="ghost" onClick={() => setPendingRemove(owner)}>
            Sahibi çıkar
          </Button>
        </div>
      ))}
      <div className="crm-pd-owners-edit__add">
        <Input label="Kişi ara" value={query} onChange={(event) => setQuery(event.target.value)} />
        <Button type="button" size="sm" onClick={() => void search()}>
          Ara
        </Button>
        {matches.map((match) => (
          <button
            key={match.id}
            type="button"
            onClick={() => {
              setShares((current) =>
                current.some((item) => item.contact_id === match.id)
                  ? current
                  : [...current, { contact_id: match.id, display_name: match.display_name, ownership_pct: '' }],
              );
              setMatches([]);
              setQuery('');
            }}
          >
            {match.display_name}
          </button>
        ))}
      </div>
      <Button type="button" size="sm" disabled={save.isPending} onClick={() => save.mutate()}>
        Sahipliği kaydet
      </Button>
      {error ? <p className="crm-pd-error">{error}</p> : null}
      {pendingRemove ? (
        <div role="dialog" aria-modal="true" data-testid="remove-owner-confirm">
          <p>
            {pendingRemove.display_name} bu satın alma ilişkisinden çıkarılacak. Kişi kaydı ve geçmişi durur.
          </p>
          <Button type="button" size="sm" disabled={remove.isPending} onClick={() => remove.mutate(pendingRemove.contact_id)}>
            İlişkiyi kaldır
          </Button>
          <Button type="button" size="sm" variant="ghost" onClick={() => setPendingRemove(null)}>
            Vazgeç
          </Button>
        </div>
      ) : null}
    </div>
  );
}
