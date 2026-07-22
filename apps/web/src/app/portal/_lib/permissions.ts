import {
  contractsA,
  contractsB,
  documentsA,
  documentsB,
  holdingsA,
  holdingsB,
  meetingsA,
  messagesA,
  messagesB,
  notificationsA,
  paymentsA,
  paymentsB,
  projectsA,
  projectsB,
  rentalA,
  reservationsA,
  reservationsB,
  tasksA,
  investorA,
  investorB,
} from '../_data/investors';
import type {
  Contract,
  Payment,
  PortalDocument,
  PortalInvestor,
  PortalMeeting,
  PortalMessage,
  PortalNotification,
  PortalTask,
  PortfolioHolding,
  ProjectDetail,
  RentalIncomeRow,
  Reservation,
} from '../_data/types';

function byInvestor<T extends { investorId: string }>(rows: T[], investorId: string): T[] {
  return rows.filter((row) => row.investorId === investorId);
}

export function getInvestorProfile(investorId: string): PortalInvestor | null {
  if (investorId === investorA.id) return investorA;
  if (investorId === investorB.id) return investorB;
  return null;
}

export function getHoldingsFor(investorId: string): PortfolioHolding[] {
  if (investorId === investorA.id) return holdingsA;
  if (investorId === investorB.id) return holdingsB;
  return [];
}

export function getProjectsFor(investorId: string): ProjectDetail[] {
  if (investorId === investorA.id) return projectsA;
  if (investorId === investorB.id) return projectsB;
  return [];
}

export function getProjectFor(investorId: string, projectId: string): ProjectDetail | null {
  return getProjectsFor(investorId).find((p) => p.id === projectId) ?? null;
}

export function getReservationsFor(investorId: string): Reservation[] {
  return byInvestor([...reservationsA, ...reservationsB], investorId);
}

export function getContractsFor(investorId: string): Contract[] {
  return byInvestor([...contractsA, ...contractsB], investorId);
}

export function getPaymentsFor(investorId: string): Payment[] {
  return byInvestor([...paymentsA, ...paymentsB], investorId);
}

export function getRentalFor(investorId: string): RentalIncomeRow[] {
  return byInvestor(rentalA, investorId);
}

export function getDocumentsFor(investorId: string): PortalDocument[] {
  return byInvestor([...documentsA, ...documentsB], investorId);
}

export function getDocumentFor(investorId: string, documentId: string): PortalDocument | null {
  const doc = [...documentsA, ...documentsB].find((d) => d.id === documentId) ?? null;
  if (!doc || doc.investorId !== investorId) return null;
  return doc;
}

/** Permission-checked download gate — false if wrong investor or download disabled. */
export function canDownloadDocument(investorId: string, documentId: string): boolean {
  const doc = getDocumentFor(investorId, documentId);
  return Boolean(doc?.canDownload);
}

export function getMessagesFor(investorId: string): PortalMessage[] {
  return byInvestor([...messagesA, ...messagesB], investorId);
}

export function getTasksFor(investorId: string): PortalTask[] {
  return byInvestor(tasksA, investorId);
}

export function getMeetingsFor(investorId: string): PortalMeeting[] {
  return byInvestor(meetingsA, investorId);
}

export function getNotificationsFor(investorId: string): PortalNotification[] {
  return byInvestor(notificationsA, investorId);
}

/** Explicit isolation helper for tests / API. */
export function assertNoCrossInvestorLeak(viewerId: string, foreignInvestorId: string): boolean {
  if (viewerId === foreignInvestorId) return true;
  const leakedDocs = getDocumentsFor(viewerId).some((d) => d.investorId === foreignInvestorId);
  const leakedHoldings = getHoldingsFor(viewerId).some((h) =>
    getHoldingsFor(foreignInvestorId).some((fh) => fh.id === h.id),
  );
  const leakedMsgs = getMessagesFor(viewerId).some((m) => m.investorId === foreignInvestorId);
  return !leakedDocs && !leakedHoldings && !leakedMsgs;
}
