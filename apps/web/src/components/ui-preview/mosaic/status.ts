import type { LeadStatus } from './demo-data';

export function statusClass(status: LeadStatus | string): string {
  const map: Record<string, string> = {
    New: 'mosaic-badge--sky',
    Qualified: 'mosaic-badge--violet',
    Meeting: 'mosaic-badge--indigo',
    Proposal: 'mosaic-badge--yellow',
    Negotiation: 'mosaic-badge--yellow',
    Won: 'mosaic-badge--green',
    Lost: 'mosaic-badge--red',
    Active: 'mosaic-badge--green',
    'Due diligence': 'mosaic-badge--sky',
    Watch: 'mosaic-badge--yellow',
  };
  return map[status] ?? 'mosaic-badge--gray';
}

export function healthClass(health: 'on_track' | 'watch' | 'risk'): string {
  if (health === 'on_track') return 'mosaic-health--ok';
  if (health === 'watch') return 'mosaic-health--watch';
  return 'mosaic-health--risk';
}

export function healthLabel(health: 'on_track' | 'watch' | 'risk'): string {
  if (health === 'on_track') return 'On track';
  if (health === 'watch') return 'Watch';
  return 'At risk';
}
