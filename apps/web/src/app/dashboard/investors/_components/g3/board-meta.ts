/**
 * Client-side board metadata for fields not yet on Investor API
 * (probability, priority, next action, stage-change notes).
 * Persisted in localStorage; stage itself is PATCH'd via /investors.
 */

export type InvestorPriority = 'low' | 'medium' | 'high' | 'urgent';

export interface StageHistoryEntry {
  from: string;
  to: string;
  at: string;
  note?: string;
  by?: string;
}

export interface InvestorBoardMeta {
  probability?: number;
  priority?: InvestorPriority;
  nextAction?: string;
  warning?: string;
  stageHistory?: StageHistoryEntry[];
}

const STORAGE_KEY = 'investhome.investors.g3.board-meta.v1';

function readAll(): Record<string, InvestorBoardMeta> {
  if (typeof window === 'undefined') return {};
  try {
    const raw = window.localStorage.getItem(STORAGE_KEY);
    if (!raw) return {};
    const parsed = JSON.parse(raw) as Record<string, InvestorBoardMeta>;
    return parsed && typeof parsed === 'object' ? parsed : {};
  } catch {
    return {};
  }
}

function writeAll(data: Record<string, InvestorBoardMeta>) {
  if (typeof window === 'undefined') return;
  window.localStorage.setItem(STORAGE_KEY, JSON.stringify(data));
}

export function getBoardMeta(investorId: string): InvestorBoardMeta {
  return readAll()[investorId] ?? {};
}

export function setBoardMeta(investorId: string, patch: Partial<InvestorBoardMeta>): InvestorBoardMeta {
  const all = readAll();
  const next = { ...(all[investorId] ?? {}), ...patch };
  all[investorId] = next;
  writeAll(all);
  return next;
}

export function appendStageHistory(
  investorId: string,
  entry: StageHistoryEntry,
): InvestorBoardMeta {
  const current = getBoardMeta(investorId);
  const history = [...(current.stageHistory ?? []), entry].slice(-40);
  return setBoardMeta(investorId, { stageHistory: history });
}
