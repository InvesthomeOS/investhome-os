export const NEDIM_CONTACT_ID = '811c6aed-5f58-4c89-a9b1-0eebed64b9cf';
export const IZZET_CONTACT_ID = '339559ed-0d11-4e7c-a021-a07b388a817b';
export const SEMRIN_CONTACT_ID = '3dde5bdc-0919-4bdc-bc29-5e220e2ff0f2';

export const PILOT_PERSON_IDS = new Set([NEDIM_CONTACT_ID, IZZET_CONTACT_ID]);

export const PILOT_SALES_IDS = new Set([
  'd30d258a-3b89-458a-bfa0-a2de4f9f0ba2',
  'bdfd5ca1-e491-4896-b5d4-4b401ef428ac',
  '444f6517-595a-4067-9c0c-3521708d2223',
]);

export function salesDetailUrl(contactId: string, agreementId: string): string {
  return `/workspaces/crm/contacts/${contactId}/satin-alma/${agreementId}`;
}

export function isPilotPersonId(contactId: string | null | undefined): boolean {
  return Boolean(contactId && PILOT_PERSON_IDS.has(contactId));
}

export function isSemrinPilotPerson(contactId: string | null | undefined): boolean {
  return Boolean(contactId);
}

export function isPilotSalesId(agreementId: string | null | undefined): boolean {
  return Boolean(agreementId && PILOT_SALES_IDS.has(agreementId));
}
