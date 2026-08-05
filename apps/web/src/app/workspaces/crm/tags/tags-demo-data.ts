import type { TagsWorkspacePreview } from './tags-model';

/** Typed local fixtures for Tags module — presentation / local state. */
export function makeTagsPreview(): TagsWorkspacePreview {
  return {
    tags: [
      {
        id: 'tag-hot-lead',
        name: 'Hot Lead',
        color: 'rose',
        usageCount: 42,
        category: 'priority',
        description: 'High-intent prospects ready for outreach.',
      },
      {
        id: 'tag-vip',
        name: 'VIP',
        color: 'amber',
        usageCount: 18,
        category: 'lifecycle',
        description: 'Priority relationship accounts.',
      },
      {
        id: 'tag-marina',
        name: 'Marina Interest',
        color: 'cyan',
        usageCount: 27,
        category: 'interest',
        description: 'Interested in Marina Heights inventory.',
      },
      {
        id: 'tag-referral',
        name: 'Referral',
        color: 'green',
        usageCount: 33,
        category: 'source',
        description: 'Came through partner or customer referral.',
      },
      {
        id: 'tag-nurture',
        name: 'Nurture',
        color: 'navy',
        usageCount: 56,
        category: 'lifecycle',
        description: 'Long-cycle nurture sequence.',
      },
      {
        id: 'tag-investor',
        name: 'Investor Track',
        color: 'violet',
        usageCount: 14,
        category: 'interest',
        description: 'Capital partner / investor path.',
      },
      {
        id: 'tag-follow-up',
        name: 'Follow-up Due',
        color: 'slate',
        usageCount: 21,
        category: 'priority',
        description: 'Needs a scheduled follow-up this week.',
      },
      {
        id: 'tag-event',
        name: 'Event 2026',
        color: 'cyan',
        usageCount: 9,
        category: 'source',
        description: 'Captured at 2026 launch event.',
      },
    ],
  };
}
