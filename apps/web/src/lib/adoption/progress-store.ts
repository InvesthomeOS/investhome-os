'use client';

import type { PathStatus } from './types';

const PREFIX = 'ih.adoption.g13.';

export type TourProgress = {
  tourId: string;
  stepIndex: number;
  completed: boolean;
  updatedAt: string;
};

export type ChecklistProgress = {
  checklistId: string;
  completedItemIds: string[];
  updatedAt: string;
};

export type OnboardingState = {
  completedSteps: string[];
  languageConfirmed: boolean;
  timezoneConfirmed: boolean;
  roleReviewed: boolean;
  tourStarted: boolean;
  finished: boolean;
  updatedAt: string;
};

export type KnowledgeScore = {
  checkId: string;
  score: number;
  passed: boolean;
  attempts: number;
  updatedAt: string;
};

export type PathProgressRecord = {
  pathId: string;
  status: PathStatus;
  completedModuleIds: string[];
  lastActivity: string;
};

export type AdoptionLocalState = {
  onboarding: OnboardingState;
  tours: Record<string, TourProgress>;
  checklists: Record<string, ChecklistProgress>;
  knowledge: Record<string, KnowledgeScore>;
  paths: Record<string, PathProgressRecord>;
  simulationMode: boolean;
  feedback: Array<Record<string, string>>;
  support: Array<Record<string, string>>;
  drafts: Array<Record<string, unknown>>;
};

function emptyState(): AdoptionLocalState {
  return {
    onboarding: {
      completedSteps: [],
      languageConfirmed: false,
      timezoneConfirmed: false,
      roleReviewed: false,
      tourStarted: false,
      finished: false,
      updatedAt: new Date().toISOString(),
    },
    tours: {},
    checklists: {},
    knowledge: {},
    paths: {},
    simulationMode: false,
    feedback: [],
    support: [],
    drafts: [],
  };
}

function storageKey(userId: string): string {
  return `${PREFIX}${userId}`;
}

export function loadAdoptionState(userId: string): AdoptionLocalState {
  if (typeof window === 'undefined') return emptyState();
  try {
    const raw = window.localStorage.getItem(storageKey(userId));
    if (!raw) return emptyState();
    return { ...emptyState(), ...JSON.parse(raw) } as AdoptionLocalState;
  } catch {
    return emptyState();
  }
}

export function saveAdoptionState(userId: string, state: AdoptionLocalState): void {
  if (typeof window === 'undefined') return;
  window.localStorage.setItem(storageKey(userId), JSON.stringify(state));
}

export function updateAdoptionState(
  userId: string,
  updater: (prev: AdoptionLocalState) => AdoptionLocalState,
): AdoptionLocalState {
  const next = updater(loadAdoptionState(userId));
  saveAdoptionState(userId, next);
  return next;
}
