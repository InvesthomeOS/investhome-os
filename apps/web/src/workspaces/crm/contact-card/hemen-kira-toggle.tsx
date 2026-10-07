'use client';

import { useMutation, useQueryClient } from '@tanstack/react-query';

import { useLocale } from 'next-intl';

import { patchAgreement } from '@/workspaces/crm/api/agreements';
import { personCardCopy } from '@/workspaces/crm/contact-card/person-card-copy';

export function HemenKiraToggle({
  agreementId,
  value,
}: {
  agreementId: string;
  value: boolean;
}) {
  const t = personCardCopy(useLocale());
  const queryClient = useQueryClient();
  const mutation = useMutation({
    mutationFn: (hemenKira: boolean) => patchAgreement(agreementId, { hemen_kira: hemenKira }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['crm', 'purchases'] });
      queryClient.invalidateQueries({ queryKey: ['crm', 'agreements'] });
      queryClient.invalidateQueries({ queryKey: ['crm', 'sales-detail'] });
    },
  });

  return (
    <div className="crm-hemen-kira" data-testid="hemen-kira-toggle">
      <button
        type="button"
        role="switch"
        aria-checked={Boolean(value)}
        disabled={mutation.isPending}
        onClick={() => mutation.mutate(!value)}
      >
        {value ? `${t.hemenKira}: ${t.yes}` : `${t.hemenKira}: ${t.no}`}
      </button>
      {mutation.isError ? <small>{t.saveFailed}</small> : null}
    </div>
  );
}
