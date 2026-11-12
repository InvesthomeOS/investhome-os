'use client';

import { useState } from 'react';
import { useQuery, useQueryClient } from '@tanstack/react-query';

import { Select } from '@investhome/ui';

import { ApiError } from '@/lib/api/client';
import { crmLeadStageLabel, CRM_LEAD_STAGES, moveCrmLeadStage, type CrmLeadStage } from '@/workspaces/crm/api/crm-leads';
import { fetchContactProcesses, updateAgreementStage } from '@/workspaces/crm/api/crm-operations';
import { AGREEMENT_STAGE_OPTIONS, agreementStageLabel } from '@/workspaces/crm/crm-source-options';

export function ActiveProcesses({
  contactId,
  canUpdate,
  focusLeadId,
  focusAgreementId,
}: {
  contactId: string;
  canUpdate: boolean;
  focusLeadId?: string | null;
  focusAgreementId?: string | null;
}) {
  const queryClient = useQueryClient();
  const [error, setError] = useState<string | null>(null);
  const query = useQuery({
    queryKey: ['crm', 'processes', contactId, focusLeadId, focusAgreementId],
    queryFn: () => fetchContactProcesses(contactId, { leadId: focusLeadId, agreementId: focusAgreementId }),
  });

  const refresh = async () => {
    await queryClient.invalidateQueries({ queryKey: ['crm', 'processes', contactId] });
    await queryClient.invalidateQueries({ queryKey: ['crm'] });
    await queryClient.invalidateQueries({ queryKey: ['crm-leads'] });
    await queryClient.invalidateQueries({ queryKey: ['crm-contact', contactId] });
  };

  const changeLead = async (id: string, stage: CrmLeadStage) => {
    setError(null);
    try {
      await moveCrmLeadStage(id, stage);
      await refresh();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Aşama kaydedilemedi.');
    }
  };

  const changeAgreement = async (id: string, stage: string) => {
    setError(null);
    try {
      await updateAgreementStage(id, stage);
      await refresh();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Aşama kaydedilemedi.');
    }
  };

  const leads = query.data?.leads ?? [];
  const agreements = query.data?.agreements ?? [];
  if (query.isLoading) return null;
  if (!leads.length && !agreements.length) return null;

  return (
    <section className="crm-active-processes" data-testid="contact-active-processes">
      <h2>Aktif Süreçler</h2>
      <ul>
        {leads.map((lead) => (
          <li key={lead.id} data-focused={lead.focused || lead.id === focusLeadId ? 'true' : 'false'}>
            <span>Lead | {crmLeadStageLabel(lead.stage, 'tr')}</span>
            {canUpdate && lead.stage !== 'converted' ? (
              <Select label="Lead aşaması" value={lead.stage} onChange={(event) => void changeLead(lead.id, event.target.value as CrmLeadStage)}>
                {CRM_LEAD_STAGES.filter((item) => item !== 'converted').map((item) => (
                  <option key={item} value={item}>{crmLeadStageLabel(item, 'tr')}</option>
                ))}
              </Select>
            ) : null}
          </li>
        ))}
        {agreements.map((agreement) => (
          <li key={agreement.id} data-focused={agreement.focused || agreement.id === focusAgreementId ? 'true' : 'false'}>
            <span>
              {agreement.project_label}
              {agreement.unit_number ? ` | Unit ${agreement.unit_number}` : ''} | {agreementStageLabel(agreement.stage)}
            </span>
            {canUpdate ? (
              <Select
                label="Anlaşma aşaması"
                value={AGREEMENT_STAGE_OPTIONS.some((item) => item.value === agreement.stage) ? agreement.stage : ''}
                onChange={(event) => void changeAgreement(agreement.id, event.target.value)}
              >
                {!AGREEMENT_STAGE_OPTIONS.some((item) => item.value === agreement.stage) ? (
                  <option value="">{agreementStageLabel(agreement.stage)}</option>
                ) : null}
                {AGREEMENT_STAGE_OPTIONS.map((item) => (
                  <option key={item.value} value={item.value}>{item.label}</option>
                ))}
              </Select>
            ) : null}
          </li>
        ))}
      </ul>
      {error ? <p role="alert">{error}</p> : null}
    </section>
  );
}
