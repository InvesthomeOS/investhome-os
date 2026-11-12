'use client';

import { useEffect, useState } from 'react';
import { useQuery, useQueryClient } from '@tanstack/react-query';

import { Button, Input, Select } from '@investhome/ui';

import { fetchUsers } from '@/lib/api/auth';
import { ApiError } from '@/lib/api/client';
import { fetchContacts, fetchMembershipProjects } from '@/workspaces/crm/api/contacts';
import {
  convertLeadToAgreement,
  createAgencyCustomer,
  createCrmAgent,
  createCrmAgreement,
  fetchProjectUnits,
} from '@/workspaces/crm/api/crm-operations';
import { unitIdentifier, unitSelectionLabel, unitsForPhase } from '@/workspaces/crm/project-phase-unit.mjs';
import { currencyPrefix } from '@/workspaces/crm/money';
import {
  CrmContactPicker,
  CrmPersonFields,
  EMPTY_PERSON_DRAFT,
  personPayload,
  type CrmPersonDraft,
} from '@/workspaces/crm/crm-person-fields';

export type CrmRecordMode = 'agreement' | 'convert' | 'agent' | 'agency-customer';

export function CrmRecordDialog({
  mode,
  leadId,
  contactId,
  onClose,
  onDone,
}: {
  mode: CrmRecordMode;
  leadId?: string | null;
  contactId?: string | null;
  onClose: () => void;
  onDone: (message: string, result?: { agreement_id?: string; contact_id?: string; reused_existing?: boolean }) => void;
}) {
  const queryClient = useQueryClient();
  const [person, setPerson] = useState<CrmPersonDraft>({ ...EMPTY_PERSON_DRAFT, contact_id: contactId || '' });
  const [selectedName, setSelectedName] = useState('');
  const [projectGroup, setProjectGroup] = useState('');
  const [phaseId, setPhaseId] = useState('');
  const [unitNumber, setUnitNumber] = useState('');
  const [inventoryAssetId, setInventoryAssetId] = useState('');
  const [amount, setAmount] = useState('');
  const [agreementDate, setAgreementDate] = useState('');
  const [agencyId, setAgencyId] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [pending, setPending] = useState(false);
  const needsSale = mode === 'agreement' || mode === 'convert';

  const usersQuery = useQuery({
    queryKey: ['crm', 'active-users'],
    queryFn: () => fetchUsers({ status: 'active' }),
  });
  const membershipQuery = useQuery({
    queryKey: ['crm-membership-projects'],
    queryFn: fetchMembershipProjects,
    enabled: needsSale,
  });
  const projectOptions = (membershipQuery.data ?? []).filter((item, index, all) => {
    const key = item.project_id || item.project_group;
    return Boolean(key) && all.findIndex((row) => (row.project_id || row.project_group) === key) === index;
  });
  const unitsQuery = useQuery({
    queryKey: ['crm', 'project-units', projectGroup],
    queryFn: () => fetchProjectUnits(projectGroup),
    enabled: needsSale && Boolean(projectGroup),
  });
  const agentsQuery = useQuery({
    queryKey: ['crm', 'agent-options'],
    queryFn: () => fetchContacts({ category: 'agent', page: 1, page_size: 100, sort_by: 'display_name', sort_dir: 'asc' }),
    enabled: mode === 'agency-customer',
  });

  useEffect(() => {
    if (contactId) setPerson((current) => ({ ...current, contact_id: contactId }));
  }, [contactId]);

  const title =
    mode === 'convert'
      ? 'Anlaşmaya Dönüştür'
      : mode === 'agreement'
        ? 'Yeni Anlaşma'
        : mode === 'agent'
          ? 'Yeni Acente'
          : 'Yeni Acente Müşterisi';

  const submit = async () => {
    setPending(true);
    setError(null);
    try {
      const selectedProject = projectOptions.find((item) => (item.project_group || item.project_id) === projectGroup);
      const saveGroup = selectedProject?.project_group || (projectGroup.includes('-') ? '' : projectGroup);
      if (needsSale && !saveGroup) throw new Error('Proje seçin.');
      if (needsSale && unitsQuery.data?.uses_phases && !phaseId) {
        throw new Error('Faz seçin.');
      }
      if (mode === 'agent') {
        const result = await createCrmAgent(personPayload(person));
        onDone(result.reused_existing ? 'Mevcut kişi acente olarak bağlandı.' : 'Acente oluşturuldu.', result);
      } else if (mode === 'agency-customer') {
        if (!agencyId) throw new Error('Acente seçin');
        const result = await createAgencyCustomer({ ...personPayload(person), agency_contact_id: agencyId });
        onDone(result.reused_existing ? 'Mevcut kişi acente müşterisi olarak bağlandı.' : 'Acente müşterisi oluşturuldu.', result);
      } else if (mode === 'convert' && leadId) {
        const result = await convertLeadToAgreement(leadId, {
          project_group: saveGroup,
          unit_number: unitIdentifier(unitNumber) || null,
          phase_id: phaseId || null,
          inventory_asset_id: inventoryAssetId || null,
          investment_amount: amount || null,
          agreement_date: agreementDate || null,
        });
        onDone(
          result.reused_existing ? 'Mevcut anlaşma açıldı. Yeni kayıt oluşturulmadı.' : 'Anlaşma oluşturuldu. Lead kazanıldı.',
          result,
        );
      } else {
        const result = await createCrmAgreement({
          ...personPayload(person),
          contact_id: person.contact_id || contactId || null,
          project_group: saveGroup,
          unit_number: unitIdentifier(unitNumber) || null,
          phase_id: phaseId || null,
          inventory_asset_id: inventoryAssetId || null,
          investment_amount: amount || null,
          agreement_date: agreementDate || null,
          source_lead_id: leadId || null,
        });
        onDone(
          result.reused_existing ? 'Mevcut anlaşma bulundu. Yeni kayıt oluşturulmadı.' : 'Anlaşma oluşturuldu.',
          result,
        );
      }
      await queryClient.invalidateQueries({ queryKey: ['crm'] });
      await queryClient.invalidateQueries({ queryKey: ['crm-leads'] });
      onClose();
    } catch (err) {
      setError(err instanceof ApiError || err instanceof Error ? err.message : 'Kayıt kaydedilemedi. Yeniden deneyin.');
    } finally {
      setPending(false);
    }
  };

  return (
    <div className="crm-record-dialog" role="dialog" aria-label={title}>
      <button type="button" className="crm-ops-drawer-backdrop" aria-label="Kapat" onClick={onClose} />
      <aside className="crm-ops-drawer">
        <div className="crm-ops-drawer__head">
          <h3>{title}</h3>
          <button type="button" onClick={onClose}>Kapat</button>
        </div>
        <div className="crm-ops-drawer__body">
          {mode === 'agency-customer' ? (
            <Select label="Acente" value={agencyId} onChange={(event) => setAgencyId(event.target.value)}>
              <option value="">Seçin</option>
              {(agentsQuery.data?.items ?? []).map((item) => (
                <option key={item.id} value={item.id}>{item.display_name}</option>
              ))}
            </Select>
          ) : null}
          {mode !== 'convert' ? (
            <CrmContactPicker
              selectedId={person.contact_id}
              selectedName={selectedName}
              projectId={projectGroup.includes('-') ? projectGroup : undefined}
              projectGroup={projectGroup && !projectGroup.includes('-') ? projectGroup : undefined}
              onSelect={(contact) => {
                if (!contact) {
                  setPerson((current) => ({ ...current, contact_id: contactId || '' }));
                  setSelectedName('');
                  return;
                }
                setSelectedName(contact.name);
                const [first, ...rest] = contact.name.split(' ');
                setPerson((current) => ({
                  ...current,
                  contact_id: contact.id,
                  first_name: first || current.first_name,
                  last_name: rest.join(' ') || current.last_name,
                  phone: contact.phone || current.phone,
                  email: contact.email || current.email,
                }));
              }}
            />
          ) : null}
          {mode !== 'convert' && !person.contact_id ? (
            <CrmPersonFields
              value={person}
              onChange={setPerson}
              users={(usersQuery.data?.items ?? []).map((item) => ({ id: item.id, name: item.full_name }))}
            />
          ) : null}
          {needsSale ? (
            <>
              <Select label="Proje" value={projectGroup} onChange={(event) => { setProjectGroup(event.target.value); setPhaseId(''); setUnitNumber(''); setInventoryAssetId(''); }}>
                <option value="">Seçin</option>
                {projectOptions.map((item) => (
                  <option key={item.project_id || item.project_group || item.label} value={item.project_group || item.project_id || ''}>
                    {item.label}
                  </option>
                ))}
              </Select>
              {unitsQuery.data?.uses_phases && !(unitsQuery.data?.phases ?? []).length ? (
                <p data-testid="phased-project-empty">Bu proje fazlı olarak tanımlı. Önce Projeler &gt; Fazlar bölümünden faz oluşturun.</p>
              ) : null}
              {unitsQuery.data?.uses_phases && (unitsQuery.data?.phases ?? []).length ? (
                <Select
                  label="Faz"
                  value={phaseId}
                  onChange={(event) => {
                    setPhaseId(event.target.value);
                    setUnitNumber('');
                    setInventoryAssetId('');
                  }}
                >
                  <option value="">Seçin</option>
                  {(unitsQuery.data?.phases ?? []).map((phase) => (
                    <option key={phase.id} value={phase.id}>{phase.name}</option>
                  ))}
                </Select>
              ) : null}
              {!(unitsQuery.data?.uses_phases && !(unitsQuery.data?.phases ?? []).length) && (!unitsQuery.data?.uses_phases || phaseId) ? (
                <>
                  <Select
                    label="Daire / Ünite"
                    value={inventoryAssetId}
                    onChange={(event) => {
                      const selected = unitsForPhase(unitsQuery.data?.items, phaseId, unitsQuery.data?.uses_phases ? unitsQuery.data?.phases : []).find(
                        (item) => item.id === event.target.value,
                      );
                      setInventoryAssetId(selected?.inventory_asset_id || '');
                      setUnitNumber(selected ? unitIdentifier(selected.unit_number) : '');
                      if (selected?.phase_id) setPhaseId(selected.phase_id);
                    }}
                  >
                    <option value="">Seçin</option>
                    {unitsForPhase(unitsQuery.data?.items, phaseId, unitsQuery.data?.uses_phases ? unitsQuery.data?.phases : []).map((item) => (
                      <option key={item.id} value={item.id}>{unitSelectionLabel(item)}</option>
                    ))}
                  </Select>
                  {unitsQuery.data?.uses_phases && phaseId && unitsForPhase(unitsQuery.data?.items, phaseId, unitsQuery.data?.phases).length === 0 ? (
                    <p data-testid="phase-units-empty">Bu faza henüz ünite atanmadı.</p>
                  ) : null}
                  <Input
                    label="Daire / Ünite"
                    value={unitNumber}
                    onChange={(event) => {
                      setUnitNumber(event.target.value);
                      setInventoryAssetId('');
                    }}
                  />
                </>
              ) : null}
              {inventoryAssetId ? (
                <dl data-testid="agreement-unit-summary">
                  {(() => {
                    const selected = (unitsQuery.data?.items ?? []).find((item) => item.inventory_asset_id === inventoryAssetId || item.id === inventoryAssetId);
                    if (!selected) return null;
                    const rows = [
                      ['Ünite', selected.unit_number],
                      ['Faz', selected.phase_name],
                      ['Bina', selected.building],
                      ['Kat', selected.floor],
                      ['Yatak odası', selected.bedrooms],
                      ['Banyo', selected.bathrooms],
                      ['Alan', selected.area_sqft],
                      ['Durum', selected.sales_status],
                      ['Liste fiyatı', selected.list_price ? `${selected.currency || '$'} ${selected.list_price}` : ''],
                    ].filter(([, value]) => value);
                    return rows.map(([label, value]) => (
                      <div key={label}><dt>{label}</dt><dd>{value}</dd></div>
                    ));
                  })()}
                </dl>
              ) : null}
              <label>
                Satış fiyatı
                <span data-testid="sale-price-prefix">{currencyPrefix((unitsQuery.data?.items ?? []).find((item) => item.inventory_asset_id === inventoryAssetId || item.id === inventoryAssetId)?.currency || projectOptions.find((item) => (item.project_group || item.project_id) === projectGroup)?.currency)}</span>
                <input value={amount} inputMode="decimal" onChange={(event) => setAmount(event.target.value.replace(/[^0-9.]/g, ''))} />
              </label>
              <Input label="Anlaşma tarihi" type="date" value={agreementDate} onChange={(event) => setAgreementDate(event.target.value)} />
            </>
          ) : null}
          {error ? <p role="alert">{error}</p> : null}
          <Button type="button" size="sm" disabled={pending} onClick={() => void submit()}>
            {pending ? 'Kaydediliyor…' : 'Kaydet'}
          </Button>
        </div>
      </aside>
    </div>
  );
}
