export type TagColorKey =
  | 'navy'
  | 'cyan'
  | 'green'
  | 'amber'
  | 'rose'
  | 'violet'
  | 'slate';

export type TagRecord = {
  id: string;
  name: string;
  color: TagColorKey;
  usageCount: number;
  category: 'lifecycle' | 'interest' | 'priority' | 'source' | 'custom';
  description: string;
};

export type TagsWorkspacePreview = {
  tags: TagRecord[];
};

export const TAG_COLOR_HEX: Record<TagColorKey, string> = {
  navy: '#075b75',
  cyan: '#58aebb',
  green: '#2f8a5b',
  amber: '#d4a017',
  rose: '#c45c5c',
  violet: '#7a6bb5',
  slate: '#718087',
};
