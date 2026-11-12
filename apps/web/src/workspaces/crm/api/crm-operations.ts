import { apiFetch } from '@/lib/api/client';

import type { CrmLeadStage } from '@/workspaces/crm/api/crm-leads';

export type CrmAgreementCreateResult = {
  agreement_id: string;
  contact_id: string;
  project_group: string;
  unit_number: string | null;
  stage_label: string;
  reused_existing: boolean;
  lead_id: string | null;
  lead_stage: string | null;
};

export type CrmContactProcessLead = {
  id: string;
  name: string;
  stage: CrmLeadStage;
  active: boolean;
  focused: boolean;
};

export type CrmContactProcessAgreement = {
  id: string;
  project_group: string;
  project_label: string;
  unit_number: string | null;
  stage: string;
  stage_label: string | null;
  active: boolean;
  focused: boolean;
};

export type CrmContactProcesses = {
  contact_id: string;
  leads: CrmContactProcessLead[];
  agreements: CrmContactProcessAgreement[];
};

export type CrmPersonPayload = {
  contact_id?: string | null;
  first_name?: string | null;
  last_name?: string | null;
  phone?: string | null;
  email?: string | null;
  source?: string | null;
  address_line1?: string | null;
  city?: string | null;
  state_province?: string | null;
  country?: string | null;
  language?: string | null;
  organization_name?: string | null;
  job_title?: string | null;
  notes?: string | null;
  owner_user_id?: string | null;
  next_follow_up_at?: string | null;
};

export async function fetchContactProcesses(
  contactId: string,
  focus?: { leadId?: string | null; agreementId?: string | null },
): Promise<CrmContactProcesses> {
  const params = new URLSearchParams();
  if (focus?.leadId) params.set('lead_id', focus.leadId);
  if (focus?.agreementId) params.set('agreement_id', focus.agreementId);
  const query = params.toString();
  return apiFetch<CrmContactProcesses>(`/crm/contacts/${contactId}/processes${query ? `?${query}` : ''}`);
}

export type CrmProjectPhaseOption = { id: string; name: string; display_order?: string };
export type CrmProjectUnitOption = {
  id: string;
  label: string;
  unit_number: string;
  phase_id: string;
  phase_name: string;
  inventory_asset_id: string;
  building?: string;
  floor?: string;
  bedrooms?: string;
  bathrooms?: string;
  area_sqft?: string;
  sales_status?: string;
  list_price?: string;
  currency?: string;
};

export async function fetchProjectUnits(projectGroup: string): Promise<{
  phases: CrmProjectPhaseOption[];
  items: CrmProjectUnitOption[];
  uses_phases: boolean;
  phase_ready: boolean;
}> {
  const params = new URLSearchParams({ project_group: projectGroup });
  const payload = await apiFetch<{
    phases?: CrmProjectPhaseOption[];
    items: Array<Partial<CrmProjectUnitOption> & { id: string; label: string }>;
    uses_phases?: boolean;
    phase_ready?: boolean;
  }>(`/crm/agreements/project-units?${params.toString()}`);
  return {
    phases: payload.phases ?? [],
    uses_phases: Boolean(payload.uses_phases),
    phase_ready: payload.phase_ready !== false,
    items: (payload.items ?? []).map((item) => ({
      id: item.id,
      label: item.label,
      unit_number: item.unit_number || item.label,
      phase_id: item.phase_id || '',
      phase_name: item.phase_name || '',
      inventory_asset_id: item.inventory_asset_id || '',
      building: item.building || '',
      floor: item.floor || '',
      bedrooms: item.bedrooms || '',
      bathrooms: item.bathrooms || '',
      area_sqft: item.area_sqft || '',
      sales_status: item.sales_status || '',
      list_price: item.list_price || '',
      currency: item.currency || '',
    })),
  };
}

export async function returnAgreementToPipeline(agreementId: string, stage: string) {
  return apiFetch(`/crm/agreements/${agreementId}/return-pipeline`, {
    method: 'POST',
    body: JSON.stringify({ stage }),
  });
}

export async function cancelAgreement(
  agreementId: string,
  payload: { reason: string; note?: string | null; cancelled_on?: string | null },
) {
  return apiFetch(`/crm/agreements/${agreementId}/cancel`, {
    method: 'POST',
    body: JSON.stringify(payload),
  });
}

export async function createCrmAgreement(
  payload: CrmPersonPayload & {
    project_group: string;
    unit_number?: string | null;
    phase_id?: string | null;
    inventory_asset_id?: string | null;
    investment_amount?: string | null;
    agreement_date?: string | null;
    source_lead_id?: string | null;
  },
): Promise<CrmAgreementCreateResult> {
  return apiFetch<CrmAgreementCreateResult>('/crm/agreements', {
    method: 'POST',
    body: JSON.stringify(payload),
  });
}

export async function convertLeadToAgreement(
  leadId: string,
  payload: {
    project_group: string;
    unit_number?: string | null;
    phase_id?: string | null;
    inventory_asset_id?: string | null;
    investment_amount?: string | null;
    agreement_date?: string | null;
  },
): Promise<CrmAgreementCreateResult> {
  return apiFetch<CrmAgreementCreateResult>(`/crm/leads/${leadId}/convert-agreement`, {
    method: 'POST',
    body: JSON.stringify(payload),
  });
}

export async function updateAgreementStage(agreementId: string, stage: string): Promise<unknown> {
  return apiFetch(`/crm/agreements/${agreementId}/stage`, {
    method: 'POST',
    body: JSON.stringify({ stage }),
  });
}

export async function createCrmAgent(payload: CrmPersonPayload): Promise<{ contact_id: string; display_name: string; reused_existing: boolean }> {
  return apiFetch('/crm/agents', { method: 'POST', body: JSON.stringify(payload) });
}

export async function createAgencyCustomer(
  payload: CrmPersonPayload & { agency_contact_id: string },
): Promise<{ contact_id: string; display_name: string; reused_existing: boolean }> {
  return apiFetch('/crm/agency-customers', { method: 'POST', body: JSON.stringify(payload) });
}
