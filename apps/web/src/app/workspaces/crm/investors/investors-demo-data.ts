import { makePeoplePreview } from '../people/people-demo-data';
import type { PeopleWorkspacePreview } from '../people/people-model';

/** Investor-focused fixtures adapted from People foundation. */
export function makeInvestorsPreview(): PeopleWorkspacePreview {
  const base = makePeoplePreview();
  const investors = base.people.filter(
    (row) =>
      row.role === 'investor' ||
      row.role === 'decisionMaker' ||
      row.role === 'ceo' ||
      row.role === 'partner' ||
      row.role === 'finance',
  );

  return {
    ...base,
    totalPeople: Math.max(investors.length * 18, 126),
    totalPages: 7,
    people: investors,
    kpis: [
      {
        key: 'total',
        value: 126,
        hintKey: 'totalHint',
        delta: '+11',
        deltaTone: 'up',
      },
      {
        key: 'active',
        value: 84,
        hintKey: 'activeHint',
        delta: '+7',
        deltaTone: 'up',
      },
      {
        key: 'decisionMakers',
        value: 52,
        hintKey: 'decisionMakersHint',
        delta: '+4',
        deltaTone: 'up',
      },
      {
        key: 'newThisMonth',
        value: 14,
        hintKey: 'newThisMonthHint',
        delta: '+6',
        deltaTone: 'up',
      },
      {
        key: 'meetingPending',
        value: 9,
        hintKey: 'meetingPendingHint',
        delta: '+2',
        deltaTone: 'up',
      },
    ],
    recentPeople: base.recentPeople.filter((p) =>
      investors.some((inv) => inv.id === p.id || inv.name === p.name),
    ),
    activePeople: base.activePeople,
  };
}
