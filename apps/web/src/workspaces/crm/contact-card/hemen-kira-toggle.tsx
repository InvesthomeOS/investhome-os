'use client';

import { useMutation, useQueryClient } from '@tanstack/react-query';

import { patchAgreement } from '@/workspaces/crm/api/agreements';

export function HemenKiraToggle({
  agreementId,
  value,
}: {
  agreementId: string;
  value: boolean;
}) {
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
        {value ? 'Hemen Kira: Evet' : 'Hemen Kira: Hayır'}
      </button>
      {mutation.isError ? <small>Kaydedilemedi</small> : null}
    </div>
  );
}
